# BYOK / KMS Integration

RunLedger encrypts sensitive secrets at rest (Kafka SASL passwords, SSO client secrets, SCIM tokens, billing webhook secrets) using a KMS provider. Three providers are supported:

| Provider | Use case |
|----------|----------|
| `local` | Default — Fernet derived from `SECRET_KEY`. Suitable for single-server or Docker Compose deployments. |
| `aws_kms` | Envelope encryption via AWS KMS. Suitable for EKS/EC2 deployments in AWS. |
| `vault` | HashiCorp Vault Transit secrets engine. Suitable for multi-cloud or on-prem with existing Vault infrastructure. |

## How encryption works

### Local (default)

Derives a 32-byte Fernet key from `SHA-256(SECRET_KEY)`. All secrets are encrypted and decrypted in-process. No external calls.

```
plaintext → Fernet(SHA-256(SECRET_KEY)) → ciphertext
```

### AWS KMS (envelope encryption)

Uses KMS to generate a per-encrypt AES-256 data key. The plaintext is encrypted with Fernet using the data key. The encrypted data key is stored alongside the ciphertext.

```
plaintext → Fernet(data_key_plaintext) → fernet_ct
KMS.GenerateDataKey(key_id) → (data_key_plaintext, data_key_encrypted)

stored: "awskms:<base64(data_key_encrypted)>:<fernet_ct>"
```

On decrypt:
```
KMS.Decrypt(data_key_encrypted) → data_key_plaintext
Fernet(data_key_plaintext).decrypt(fernet_ct) → plaintext
```

This means AWS KMS is called on every encrypt AND decrypt. The data key is not cached.

### HashiCorp Vault Transit

Delegates all encryption/decryption to Vault's Transit secrets engine. Vault handles the key material; RunLedger never sees the raw key.

```
POST /v1/transit/encrypt/{key}  {"plaintext": base64(secret)} → "vault:v1:..."
stored: "vault:<vault:v1:...>"

POST /v1/transit/decrypt/{key}  {"ciphertext": "vault:v1:..."} → base64(plaintext)
```

## Configuration

### AWS KMS

Set in environment / Helm values:

```bash
KMS_PROVIDER=aws_kms
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/mrk-abc123
AWS_KMS_REGION=us-east-1
```

Or in `values.yaml`:

```yaml
secrets:
  kmsProvider: aws_kms
  awsKmsKeyId: "arn:aws:kms:us-east-1:123456789:key/mrk-abc123"
  awsKmsRegion: us-east-1
```

#### Required IAM policy

Attach this policy to the IAM role used by RunLedger pods (via IRSA on EKS, or instance profile on EC2):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RunLedgerKMS",
      "Effect": "Allow",
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789:key/mrk-abc123"
    }
  ]
}
```

#### IRSA setup (EKS)

```bash
# 1. Create IAM role with trust policy for your service account
aws iam create-role \
  --role-name runledger-kms \
  --assume-role-policy-document file://trust-policy.json

# trust-policy.json:
# {
#   "Version": "2012-10-17",
#   "Statement": [{
#     "Effect": "Allow",
#     "Principal": {"Federated": "arn:aws:iam::ACCOUNT:oidc-provider/OIDC_URL"},
#     "Action": "sts:AssumeRoleWithWebIdentity",
#     "Condition": {
#       "StringEquals": {
#         "OIDC_URL:sub": "system:serviceaccount:runledger:runledger"
#       }
#     }
#   }]
# }

# 2. Attach the KMS policy
aws iam attach-role-policy \
  --role-name runledger-kms \
  --policy-arn arn:aws:iam::123456789:policy/RunLedgerKMSPolicy

# 3. Annotate the ServiceAccount in Helm values
```

```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/runledger-kms
```

#### Using a Multi-Region Key (MRK)

For active-active multi-region deployments, use an MRK:

```
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/mrk-abc123
```

Decrypt works in any region where the MRK replica exists — no re-encryption needed when failing over.

### HashiCorp Vault Transit

```bash
KMS_PROVIDER=vault
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=hvs.CAESIB...           # or use Vault Agent sidecar
VAULT_TRANSIT_KEY=runledger
```

Or in `values.yaml`:

```yaml
secrets:
  kmsProvider: vault
  vaultAddr: "https://vault.example.com"
  vaultToken: ""   # store in existingSecret key VAULT_TOKEN
  vaultTransitKey: runledger
```

#### Required Vault policy

```hcl
# runledger-policy.hcl
path "transit/encrypt/runledger" {
  capabilities = ["update"]
}

path "transit/decrypt/runledger" {
  capabilities = ["update"]
}
```

```bash
# Create the transit key
vault secrets enable transit
vault write -f transit/keys/runledger type=aes256-gcm96

# Create the policy
vault policy write runledger runledger-policy.hcl

# Create a token (or use AppRole / Kubernetes auth)
vault token create \
  --policy=runledger \
  --ttl=8760h \
  --renewable=true
```

#### Vault Agent sidecar (recommended for K8s)

Instead of storing a long-lived token in a Secret, use the Vault Agent sidecar to inject a short-lived token:

```yaml
podAnnotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "runledger"
  vault.hashicorp.com/agent-inject-secret-vault-token: "auth/token/create"
```

## Rotating keys

### Local → AWS KMS migration

When switching from `local` to `aws_kms`, existing ciphertexts are in Fernet format (no prefix). They will fail to decrypt with the AWS KMS provider.

Migration procedure:

1. Keep `KMS_PROVIDER=local` while re-encrypting existing secrets.
2. Write a one-off script that reads each encrypted column, decrypts with `LocalKmsProvider`, re-encrypts with `AwsKmsProvider`, and updates the row.
3. After all rows are migrated, switch `KMS_PROVIDER=aws_kms`.

The `services/kms.py` `LocalKmsProvider.decrypt()` handles the `b64:` prefix and raw Fernet formats for backwards compatibility.

### AWS KMS key rotation

AWS KMS supports automatic annual key rotation. Existing ciphertexts remain decryptable after rotation — AWS KMS tracks which key version was used for each ciphertext.

```bash
aws kms enable-key-rotation --key-id mrk-abc123
```

No application changes needed.

### Vault key rotation

```bash
vault write -f transit/keys/runledger/rotate
```

Vault re-wraps existing ciphertexts transparently on next decrypt. To force re-wrap:

```bash
vault write transit/rewrap/runledger ciphertext="vault:v1:..."
```

## Ciphertext format reference

| Provider | Stored format |
|----------|--------------|
| `local` | `gAAAAA...` (Fernet token, base64url) |
| `aws_kms` | `awskms:<base64(encrypted_data_key)>:<fernet_token>` |
| `vault` | `vault:<vault:v1:XXXX...>` |

The `decrypt_secret()` function in `services/crypto.py` reads the prefix and dispatches to the correct provider automatically. This means secrets encrypted with one provider can be decrypted even if `KMS_PROVIDER` has changed, **as long as the required credentials are present**.

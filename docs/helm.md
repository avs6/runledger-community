# Helm Chart Deployment

RunLedger ships an official Helm chart for production Kubernetes deployments. The chart deploys the full stack — the control plane (API, Celery worker, Celery beat, Next.js web) and the optimization layer (the stateless microservices, each with an HPA + PDB, plus the pluggable stateful stores) — along with an optional pre-install migration Job and a multi-store backup CronJob.

Two modes, one chart:

- **Self-hosted / dev** — leave the stores in-cluster; a single `helm install` brings up everything (including optional in-cluster Postgres + Redis), no external dependencies.
- **Production / HA** — set each store `external: true` with a managed URL; the stateless services still autoscale in-cluster. See [ha.md](./ha.md) for the scaling model.

The optimization microservice images are published to `docker.io/abijith13/runledger-<svc>` by the `Build & Push Images` workflow; override `optimization.imageRegistry` / `optimization.imageTag` to use your own registry.

## Prerequisites

- Kubernetes 1.27+
- Helm 3.12+
- An external PostgreSQL 16 database
- An external Redis 7 instance
- (Optional) cert-manager for automatic TLS

## Quick start

```bash
# Add the chart (or use the local path from the repo)
helm install runledger ./infra/helm/runledger \
  --namespace runledger \
  --create-namespace \
  --set externalDatabase.url="postgresql+asyncpg://user:pass@pg-host:5432/runledger" \
  --set externalRedis.url="redis://redis-host:6379/0" \
  --set secrets.secretKey="$(openssl rand -hex 32)" \
  --set secrets.nextauthSecret="$(openssl rand -hex 32)" \
  --set ingress.enabled=true \
  --set ingress.hosts.api.host=api.example.com \
  --set ingress.hosts.web.host=app.example.com
```

## Production values file

For production, store secrets in a pre-created Kubernetes Secret and reference it by name:

```bash
kubectl create secret generic runledger-secrets \
  --namespace runledger \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@pg-host:5432/runledger" \
  --from-literal=REDIS_URL="redis://redis-host:6379/0" \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_SECRET="$(openssl rand -hex 32)" \
  --from-literal=METRICS_TOKEN="$(openssl rand -hex 24)" \
  --from-literal=NEXTAUTH_SECRET="$(openssl rand -hex 32)"
```

Then in your values override file:

```yaml
# my-values.yaml
image:
  repository: ghcr.io/avs6/runledger-api
  tag: "0.1.0"

webImage:
  repository: ghcr.io/avs6/runledger-web
  tag: "0.1.0"

secrets:
  existingSecret: runledger-secrets

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    api:
      host: api.example.com
      tls: true
      secretName: runledger-api-tls
    web:
      host: app.example.com
      tls: true
      secretName: runledger-web-tls

api:
  replicaCount: 3

worker:
  replicaCount: 4

autoscaling:
  api:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
  worker:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
```

```bash
helm upgrade --install runledger ./infra/helm/runledger \
  --namespace runledger \
  --values my-values.yaml
```

## KMS / BYOK

To use AWS KMS for envelope encryption instead of the default local Fernet:

```yaml
secrets:
  existingSecret: runledger-secrets   # must contain AWS_KMS_KEY_ID
  kmsProvider: aws_kms
  awsKmsKeyId: "arn:aws:kms:us-east-1:123456789:key/mrk-..."
  awsKmsRegion: us-east-1

serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/runledger-kms
```

For HashiCorp Vault Transit:

```yaml
secrets:
  kmsProvider: vault
  vaultAddr: "https://vault.example.com"
  vaultToken: ""           # or use existingSecret key VAULT_TOKEN
  vaultTransitKey: runledger
```

The referenced Secret must carry the provider credentials (`AWS_KMS_KEY_ID` for KMS, or `VAULT_TOKEN` for Vault Transit); grant the ServiceAccount the matching IAM role (EKS IRSA) or Vault policy.

## Backup CronJob

The chart includes an optional nightly **multi-store** backup CronJob → S3. The control-plane Postgres is always dumped; the optimization-layer durable stores are toggled individually:

```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"
  s3Bucket: "s3://my-bucket/runledger-backups"
  awsRegion: us-east-1
  retainDays: 30
  stores:
    memoryDb: { enabled: true }   # pg_dump the Letta memory Postgres
    qdrant:   { enabled: false }  # Qdrant snapshot (largely regenerable)
    kuzu:     { enabled: true }   # tar the knowledge-graph PVC
    skills:   { enabled: true }   # tar the skill-registry PVC
```

The backup pod uses the `postgres:16-alpine` image and requires AWS credentials. Use IRSA (EKS) or a `kube2iam` annotation on the ServiceAccount. See [backup-restore.md](./backup-restore.md) for the store matrix and restore procedures (`scripts/restore.sh`).

## Migrations

By default, `helm install` / `helm upgrade` runs an `alembic upgrade head` Job before the pods start (`pre-install,pre-upgrade` hook). To disable (e.g., you manage migrations separately):

```yaml
migrations:
  enabled: false
```

See [upgrade.md](./upgrade.md) for zero-downtime migration strategy.

## Monitoring

Expose the Prometheus metrics endpoint to your scraper:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/path: /metrics
  prometheus.io/port: "8000"

secrets:
  metricsToken: "your-scrape-token"
```

Prometheus scrape config:

```yaml
- job_name: runledger
  static_configs:
    - targets: ["runledger-api.runledger.svc.cluster.local:8000"]
  authorization:
    type: Bearer
    credentials: <METRICS_TOKEN>
```

Import the dashboard JSON from `docs/grafana-dashboard.json` (see [ha.md](./ha.md) for the full Grafana setup).

## Values reference

| Key | Default | Description |
|-----|---------|-------------|
| `image.repository` | `ghcr.io/avs6/runledger-api` | API + worker image |
| `image.tag` | `latest` | Image tag |
| `api.replicaCount` | `2` | API pod count |
| `worker.replicaCount` | `2` | Worker pod count |
| `beat.replicaCount` | `1` | Beat pod count — **always 1** |
| `autoscaling.api.enabled` | `false` | Enable HPA for API |
| `autoscaling.worker.enabled` | `false` | Enable HPA for workers |
| `secrets.existingSecret` | `""` | Pre-created Secret name |
| `secrets.kmsProvider` | `local` | `local` / `aws_kms` / `vault` |
| `ingress.enabled` | `false` | Create Ingress resources |
| `migrations.enabled` | `true` | Run Alembic pre-upgrade Job |
| `backup.enabled` | `false` | Enable nightly multi-store backup CronJob |
| `backup.stores.*.enabled` | varies | Include memory-db / qdrant / kuzu / skills in the backup |
| `pricingConfig.enabled` | `false` | Mount custom pricing YAML |
| `optimization.enabled` | `true` | Deploy the optimization-layer services + stores |
| `optimization.imageRegistry` | `docker.io/abijith13` | Registry for the microservice images |
| `optimizationServices.<svc>.autoscaling.enabled` | `true` | HPA for a stateless optimization service |
| `stores.<store>.external` | `false` | Use a managed URL instead of an in-cluster StatefulSet |
| `postgres.inCluster` / `redis.inCluster` | `false` | Run control-plane Postgres / Redis in-cluster (self-host) |

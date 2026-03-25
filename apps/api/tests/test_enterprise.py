"""
Tests for enterprise hardening features:
  - KMS providers (local, aws_kms, vault)
  - Operational metrics endpoints (/metrics, /ops/status)
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from runledger_api.main import app
from runledger_api.services.kms import (
    AwsKmsProvider,
    LocalKmsProvider,
    VaultTransitProvider,
    reset_kms_provider_cache,
)

client = TestClient(app)


# ── KMS: Local provider ────────────────────────────────────────────────────────


class TestLocalKmsProvider:
    def setup_method(self) -> None:
        reset_kms_provider_cache()

    def test_encrypt_decrypt_roundtrip(self) -> None:
        p = LocalKmsProvider()
        ct = p.encrypt("my-secret-value")
        assert ct != "my-secret-value"
        assert p.decrypt(ct) == "my-secret-value"

    def test_decrypt_b64_legacy_format(self) -> None:
        p = LocalKmsProvider()
        b64 = "b64:" + base64.b64encode(b"legacy-secret").decode()
        assert p.decrypt(b64) == "legacy-secret"

    def test_decrypt_rejects_awskms_prefix(self) -> None:
        p = LocalKmsProvider()
        with pytest.raises(ValueError, match="awskms"):
            p.decrypt("awskms:somedata:somefernet")

    def test_decrypt_rejects_vault_prefix(self) -> None:
        p = LocalKmsProvider()
        with pytest.raises(ValueError, match="vault"):
            p.decrypt("vault:vault:v1:XXXX")

    def test_encrypt_produces_fernet_token(self) -> None:
        p = LocalKmsProvider()
        ct = p.encrypt("hello")
        # Fernet tokens start with 'g' (base64url encoded)
        assert ct.startswith("g") or "." not in ct  # Fernet base64url


# ── KMS: AWS KMS provider ─────────────────────────────────────────────────────


class TestAwsKmsProvider:
    def setup_method(self) -> None:
        reset_kms_provider_cache()

    def test_encrypt_produces_awskms_prefix(self) -> None:

        dk_plain = b"\x00" * 32
        dk_enc = b"\x01" * 32
        mock_client = MagicMock()
        mock_client.generate_data_key.return_value = {
            "Plaintext": dk_plain,
            "CiphertextBlob": dk_enc,
        }

        with patch("boto3.client", return_value=mock_client):
            p = AwsKmsProvider(key_id="arn:aws:kms:us-east-1:123:key/test")
            ct = p.encrypt("secret")

        assert ct.startswith("awskms:")
        parts = ct.split(":", 2)
        assert len(parts) == 3

    def test_decrypt_awskms_ciphertext(self) -> None:
        from cryptography.fernet import Fernet

        dk_plain = b"\x42" * 32
        # Build a real ciphertext with the known data key
        f = Fernet(base64.urlsafe_b64encode(dk_plain))
        fernet_ct = f.encrypt(b"secret-value").decode()
        dk_enc = b"\x99" * 32
        dk_b64 = base64.b64encode(dk_enc).decode()
        stored = f"awskms:{dk_b64}:{fernet_ct}"

        mock_client = MagicMock()
        mock_client.decrypt.return_value = {"Plaintext": dk_plain}

        with patch("boto3.client", return_value=mock_client):
            p = AwsKmsProvider(key_id="arn:aws:kms:us-east-1:123:key/test")
            result = p.decrypt(stored)

        assert result == "secret-value"

    def test_decrypt_legacy_delegates_to_local(self) -> None:
        """AWS KMS provider can still decrypt local Fernet ciphertexts."""
        local = LocalKmsProvider()
        local_ct = local.encrypt("fallback-value")

        mock_client = MagicMock()
        with patch("boto3.client", return_value=mock_client):
            p = AwsKmsProvider(key_id="arn:aws:kms:us-east-1:123:key/test")
            result = p.decrypt(local_ct)

        assert result == "fallback-value"
        # Should NOT have called KMS for a non-awskms ciphertext
        mock_client.decrypt.assert_not_called()


# ── KMS: Vault Transit provider ───────────────────────────────────────────────


class TestVaultTransitProvider:
    def setup_method(self) -> None:
        reset_kms_provider_cache()

    def test_encrypt_produces_vault_prefix(self) -> None:
        vault_response = MagicMock()
        vault_response.raise_for_status = MagicMock()
        vault_response.json.return_value = {"data": {"ciphertext": "vault:v1:ABC123"}}

        with patch("httpx.post", return_value=vault_response) as mock_post:
            p = VaultTransitProvider(
                addr="https://vault.example.com",
                token="hvs.test",
                key="runledger",
            )
            ct = p.encrypt("my-secret")

        assert ct == "vault:vault:v1:ABC123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "transit/encrypt/runledger" in call_kwargs[0][0]

    def test_decrypt_vault_ciphertext(self) -> None:
        plaintext_b64 = base64.b64encode(b"decrypted-value").decode()
        vault_response = MagicMock()
        vault_response.raise_for_status = MagicMock()
        vault_response.json.return_value = {"data": {"plaintext": plaintext_b64}}

        with patch("httpx.post", return_value=vault_response):
            p = VaultTransitProvider(
                addr="https://vault.example.com",
                token="hvs.test",
                key="runledger",
            )
            result = p.decrypt("vault:vault:v1:ABC123")

        assert result == "decrypted-value"

    def test_decrypt_legacy_delegates_to_local(self) -> None:
        local = LocalKmsProvider()
        local_ct = local.encrypt("legacy")

        p = VaultTransitProvider(
            addr="https://vault.example.com",
            token="hvs.test",
        )
        # Should use local fallback, not call vault
        with patch("httpx.post") as mock_post:
            result = p.decrypt(local_ct)

        assert result == "legacy"
        mock_post.assert_not_called()

    def test_vault_url_strips_trailing_slash(self) -> None:
        vault_response = MagicMock()
        vault_response.raise_for_status = MagicMock()
        vault_response.json.return_value = {"data": {"ciphertext": "vault:v1:X"}}

        with patch("httpx.post", return_value=vault_response) as mock_post:
            p = VaultTransitProvider(
                addr="https://vault.example.com/",  # trailing slash
                token="hvs.test",
            )
            p.encrypt("x")

        url = mock_post.call_args[0][0]
        assert "//v1" not in url  # no double slash


# ── Ops metrics endpoints ─────────────────────────────────────────────────────


METRICS_TOKEN = "test-metrics-token"


@pytest.fixture()
def mock_collect():
    metrics = {
        "collected_at": "2026-03-24T02:00:00+00:00",
        "uptime_seconds": 3600.0,
        "active_runs": 12,
        "pipeline_lag_seconds": 4.5,
        "ingest_rate_per_minute": 2.5,
        "provider_calls_last_hour": 450,
        "gateway_requests_last_hour": 120,
        "gateway_cache_hit_rate": 0.42,
        "uncosted_provider_calls": 3,
        "celery_queue_depths": {"celery": 5, "priority": 1, "low": 0},
    }
    with patch(
        "runledger_api.routers.ops._collect_metrics", new_callable=AsyncMock, return_value=metrics
    ) as m:
        yield m


@pytest.fixture(autouse=True)
def patch_metrics_token(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", METRICS_TOKEN)
    # Also patch settings directly to avoid env var parsing complexity
    with patch("runledger_api.routers.ops.settings") as mock_settings:
        mock_settings.effective_metrics_token = METRICS_TOKEN
        yield mock_settings


class TestPrometheusMetrics:
    def test_metrics_requires_token(self, mock_collect) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 401

    def test_metrics_rejects_wrong_token(self, mock_collect) -> None:
        resp = client.get("/metrics", headers={"X-Metrics-Token": "wrong"})
        assert resp.status_code == 401

    def test_metrics_returns_prometheus_format(self, mock_collect) -> None:
        resp = client.get("/metrics", headers={"X-Metrics-Token": METRICS_TOKEN})
        assert resp.status_code == 200
        body = resp.text
        assert "runledger_uptime_seconds" in body
        assert "runledger_active_runs" in body
        assert "runledger_pipeline_lag_seconds" in body
        assert "runledger_ingest_rate_per_minute" in body
        assert "runledger_celery_queue_depth" in body
        assert "# TYPE runledger_active_runs gauge" in body

    def test_metrics_includes_queue_labels(self, mock_collect) -> None:
        resp = client.get("/metrics", headers={"X-Metrics-Token": METRICS_TOKEN})
        body = resp.text
        assert 'queue="celery"' in body
        assert 'queue="priority"' in body
        assert 'queue="low"' in body

    def test_metrics_bearer_prefix_stripped(self, mock_collect) -> None:
        resp = client.get("/metrics", headers={"X-Metrics-Token": f"Bearer {METRICS_TOKEN}"})
        assert resp.status_code == 200


class TestOpsStatus:
    def test_ops_status_requires_token(self, mock_collect) -> None:
        resp = client.get("/ops/status")
        assert resp.status_code == 401

    def test_ops_status_returns_json(self, mock_collect) -> None:
        resp = client.get("/ops/status", headers={"X-Metrics-Token": METRICS_TOKEN})
        assert resp.status_code == 200
        data = resp.json()
        assert "active_runs" in data
        assert "pipeline_lag_seconds" in data
        assert "celery_queue_depths" in data
        assert data["active_runs"] == 12
        assert data["gateway_cache_hit_rate"] == 0.42

    def test_ops_status_collection_error_returns_500(self) -> None:
        with patch(
            "runledger_api.routers.ops._collect_metrics",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            resp = client.get("/ops/status", headers={"X-Metrics-Token": METRICS_TOKEN})
        assert resp.status_code == 500

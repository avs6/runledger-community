from __future__ import annotations

from typing import Any

from runledger_api.core.config import settings


def evaluate_infra_posture() -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def add_check(category: str, name: str, status: str, detail: str) -> None:
        checks.append(
            {
                "category": category,
                "name": name,
                "status": status,
                "detail": detail,
            }
        )

    redis_mode = settings.redis_durability_mode
    add_check(
        "redis",
        "durability",
        "pass" if redis_mode != "ephemeral" else "warn",
        (
            f"Redis durability mode is {redis_mode}."
            if redis_mode != "ephemeral"
            else "Redis is configured as ephemeral cache/queue storage; enable AOF or managed persistent Redis before storing non-ephemeral state."
        ),
    )

    add_check(
        "storage",
        "object_lifecycle",
        "pass" if settings.object_lifecycle_enabled else "warn",
        (
            f"Lifecycle policy configured for {settings.object_lifecycle_days} day(s)."
            if settings.object_lifecycle_enabled
            else "Object lifecycle rules are not configured for backup/compliance buckets."
        ),
    )

    compliance_ready = settings.compliance_export_enabled and bool(
        settings.compliance_export_bucket
    )
    add_check(
        "storage",
        "compliance_export",
        "pass" if compliance_ready else "warn",
        (
            f"Compliance exports target s3://{settings.compliance_export_bucket}/{settings.compliance_export_prefix}"
            if compliance_ready
            else "Compliance export storage is not configured."
        ),
    )

    add_check(
        "security",
        "abuse_protection",
        "pass" if settings.abuse_protection_enabled else "warn",
        (
            f"System surfaces are rate-limited at {settings.system_rate_limit_per_minute}/min."
            if settings.abuse_protection_enabled
            else "Abuse protection is disabled for system surfaces."
        ),
    )

    add_check(
        "security",
        "metrics_token",
        "pass" if settings.metrics_token else "warn",
        (
            "Dedicated metrics token is configured."
            if settings.metrics_token
            else "Metrics endpoint falls back to ADMIN_SECRET; set METRICS_TOKEN for tighter isolation."
        ),
    )

    add_check(
        "tls",
        "local_tls_demo",
        "pass" if settings.local_tls_enabled else "warn",
        (
            "Local TLS demo profile is enabled."
            if settings.local_tls_enabled
            else "Local TLS demo is off; use the tls-demo profile when you need realistic customer demos."
        ),
    )

    add_check(
        "deployment",
        "profile",
        "pass",
        f"Current deployment profile is '{settings.deployment_profile}'.",
    )

    summary = {
        "pass": sum(1 for c in checks if c["status"] == "pass"),
        "warn": sum(1 for c in checks if c["status"] == "warn"),
        "fail": sum(1 for c in checks if c["status"] == "fail"),
    }
    return {
        "mode": settings.infra_policy_enforcement_mode,
        "summary": summary,
        "checks": checks,
    }

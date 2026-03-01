"""
Celery worker: replay cost-projection experiment.

Projects the cost of running a dataset's runs against each experiment config
using actual token counts from provider_calls × ProviderPricing rates.
No real LLM calls are made — this is a pure cost projection.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.replay import ReplayDataset, ReplayExperiment

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="replay.run_experiment",
    max_retries=1,
)
def run_experiment_worker(experiment_id: str) -> dict[str, Any]:
    """Project costs for each model config in the experiment."""
    return asyncio.run(_run_experiment(experiment_id))


async def _run_experiment(experiment_id: str) -> dict[str, Any]:
    factory = _make_session_factory()

    async with factory() as session:
        # 1. Load experiment
        exp_stmt = select(ReplayExperiment).where(
            ReplayExperiment.id == experiment_id  # type: ignore[arg-type]
        )
        exp_result = await session.execute(exp_stmt)
        experiment = exp_result.scalar_one_or_none()
        if experiment is None:
            log.error("replay.experiment.not_found", experiment_id=experiment_id)
            return {"error": "experiment not found"}

        # 2. Load dataset
        ds_stmt = select(ReplayDataset).where(ReplayDataset.id == experiment.dataset_id)
        ds_result = await session.execute(ds_stmt)
        dataset = ds_result.scalar_one_or_none()
        if dataset is None:
            log.error("replay.dataset.not_found", dataset_id=str(experiment.dataset_id))
            return {"error": "dataset not found"}

        run_ids: list[str] = list(dataset.run_ids)
        configs: list[dict[str, Any]] = list(experiment.configs)

        if not run_ids:
            results_payload: dict[str, Any] = {
                "configs": [],
                "deltas": [],
                "completed_at": datetime.now(UTC).isoformat(),
                "dataset_run_count": 0,
            }
            await session.execute(
                update(ReplayExperiment)
                .where(ReplayExperiment.id == experiment.id)
                .values(results=results_payload, status="completed")
            )
            await session.commit()
            return {"experiment_id": experiment_id, "configs_run": 0}

        # 3. Query token totals for all runs in dataset
        token_stmt = text(
            """
            SELECT
                SUM(input_tokens)::bigint  AS total_input,
                SUM(output_tokens)::bigint AS total_output,
                COUNT(DISTINCT run_id)     AS run_count
            FROM provider_calls
            WHERE run_id = ANY(CAST(:run_ids AS UUID[]))
              AND status = 'success'
            """
        )
        token_result = await session.execute(token_stmt, {"run_ids": run_ids})
        token_row = token_result.one()

        total_input: int = int(token_row.total_input or 0)
        total_output: int = int(token_row.total_output or 0)
        run_count: int = int(token_row.run_count or 0)

        # 4. Project cost for each config
        config_results: list[dict[str, Any]] = []
        for cfg in configs:
            model_name: str = cfg["model"]
            label: str | None = cfg.get("label")

            pricing_stmt = (
                select(ProviderPricing).where(ProviderPricing.model == model_name).limit(1)
            )
            pricing_result = await session.execute(pricing_stmt)
            pricing = pricing_result.scalar_one_or_none()

            if pricing is not None:
                projected_cost = (
                    Decimal(total_input) / Decimal(1_000_000) * pricing.input_per_1m
                    + Decimal(total_output) / Decimal(1_000_000) * pricing.output_per_1m
                )
                pricing_found = True
            else:
                projected_cost = Decimal(0)
                pricing_found = False

            avg_cost_per_run = projected_cost / Decimal(run_count) if run_count > 0 else Decimal(0)

            config_results.append(
                {
                    "model": model_name,
                    "label": label,
                    "run_count": run_count,
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "projected_cost_usd": str(projected_cost),
                    "avg_cost_per_run": str(avg_cost_per_run),
                    "pricing_found": pricing_found,
                }
            )

        # 5. Build pairwise deltas (config[0] vs config[1], config[0] vs config[2], …)
        deltas: list[dict[str, Any]] = []
        if len(config_results) >= 2:
            base = config_results[0]
            cost_a = Decimal(base["projected_cost_usd"])
            for other in config_results[1:]:
                cost_b = Decimal(other["projected_cost_usd"])
                delta_pct: str | None = None
                if cost_a > Decimal(0):
                    delta_pct = str((cost_b - cost_a) / cost_a * Decimal(100))
                deltas.append(
                    {
                        "config_a": base["model"],
                        "config_b": other["model"],
                        "cost_delta_pct": delta_pct,
                    }
                )

        results_payload = {
            "configs": config_results,
            "deltas": deltas,
            "completed_at": datetime.now(UTC).isoformat(),
            "dataset_run_count": run_count,
        }

        # 6. Persist results
        await session.execute(
            update(ReplayExperiment)
            .where(ReplayExperiment.id == experiment.id)
            .values(results=results_payload, status="completed")
        )
        await session.commit()

        log.info(
            "replay.experiment.completed",
            experiment_id=experiment_id,
            configs_run=len(config_results),
            run_count=run_count,
        )
        return {"experiment_id": experiment_id, "configs_run": len(config_results)}

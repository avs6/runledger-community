"""Cost and token forecasting using linear regression and Holt-Winters.

Both methods produce point forecasts with confidence intervals. The
orchestrator runs both, picks the one with lower in-sample MAPE, and
stores the result.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLForecast
from runledger_api.services.ml.features import load_feature_series

log = structlog.get_logger()


@dataclass
class ForecastResult:
    method: str
    points: list[dict[str, Any]] = field(default_factory=list)
    mape: float = 0.0
    mae: float = 0.0
    r_squared: float = 0.0


def forecast_linear(
    dates: list[date],
    values: list[float],
    horizon_days: int = 14,
) -> ForecastResult:
    """Simple linear regression forecast with prediction intervals."""
    n = len(values)
    x = np.arange(n, dtype=np.float64)
    y = np.array(values, dtype=np.float64)

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs[0], coeffs[1]

    fitted = np.polyval(coeffs, x)
    residuals = y - fitted
    residual_std = float(np.std(residuals, ddof=2)) if n > 2 else float(np.std(residuals))

    abs_errors = np.abs(residuals)
    mae = float(np.mean(abs_errors))
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_errors = np.where(y != 0, abs_errors / np.abs(y), 0)
    mape = float(np.mean(pct_errors))

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    last_date = dates[-1]
    points = []
    for d in range(1, horizon_days + 1):
        future_x = n + d - 1
        predicted = slope * future_x + intercept
        margin_80 = 1.28 * residual_std * np.sqrt(1 + 1 / n + (future_x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2))
        margin_95 = 1.96 * residual_std * np.sqrt(1 + 1 / n + (future_x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2))
        points.append({
            "date": str(last_date + timedelta(days=d)),
            "predicted": round(max(predicted, 0), 4),
            "lower": round(max(predicted - margin_95, 0), 4),
            "upper": round(predicted + margin_95, 4),
        })

    return ForecastResult(
        method="linear",
        points=points,
        mape=round(mape, 4),
        mae=round(mae, 4),
        r_squared=round(r_squared, 4),
    )


def forecast_holt_winters(
    values: list[float],
    horizon_days: int = 14,
    seasonal_period: int = 7,
    last_date: date | None = None,
) -> ForecastResult | None:
    """Holt-Winters exponential smoothing with additive weekly seasonality."""
    if len(values) < seasonal_period * 2:
        return None

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        model = ExponentialSmoothing(
            values,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_period,
        ).fit(optimized=True)

        forecast = model.forecast(horizon_days)
        fitted = model.fittedvalues
        residuals = np.array(values) - np.array(fitted)
        residual_std = float(np.std(residuals, ddof=1))

        abs_errors = np.abs(residuals)
        mae = float(np.mean(abs_errors))
        y = np.array(values, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            pct_errors = np.where(y != 0, abs_errors / np.abs(y), 0)
        mape = float(np.mean(pct_errors))

        base_date = last_date or date.today()
        points = []
        for i, val in enumerate(forecast):
            step = i + 1
            margin = 1.96 * residual_std * np.sqrt(step)
            points.append({
                "date": str(base_date + timedelta(days=step)),
                "predicted": round(max(float(val), 0), 4),
                "lower": round(max(float(val) - margin, 0), 4),
                "upper": round(float(val) + margin, 4),
            })

        return ForecastResult(
            method="holt_winters",
            points=points,
            mape=round(mape, 4),
            mae=round(mae, 4),
        )
    except Exception:
        log.exception("holt_winters_failed")
        return None


async def run_forecast(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    forecast_type: str = "cost_daily",
    horizon_days: int = 14,
    dimension_key: str | None = None,
) -> MLForecast | None:
    """Run forecasting, pick the best method, and store the result."""
    dimension = forecast_type.replace("_daily", "")
    series = await load_feature_series(db, workspace_id, dimension, dimension_key, days=60)

    if len(series) < 7:
        return None

    dates = [row["date"] for row in series]
    values = [row["features"].get("value", 0) for row in series]

    linear_result = forecast_linear(dates, values, horizon_days)
    hw_result = forecast_holt_winters(values, horizon_days, last_date=dates[-1])

    best: ForecastResult
    if hw_result and hw_result.mape < linear_result.mape:
        best = hw_result
    else:
        best = linear_result

    forecast = MLForecast(
        workspace_id=workspace_id,
        forecast_type=forecast_type,
        dimension_key=dimension_key,
        method=best.method,
        horizon_days=horizon_days,
        forecast_from=dates[-1],
        points=best.points,
        accuracy_metrics={
            "mape": best.mape,
            "mae": best.mae,
            "r_squared": best.r_squared,
        },
    )
    db.add(forecast)
    await db.flush()
    log.info("forecast_created", workspace_id=str(workspace_id), method=best.method, mape=best.mape)
    return forecast


async def forecast_with_budget(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    horizon_days: int = 30,
) -> dict[str, Any] | None:
    """Run cost forecast and overlay workspace budget for breach analysis."""
    from runledger_api.models.budgets import Budget

    forecast = await run_forecast(db, workspace_id, "cost_daily", horizon_days)
    if not forecast:
        return None

    result = await db.execute(
        select(Budget).where(
            Budget.workspace_id == workspace_id,
            Budget.scope_type == "workspace",
        ).limit(1)
    )
    budget = result.scalar_one_or_none()
    budget_limit = float(budget.limit_usd) if budget else None

    projected_spend = sum(p.get("predicted", 0) for p in forecast.points)
    days_to_exhaustion = None
    exhaustion_date = None

    if budget_limit:
        cumulative = 0.0
        for i, p in enumerate(forecast.points):
            cumulative += p.get("predicted", 0)
            if cumulative >= budget_limit:
                days_to_exhaustion = i + 1
                exhaustion_date = p["date"]
                break

    return {
        "forecast_id": str(forecast.id),
        "budget_limit": str(budget_limit) if budget_limit else None,
        "projected_spend": round(projected_spend, 2),
        "days_to_exhaustion": days_to_exhaustion,
        "exhaustion_date": exhaustion_date,
        "breach_probability": min(projected_spend / budget_limit, 1.0) if budget_limit else None,
    }

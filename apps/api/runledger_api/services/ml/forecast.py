"""Cost and token forecasting — linear, Holt-Winters, Prophet-style decomposition, and ARIMA.

All methods produce point forecasts with confidence intervals. The
orchestrator runs all applicable methods, picks the one with lowest
in-sample MAPE, and stores the result.
"""

from __future__ import annotations

import uuid
import warnings
from dataclasses import dataclass, field
from datetime import date, timedelta
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

    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    last_date = dates[-1]
    points = []
    for d in range(1, horizon_days + 1):
        future_x = n + d - 1
        predicted = slope * future_x + intercept
        prediction_var = 1 + 1 / n + (future_x - np.mean(x)) ** 2 / np.sum((x - np.mean(x)) ** 2)
        margin_95 = 1.96 * residual_std * np.sqrt(prediction_var)
        points.append(
            {
                "date": str(last_date + timedelta(days=d)),
                "predicted": round(max(predicted, 0), 4),
                "lower": round(max(predicted - margin_95, 0), 4),
                "upper": round(predicted + margin_95, 4),
            }
        )

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
            points.append(
                {
                    "date": str(base_date + timedelta(days=step)),
                    "predicted": round(max(float(val), 0), 4),
                    "lower": round(max(float(val) - margin, 0), 4),
                    "upper": round(float(val) + margin, 4),
                }
            )

        return ForecastResult(
            method="holt_winters",
            points=points,
            mape=round(mape, 4),
            mae=round(mae, 4),
        )
    except Exception:
        log.exception("holt_winters_failed")
        return None


def forecast_prophet_style(
    dates: list[date],
    values: list[float],
    horizon_days: int = 14,
    seasonal_period: int = 7,
) -> ForecastResult | None:
    """Prophet-style additive decomposition forecast.

    Decomposes the series via STL into trend, seasonal, and residual
    components, then extrapolates trend via linear regression and
    repeats the seasonal cycle forward. Confidence intervals are
    derived from the residual standard deviation.
    """
    n = len(values)
    if n < 2 * seasonal_period + 1:
        return None

    try:
        from statsmodels.tsa.seasonal import STL

        y = np.array(values, dtype=np.float64)
        stl_result = STL(y, period=seasonal_period, robust=True).fit()

        trend = np.array(stl_result.trend, dtype=np.float64)
        seasonal = np.array(stl_result.seasonal, dtype=np.float64)
        residual = np.array(stl_result.resid, dtype=np.float64)

        residual_std = float(np.std(residual, ddof=1))

        x = np.arange(n, dtype=np.float64)
        trend_coeffs = np.polyfit(x, trend, 1)
        trend_slope, trend_intercept = trend_coeffs[0], trend_coeffs[1]

        fitted = trend + seasonal
        abs_errors = np.abs(y - fitted)
        mae = float(np.mean(abs_errors))
        with np.errstate(divide="ignore", invalid="ignore"):
            pct_errors = np.where(y != 0, abs_errors / np.abs(y), 0)
        mape = float(np.mean(pct_errors))

        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        last_date = dates[-1]
        points = []
        for d in range(1, horizon_days + 1):
            future_x = n + d - 1
            future_trend = trend_slope * future_x + trend_intercept
            seasonal_idx = (n + d - 1) % seasonal_period
            future_seasonal = float(seasonal[seasonal_idx])
            predicted = future_trend + future_seasonal
            margin = 1.96 * residual_std * np.sqrt(d)
            points.append(
                {
                    "date": str(last_date + timedelta(days=d)),
                    "predicted": round(max(float(predicted), 0), 4),
                    "lower": round(max(float(predicted) - margin, 0), 4),
                    "upper": round(float(predicted) + margin, 4),
                }
            )

        return ForecastResult(
            method="prophet_style",
            points=points,
            mape=round(mape, 4),
            mae=round(mae, 4),
            r_squared=round(r_squared, 4),
        )
    except Exception:
        log.exception("prophet_style_failed")
        return None


def _arima_select_order(
    y: np.ndarray[Any, np.dtype[np.float64]],
    max_p: int = 3,
    max_d: int = 2,
    max_q: int = 3,
) -> tuple[int, int, int]:
    """Grid-search ARIMA(p,d,q) orders and return the one with lowest AIC."""
    from statsmodels.tsa.arima.model import ARIMA as StatsARIMA

    best_aic = np.inf
    best_order: tuple[int, int, int] = (1, 0, 0)

    for d in range(max_d + 1):
        for p in range(max_p + 1):
            for q in range(max_q + 1):
                if p == 0 and q == 0:
                    continue
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = StatsARIMA(y, order=(p, d, q)).fit(method="innovations_mle")
                    if model.aic < best_aic:
                        best_aic = model.aic
                        best_order = (p, d, q)
                except Exception:
                    continue

    return best_order


def forecast_arima(
    dates: list[date],
    values: list[float],
    horizon_days: int = 14,
) -> ForecastResult | None:
    """ARIMA forecast with automatic order selection via AIC grid search.

    Best suited for stationary or near-stationary series where seasonal
    patterns are weak. The differencing order (d) handles non-stationarity.
    """
    n = len(values)
    if n < 10:
        return None

    try:
        from statsmodels.tsa.arima.model import ARIMA as StatsARIMA

        y = np.array(values, dtype=np.float64)

        order = _arima_select_order(y)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = StatsARIMA(y, order=order).fit(method="innovations_mle")

        forecast_obj = model.get_forecast(steps=horizon_days)
        predicted_mean = np.asarray(forecast_obj.predicted_mean)
        conf_int = np.asarray(forecast_obj.conf_int(alpha=0.05))

        fitted = np.asarray(model.fittedvalues)
        abs_errors = np.abs(y[1:] - fitted[1:])
        mae = float(np.mean(abs_errors))
        with np.errstate(divide="ignore", invalid="ignore"):
            pct_errors = np.where(y[1:] != 0, abs_errors / np.abs(y[1:]), 0)
        mape = float(np.mean(pct_errors))

        ss_res = float(np.sum((y[1:] - fitted[1:]) ** 2))
        ss_tot = float(np.sum((y[1:] - np.mean(y[1:])) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        last_date = dates[-1]
        points = []
        for i in range(horizon_days):
            pred = float(predicted_mean[i])
            lower = float(conf_int[i, 0])
            upper = float(conf_int[i, 1])
            points.append(
                {
                    "date": str(last_date + timedelta(days=i + 1)),
                    "predicted": round(max(pred, 0), 4),
                    "lower": round(max(lower, 0), 4),
                    "upper": round(upper, 4),
                }
            )

        return ForecastResult(
            method="arima",
            points=points,
            mape=round(mape, 4),
            mae=round(mae, 4),
            r_squared=round(r_squared, 4),
        )
    except Exception:
        log.exception("arima_failed")
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

    candidates: list[ForecastResult] = [forecast_linear(dates, values, horizon_days)]

    hw_result = forecast_holt_winters(values, horizon_days, last_date=dates[-1])
    if hw_result:
        candidates.append(hw_result)

    prophet_result = forecast_prophet_style(dates, values, horizon_days)
    if prophet_result:
        candidates.append(prophet_result)

    arima_result = forecast_arima(dates, values, horizon_days)
    if arima_result:
        candidates.append(arima_result)

    best = min(candidates, key=lambda r: r.mape)

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
        select(Budget)
        .where(
            Budget.workspace_id == workspace_id,
            Budget.scope_type == "workspace",
        )
        .limit(1)
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

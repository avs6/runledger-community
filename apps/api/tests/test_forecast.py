"""Unit tests for Prophet-style decomposition and ARIMA forecasting."""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
from runledger_api.services.ml.forecast import (
    forecast_arima,
    forecast_linear,
    forecast_prophet_style,
)


def _make_series(
    n: int = 30,
    base: float = 10.0,
    trend: float = 0.1,
    seasonal_amplitude: float = 2.0,
    seasonal_period: int = 7,
    noise_scale: float = 0.3,
    seed: int = 42,
) -> tuple[list[date], list[float]]:
    """Generate a synthetic series with trend + weekly seasonality + noise."""
    rng = np.random.default_rng(seed)
    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n)]
    values = [
        base
        + trend * i
        + seasonal_amplitude * math.sin(2 * math.pi * i / seasonal_period)
        + rng.normal(0, noise_scale)
        for i in range(n)
    ]
    return dates, values


def _make_stationary_series(
    n: int = 40,
    mean: float = 50.0,
    noise_scale: float = 2.0,
    seed: int = 42,
) -> tuple[list[date], list[float]]:
    """Generate a stationary series around a constant mean."""
    rng = np.random.default_rng(seed)
    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(n)]
    values = [mean + rng.normal(0, noise_scale) for _ in range(n)]
    return dates, values


# ── Prophet-style tests ────────────────────────────────────────────────


class TestProphetStyle:
    def test_returns_forecast_points(self) -> None:
        dates, values = _make_series(n=30)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is not None
        assert result.method == "prophet_style"
        assert len(result.points) == 7

    def test_returns_none_when_too_few_observations(self) -> None:
        dates, values = _make_series(n=10)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is None

    def test_forecast_dates_are_sequential(self) -> None:
        dates, values = _make_series(n=30)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is not None
        forecast_dates = [p["date"] for p in result.points]
        last = dates[-1]
        for i, d in enumerate(forecast_dates):
            assert d == str(last + timedelta(days=i + 1))

    def test_confidence_intervals_ordered(self) -> None:
        dates, values = _make_series(n=30)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is not None
        for p in result.points:
            assert p["lower"] <= p["predicted"] <= p["upper"]

    def test_accuracy_metrics_computed(self) -> None:
        dates, values = _make_series(n=30)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is not None
        assert 0 <= result.mape <= 1
        assert result.mae > 0
        assert result.r_squared > 0

    def test_captures_trend(self) -> None:
        dates, values = _make_series(n=40, trend=0.5, seasonal_amplitude=0)
        result = forecast_prophet_style(dates, values, horizon_days=7)
        assert result is not None
        predictions = [p["predicted"] for p in result.points]
        assert predictions[-1] > predictions[0]


# ── ARIMA tests ────────────────────────────────────────────────────────


class TestARIMA:
    def test_returns_forecast_points(self) -> None:
        dates, values = _make_stationary_series(n=40)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is not None
        assert result.method == "arima"
        assert len(result.points) == 7

    def test_returns_none_when_too_few_observations(self) -> None:
        dates, values = _make_stationary_series(n=5)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is None

    def test_forecast_dates_are_sequential(self) -> None:
        dates, values = _make_stationary_series(n=40)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is not None
        last = dates[-1]
        for i, p in enumerate(result.points):
            assert p["date"] == str(last + timedelta(days=i + 1))

    def test_confidence_intervals_ordered(self) -> None:
        dates, values = _make_stationary_series(n=40)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is not None
        for p in result.points:
            assert p["lower"] <= p["predicted"] <= p["upper"]

    def test_stationary_predictions_near_mean(self) -> None:
        mean = 50.0
        dates, values = _make_stationary_series(n=60, mean=mean)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is not None
        for p in result.points:
            assert abs(p["predicted"] - mean) < 15

    def test_trended_series(self) -> None:
        dates, values = _make_series(n=40, trend=1.0, seasonal_amplitude=0)
        result = forecast_arima(dates, values, horizon_days=7)
        assert result is not None
        last_actual = values[-1]
        assert result.points[-1]["predicted"] > last_actual * 0.5


# ── Orchestrator competition tests ─────────────────────────────────────


class TestMethodCompetition:
    def test_all_methods_produce_results_for_seasonal_data(self) -> None:
        dates, values = _make_series(n=40, seasonal_amplitude=3.0)
        linear = forecast_linear(dates, values, horizon_days=7)
        prophet = forecast_prophet_style(dates, values, horizon_days=7)
        arima = forecast_arima(dates, values, horizon_days=7)
        assert linear is not None
        assert prophet is not None
        assert arima is not None

    def test_prophet_beats_linear_on_seasonal_data(self) -> None:
        dates, values = _make_series(n=40, seasonal_amplitude=5.0, noise_scale=0.1)
        linear = forecast_linear(dates, values, horizon_days=7)
        prophet = forecast_prophet_style(dates, values, horizon_days=7)
        assert prophet is not None
        assert prophet.mape <= linear.mape

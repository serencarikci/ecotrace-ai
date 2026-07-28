# Forecasting

Methods: linear trend, moving average, weighted moving average, seasonal naive, simple exponential smoothing (optional Holt variants when configured).

Accuracy: MAE, RMSE, MAPE (zero-safe), sMAPE. Backtesting holds out recent periods. Target trajectory labels are projections (`likely_on_track`, `potentially_at_risk`, `likely_off_track`, `insufficient_data`), not guarantees.

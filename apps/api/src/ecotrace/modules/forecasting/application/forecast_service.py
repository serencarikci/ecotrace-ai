from __future__ import annotations
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.core.intelligence_constants import FORECAST_ENGINE_VERSION, FORECAST_METHODS
from ecotrace.modules.forecasting.application.methods import accuracy_bundle, d, run_method, select_method, target_trajectory_label
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import ForecastDefinition, ForecastPoint, ForecastRun
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_manage, require_automation_read, require_automation_write

def list_definitions(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(ForecastDefinition).where(ForecastDefinition.organization_id == organization_id)).scalars()
    return [_ser_def(r) for r in rows]

def create_definition(db: Session, user: User, organization_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    method = str(payload.get('method') or 'linear_trend')
    if method not in FORECAST_METHODS and method != 'auto':
        raise ValidationAppError('Unsupported forecast method.')
    row = ForecastDefinition(organization_id=organization_id, code=str(payload['code']), name=str(payload['name']), metric_type=str(payload.get('metricType') or 'total_emissions'), entity_type=str(payload.get('entityType') or 'organization'), entity_id=uuid.UUID(payload['entityId']) if payload.get('entityId') else None, method=method, historical_period_count=int(payload.get('historicalPeriodCount') or 12), forecast_horizon=int(payload.get('forecastHorizon') or 6), granularity=str(payload.get('granularity') or 'monthly'), configuration_json=payload.get('configuration') or {}, is_active=True)
    db.add(row)
    db.flush()
    write_audit_log(db, action='forecast.definition.created', actor_user_id=user.id, organization_id=organization_id, entity_type='forecast_definition', entity_id=str(row.id))
    return _ser_def(row)

def get_definition(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser_def(_get_def(db, organization_id, definition_id))

def update_definition(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get_def(db, organization_id, definition_id)
    for key, attr in {'name': 'name', 'method': 'method', 'forecastHorizon': 'forecast_horizon', 'historicalPeriodCount': 'historical_period_count', 'isActive': 'is_active', 'configuration': 'configuration_json'}.items():
        if key in payload:
            setattr(row, attr, payload[key])
    db.flush()
    return _ser_def(row)

def run_forecast(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID, *, backtest: bool=True) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    definition = _get_def(db, organization_id, definition_id)
    series = _load_series(db, organization_id, definition.metric_type)
    if len(series) < 3:
        raise ValidationAppError('Insufficient historical data for forecasting.')
    method = definition.method
    if method == 'auto':
        method = select_method(series)
    metrics: dict[str, Any] = {}
    if backtest and len(series) >= 6:
        hold = min(3, len(series) // 4 or 1)
        train, actual = (series[:-hold], series[-hold:])
        predicted = run_method(method, train, hold)
        accuracy = accuracy_bundle(actual, predicted)
        metrics = {**accuracy, 'selectedMethod': method, 'selectionStrategy': 'Hold out recent periods and minimize MAE among supported deterministic models.'}
    horizon = definition.forecast_horizon
    preds = run_method(method, series, horizon)
    today = date.today().replace(day=1)
    run = ForecastRun(organization_id=organization_id, forecast_definition_id=definition.id, status='completed', training_start_date=today - timedelta(days=30 * len(series)), training_end_date=today, forecast_start_date=today + timedelta(days=30), forecast_end_date=today + timedelta(days=30 * horizon), model_version=FORECAST_ENGINE_VERSION, data_point_count=len(series), accuracy_metrics_json=metrics, source_data_quality='provisional', generated_at=datetime.now(UTC), triggered_by_user_id=user.id)
    db.add(run)
    db.flush()
    for i, value in enumerate(preds):
        start = today + timedelta(days=30 * (i + 1))
        end = start + timedelta(days=29)
        band = abs(value) * 0.1
        db.add(ForecastPoint(forecast_run_id=run.id, period_start=start, period_end=end, predicted_value=d(value), lower_bound=d(value - band), upper_bound=d(value + band)))
    write_audit_log(db, action='forecast.run.completed', actor_user_id=user.id, organization_id=organization_id, entity_type='forecast_run', entity_id=str(run.id))
    db.flush()
    return get_run(db, user, organization_id, run.id)

def list_runs(db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(ForecastRun).where(ForecastRun.organization_id == organization_id, ForecastRun.forecast_definition_id == definition_id).order_by(ForecastRun.created_at.desc())).scalars()
    return [_ser_run(r) for r in rows]

def get_run(db: Session, user: User, organization_id: uuid.UUID, run_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    row = db.execute(select(ForecastRun).where(ForecastRun.id == run_id, ForecastRun.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Forecast run not found.')
    return _ser_run(row)

def get_points(db: Session, user: User, organization_id: uuid.UUID, run_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    get_run(db, user, organization_id, run_id)
    rows = db.execute(select(ForecastPoint).where(ForecastPoint.forecast_run_id == run_id).order_by(ForecastPoint.period_start.asc())).scalars()
    return [{'id': str(p.id), 'periodStart': p.period_start.isoformat(), 'periodEnd': p.period_end.isoformat(), 'predictedValue': float(p.predicted_value), 'lowerBound': float(p.lower_bound) if p.lower_bound is not None else None, 'upperBound': float(p.upper_bound) if p.upper_bound is not None else None, 'actualValue': float(p.actual_value) if p.actual_value is not None else None} for p in rows]

def target_trajectory(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    from ecotrace.modules.sustainability_targets.infrastructure.models import SustainabilityTarget
    target = db.execute(select(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id, SustainabilityTarget.status.in_(['active', 'approved', 'draft'])).order_by(SustainabilityTarget.updated_at.desc()).limit(1)).scalar_one_or_none()
    series = _load_series(db, organization_id, 'total_emissions')
    if target is None or len(series) < 3:
        return {'label': 'insufficient_data', 'disclaimer': 'Model-based projection only; not a guarantee.'}
    preds = run_method('linear_trend', series, 12)
    current = series[0]
    target_value = float(getattr(target, 'target_value', None) or getattr(target, 'absolute_target_value', None) or current * 0.7)
    label = target_trajectory_label(current=current, target=target_value, forecast_at_target=preds[-1], periods_remaining=12)
    gap = preds[-1] - target_value
    monthly = gap / 12 if 12 else None
    return {'targetId': str(target.id), 'targetName': target.name, 'currentValue': current, 'targetValue': target_value, 'forecastAtTargetDate': preds[-1], 'expectedGap': gap, 'requiredMonthlyImprovement': monthly, 'label': label, 'disclaimer': 'Model-based projection only; not a statistical probability or guarantee.'}

def _load_series(db: Session, organization_id: uuid.UUID, metric_type: str) -> list[float]:
    _ = metric_type
    from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationRun, CarbonInventory
    runs = list(db.execute(select(CarbonCalculationRun).join(CarbonInventory, CarbonCalculationRun.inventory_id == CarbonInventory.id).where(CarbonInventory.organization_id == organization_id).order_by(CarbonCalculationRun.created_at.asc()).limit(36)).scalars())
    chrono: list[float] = []
    for r in runs:
        value = r.total_kg_co2e
        if value is not None:
            chrono.append(float(value))
    if chrono:
        return chrono
    from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
    acts = list(db.execute(select(ActivityRecord).where(ActivityRecord.organization_id == organization_id).order_by(ActivityRecord.created_at.asc()).limit(24)).scalars())
    return [float(a.quantity) for a in acts if getattr(a, 'quantity', None) is not None]

def _get_def(db: Session, organization_id: uuid.UUID, definition_id: uuid.UUID) -> ForecastDefinition:
    row = db.execute(select(ForecastDefinition).where(ForecastDefinition.id == definition_id, ForecastDefinition.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Forecast definition not found.')
    return row

def _ser_def(row: ForecastDefinition) -> dict[str, Any]:
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'metricType': row.metric_type, 'entityType': row.entity_type, 'entityId': str(row.entity_id) if row.entity_id else None, 'method': row.method, 'historicalPeriodCount': row.historical_period_count, 'forecastHorizon': row.forecast_horizon, 'granularity': row.granularity, 'isActive': row.is_active, 'disclaimer': 'Forecasts are estimates only.'}

def _ser_run(row: ForecastRun) -> dict[str, Any]:
    return {'id': str(row.id), 'forecastDefinitionId': str(row.forecast_definition_id), 'status': row.status, 'modelVersion': row.model_version, 'dataPointCount': row.data_point_count, 'accuracyMetrics': row.accuracy_metrics_json, 'sourceDataQuality': row.source_data_quality, 'generatedAt': row.generated_at.isoformat() if row.generated_at else None, 'disclaimer': row.disclaimer, 'forecastStartDate': row.forecast_start_date.isoformat() if row.forecast_start_date else None, 'forecastEndDate': row.forecast_end_date.isoformat() if row.forecast_end_date else None}

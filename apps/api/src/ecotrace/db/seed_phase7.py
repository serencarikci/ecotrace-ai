from __future__ import annotations
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.modules.agents.application.agent_service import ensure_catalog
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.production_operations.infrastructure.models import AnomalyDetectionRule, AutomationRule, ForecastDefinition, OrganizationRegulatoryAssessment, RegulatoryDocument, SupplierAssessment, SupplierMonitoringProfile
from ecotrace.modules.suppliers.infrastructure.models import Supplier

def seed_phase7(session: Session, org: Organization, actor: User) -> None:
    ensure_catalog(session)
    _seed_automation(session, org, actor)
    _seed_anomaly_rules(session, org)
    _seed_forecasts(session, org)
    _seed_supplier_monitoring(session, org, actor)
    _seed_regulatory(session, org, actor)

def _seed_automation(session: Session, org: Organization, actor: User) -> None:
    specs = [('weekly-anomaly-scan', 'Weekly anomaly scan', 'weekly_anomaly_scan', 'schedule', {'expression': 'weekly', 'weekday': 1}, 'run_anomaly_detection', {}), ('monthly-exec-report', 'Monthly executive sustainability report', 'monthly_carbon_report', 'schedule', {'expression': 'monthly', 'day': 1}, 'generate_report', {'reportType': 'executive_sustainability_summary'}), ('daily-dq-scan', 'Daily data quality scan', 'daily_data_quality_scan', 'schedule', {'expression': 'daily'}, 'run_data_quality_scan', {}), ('target-offtrack-alert', 'Target off-track alert', 'target_risk_alert', 'schedule', {'expression': 'weekly'}, 'create_alert', {'alertType': 'target_risk'}), ('quarterly-supplier-review', 'Quarterly supplier review', 'quarterly_supplier_review', 'schedule', {'expression': 'quarterly'}, 'start_agent_execution', {'agentCode': 'supplier_review'}), ('regulatory-effective-alert', 'Regulatory effective-date alert', 'regulatory_effective_date_alert', 'schedule', {'expression': 'daily'}, 'create_alert', {'alertType': 'document_expiration'})]
    for code, name, _tpl, trigger, tcfg, action, acfg in specs:
        exists = session.execute(select(AutomationRule.id).where(AutomationRule.organization_id == org.id, AutomationRule.code == code)).scalar_one_or_none()
        if exists:
            continue
        session.add(AutomationRule(organization_id=org.id, code=code, name=name, description=f'Demo automation: {name}', trigger_type=trigger, trigger_config_json=tcfg, condition_config_json={}, action_type=action, action_config_json=acfg, approval_required=False, status='active', created_by_user_id=actor.id, next_run_at=datetime.now(UTC) + timedelta(days=1)))
    session.flush()

def _seed_anomaly_rules(session: Session, org: Organization) -> None:
    rules = [('elec-spike', 'Electricity consumption spike', 'activity_quantity', 'z_score', {'z': 2.5}), ('missing-gas', 'Missing monthly natural gas record', 'missing_expected_data', 'expected_frequency', {'expectedDays': 35}), ('intensity-up', 'Carbon intensity increase', 'carbon_intensity', 'percentage_change', {'pct': 25.0}), ('import-fail-freq', 'Import failure frequency', 'import_failures', 'percentage_change', {'pct': 50.0}), ('target-traj-dev', 'Target trajectory deviation', 'target_trajectory', 'percentage_change', {'pct': 15.0})]
    for code, name, metric, method, thr in rules:
        exists = session.execute(select(AnomalyDetectionRule.id).where(AnomalyDetectionRule.organization_id == org.id, AnomalyDetectionRule.code == code)).scalar_one_or_none()
        if exists:
            continue
        session.add(AnomalyDetectionRule(organization_id=org.id, code=code, name=name, description=f'Demo anomaly rule: {name}', metric_type=metric, detection_method=method, threshold_config_json=thr, scope_config_json={}, severity_mapping_json={}, minimum_data_points=5, lookback_period=12, is_active=True))
    session.flush()

def _seed_forecasts(session: Session, org: Organization) -> None:
    defs = [('total-emissions-fc', 'Total emissions forecast', 'total_emissions', 'linear_trend'), ('scope2-fc', 'Scope 2 forecast', 'scope_2_emissions', 'moving_average'), ('elec-fc', 'Electricity consumption forecast', 'energy_consumption', 'weighted_moving_average'), ('intensity-fc', 'Carbon intensity forecast', 'carbon_intensity', 'simple_exponential_smoothing'), ('target-2030-fc', '2030 target trajectory forecast', 'target_trajectory', 'linear_trend')]
    for code, name, metric, method in defs:
        exists = session.execute(select(ForecastDefinition.id).where(ForecastDefinition.organization_id == org.id, ForecastDefinition.code == code)).scalar_one_or_none()
        if exists:
            continue
        session.add(ForecastDefinition(organization_id=org.id, code=code, name=name, metric_type=metric, entity_type='organization', method=method, historical_period_count=12, forecast_horizon=6, granularity='monthly', configuration_json={'demo': True}, is_active=True))
    session.flush()

def _seed_supplier_monitoring(session: Session, org: Organization, actor: User) -> None:
    suppliers = list(session.execute(select(Supplier).where(Supplier.organization_id == org.id).limit(3)).scalars())
    if not suppliers:
        return
    for idx, supplier in enumerate(suppliers):
        exists = session.execute(select(SupplierMonitoringProfile.id).where(SupplierMonitoringProfile.organization_id == org.id, SupplierMonitoringProfile.supplier_id == supplier.id)).scalar_one_or_none()
        if exists:
            continue
        overdue = idx == 0
        session.add(SupplierMonitoringProfile(organization_id=org.id, supplier_id=supplier.id, monitoring_status='active', risk_level='medium' if overdue else 'low', required_document_types_json=['iso14001', 'ghg_inventory'], review_frequency='quarterly', last_reviewed_at=datetime.now(UTC) - timedelta(days=200 if overdue else 30), next_review_at=datetime.now(UTC) - timedelta(days=10) if overdue else datetime.now(UTC) + timedelta(days=60), assigned_to_user_id=actor.id))
        session.add(SupplierAssessment(organization_id=org.id, supplier_id=supplier.id, assessment_date=date.today() - timedelta(days=30), assessment_type='internal', emissions_score=Decimal('72.5'), data_quality_score=Decimal('68.0'), document_completeness_score=Decimal('55.0' if overdue else '80.0'), sustainability_score=Decimal('65.0'), risk_level='medium' if overdue else 'low', findings_json={'disclaimer': 'Internal non-certified assessment.', 'notes': 'Demo assessment only.'}, recommendations_json={'items': ['Request updated GHG inventory']}, assessed_by_user_id=actor.id, status='completed'))
    session.flush()

def _seed_regulatory(session: Session, org: Organization, actor: User) -> None:
    docs = [('EU', 'European Commission', 'DEMO-CSRD-2024', 'Demo CSRD overview (not legal guidance)', 'disclosure'), ('TR', 'Demo Authority', 'DEMO-TR-CLIMATE-1', 'Demo Türkiye climate reporting note', 'climate')]
    created: list[RegulatoryDocument] = []
    for jur, auth, code, title, cat in docs:
        existing = session.execute(select(RegulatoryDocument).where(RegulatoryDocument.regulation_code == code)).scalar_one_or_none()
        if existing:
            created.append(existing)
            continue
        row = RegulatoryDocument(jurisdiction_code=jur, authority_name=auth, regulation_code=code, title=title, description='DEMO DATA ONLY. Not current legal guidance. This module does not provide legal advice or guarantee compliance.', category=cat, source_url='https://example.com/demo-regulatory', published_at=date.today() - timedelta(days=90), effective_from=date.today() + timedelta(days=60), version='1.0-demo', status='published', is_demo=True)
        session.add(row)
        session.flush()
        created.append(row)
    if not created:
        return
    first = created[0]
    exists = session.execute(select(OrganizationRegulatoryAssessment.id).where(OrganizationRegulatoryAssessment.organization_id == org.id, OrganizationRegulatoryAssessment.regulatory_document_id == first.id)).scalar_one_or_none()
    if not exists:
        session.add(OrganizationRegulatoryAssessment(organization_id=org.id, regulatory_document_id=first.id, applicability_status='potentially_applicable', relevance_score=Decimal('0.72'), review_status='action_required', assigned_to_user_id=actor.id, assessment_notes='Demo assessment — human review required.', impact_summary='Potential disclosure process impact (demo).', action_required=True, due_date=date.today() + timedelta(days=30)))
        session.flush()

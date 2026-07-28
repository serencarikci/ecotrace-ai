from __future__ import annotations
from typing import Final
PHASE7_ENGINE_VERSION: Final[str] = 'ecotrace-phase7-0.7.1'
FORECAST_ENGINE_VERSION: Final[str] = 'ecotrace-forecast-0.7.1'
ANOMALY_ENGINE_VERSION: Final[str] = 'ecotrace-anomaly-0.7.1'
AGENT_CODES: Final[frozenset[str]] = frozenset({'carbon_analysis', 'data_quality', 'target_monitoring', 'report_generation', 'supplier_review', 'regulatory_document'})
READ_ONLY_TOOLS: Final[frozenset[str]] = frozenset({'get_carbon_inventory_summary', 'compare_carbon_inventories', 'get_facility_emissions', 'get_activity_records', 'get_anomaly_results', 'get_target_progress', 'get_scenario_results', 'get_lca_results', 'get_product_footprint', 'get_digital_product_passport', 'search_organization_documents', 'retrieve_cited_evidence', 'get_supplier_sustainability_data', 'get_data_quality_issues', 'get_scheduled_report_status'})
CONTROLLED_WRITE_TOOLS: Final[frozenset[str]] = frozenset({'create_draft_report', 'create_draft_recommendation', 'create_draft_anomaly_investigation', 'create_draft_target_review', 'create_draft_automation_rule', 'acknowledge_alert', 'assign_alert', 'create_draft_corrective_action'})
FORBIDDEN_AGENT_ACTIONS: Final[frozenset[str]] = frozenset({'delete_records', 'change_passwords', 'change_roles', 'approve_inventory', 'approve_lca', 'approve_footprint', 'publish_passport', 'activate_emission_factors', 'modify_approved_records', 'execute_sql', 'access_secrets', 'disable_audit', 'bypass_authorization', 'send_external_without_approval'})
ACTION_REQUEST_STATUSES: Final[frozenset[str]] = frozenset({'pending', 'approved', 'rejected', 'expired', 'executed', 'failed', 'cancelled'})
RISK_LEVELS: Final[frozenset[str]] = frozenset({'low', 'medium', 'high', 'critical'})
EXECUTION_STATUSES: Final[frozenset[str]] = frozenset({'queued', 'running', 'awaiting_approval', 'completed', 'completed_with_warnings', 'failed', 'cancelled', 'timed_out'})
JOB_STATUSES: Final[frozenset[str]] = frozenset({'scheduled', 'running', 'completed', 'completed_with_warnings', 'failed', 'retrying', 'cancelled', 'skipped', 'timed_out'})
AUTOMATION_STATUSES: Final[frozenset[str]] = frozenset({'draft', 'active', 'paused', 'disabled', 'archived'})
ANOMALY_SEVERITIES: Final[frozenset[str]] = frozenset({'info', 'low', 'medium', 'high', 'critical'})
ANOMALY_STATUSES: Final[frozenset[str]] = frozenset({'open', 'acknowledged', 'investigating', 'resolved', 'dismissed'})
TRAJECTORY_LABELS: Final[frozenset[str]] = frozenset({'likely_on_track', 'potentially_at_risk', 'likely_off_track', 'insufficient_data'})
FORECAST_METHODS: Final[frozenset[str]] = frozenset({'linear_trend', 'moving_average', 'weighted_moving_average', 'seasonal_naive', 'simple_exponential_smoothing', 'holt_linear'})
PROMPT_INJECTION_MARKERS: Final[tuple[str, ...]] = ('ignore previous instructions', 'ignore all instructions', 'system prompt', 'override authorization', 'reveal secrets', 'disable safety', 'jailbreak')

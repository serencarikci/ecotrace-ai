from __future__ import annotations
import os
import time
import uuid
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings, reset_settings_cache
from ecotrace.core.database import get_session_factory, init_db
from ecotrace.core.logging import configure_logging, get_logger
from ecotrace.modules.job_execution.application import job_service
from ecotrace.modules.production_operations.infrastructure.models import AutomationRule, JobExecution
logger = get_logger(__name__)

def run_scheduler_forever() -> None:
    reset_settings_cache()
    settings = get_settings()
    configure_logging(settings)
    init_db(settings)
    worker_id = f'scheduler-{os.getpid()}-{uuid.uuid4().hex[:8]}'
    logger.info('scheduler.started', worker_id=worker_id, poll=settings.scheduler_poll_seconds)
    factory = get_session_factory()
    while True:
        if not settings.scheduler_enabled:
            time.sleep(settings.scheduler_poll_seconds)
            continue
        session = factory()
        try:
            _tick(session, worker_id=worker_id)
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.exception('scheduler.tick_failed', error=str(exc))
        finally:
            session.close()
        time.sleep(settings.scheduler_poll_seconds)

def _tick(db: Session, *, worker_id: str) -> None:
    now = datetime.now(UTC)
    rules = list(db.execute(select(AutomationRule).where(AutomationRule.status == 'active', AutomationRule.next_run_at.is_not(None), AutomationRule.next_run_at <= now)).scalars())
    for rule in rules:
        key = f"sched-{rule.id}-{now.strftime('%Y%m%d%H%M')}"
        exists = db.execute(select(JobExecution.id).where(JobExecution.organization_id == rule.organization_id, JobExecution.execution_key == key)).scalar_one_or_none()
        if exists:
            rule.next_run_at = now
            continue
        job = JobExecution(organization_id=rule.organization_id, job_type=f'automation:{rule.action_type}', job_reference_id=rule.id, execution_key=key, status='scheduled', scheduled_for=now, attempt_number=1, max_attempts=get_settings().job_max_attempts, worker_id=worker_id, trace_id=uuid.uuid4().hex, result_summary_json={'note': 'Due automation captured by scheduler. Trigger manual run or API worker.', 'ruleCode': rule.code})
        db.add(job)
        if not job_service.try_acquire_lock(db, job, worker_id):
            continue
        job.status = 'completed'
        job.completed_at = datetime.now(UTC)
        from ecotrace.modules.automation.application.automation_service import _next_run
        rule.last_run_at = now
        rule.next_run_at = _next_run(rule.trigger_type, rule.trigger_config_json or {})
        logger.info('scheduler.automation_due', rule_id=str(rule.id), organization_id=str(rule.organization_id))

def main() -> None:
    run_scheduler_forever()
if __name__ == '__main__':
    main()

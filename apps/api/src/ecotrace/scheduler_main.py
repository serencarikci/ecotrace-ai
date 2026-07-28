from __future__ import annotations
from ecotrace.core.config import get_settings
from ecotrace.core.logging import configure_logging, get_logger
from ecotrace.modules.job_execution.application.scheduler_worker import run_scheduler_forever

def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info('scheduler.starting', enabled=settings.scheduler_enabled, poll_seconds=settings.scheduler_poll_seconds)
    if not settings.scheduler_enabled:
        logger.warning('scheduler.disabled')
        return
    run_scheduler_forever()
if __name__ == '__main__':
    main()

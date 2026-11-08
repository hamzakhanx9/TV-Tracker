import logging
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs import generate_notifications

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


def run_notification_job() -> None:
    with SessionLocal() as db:
        generate_notifications(db)


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_notification_job,
        trigger="interval",
        minutes=15,
        id="generate-notifications",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(UTC),
    )
    logger.info("Starting FRAME notification worker")
    scheduler.start()


if __name__ == "__main__":
    main()

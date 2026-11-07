import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


def log_worker_heartbeat() -> None:
    logger.info("FRAME worker is running; no scheduled product jobs are enabled yet")


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        log_worker_heartbeat,
        trigger="interval",
        minutes=30,
        id="worker-heartbeat",
        replace_existing=True,
    )
    logger.info("Starting FRAME background worker")
    scheduler.start()


if __name__ == "__main__":
    main()

import logging
import os


def setup_logging(level: str | None = None) -> None:
    """Configure root logging once; level defaults to $LOG_LEVEL or INFO."""
    logging.basicConfig(
        level=(level or os.getenv("LOG_LEVEL", "INFO")).upper(),
        format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

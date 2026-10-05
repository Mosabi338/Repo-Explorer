import logging


def setup_logging():
    """Configure how log messages look. Call once when the app starts."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
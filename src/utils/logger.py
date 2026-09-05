"""Central logging configuration for the application."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger("nexustiq24")
    if root.handlers:
        return  # already configured
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    root.addHandler(handler)

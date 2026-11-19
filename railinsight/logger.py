"""Configuration des logs de l'application."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Define where the log files go
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_logger(name: str = "railinsight") -> logging.Logger:
    """Retourne un logger configuré une seule fois pour le projet."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    debug_handler = RotatingFileHandler(
        LOG_DIR / "debug.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(debug_handler)
    logger.addHandler(error_handler)
    logger.propagate = False
    return logger


def get_user_logger(name: str = "railinsight.users") -> logging.Logger:
    """Retourne un logger dédié aux actions des utilisateurs dans ``logs/users.log``."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    user_handler = RotatingFileHandler(
        LOG_DIR / "users.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    user_handler.setLevel(logging.INFO)
    user_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(user_handler)
    logger.propagate = False
    return logger

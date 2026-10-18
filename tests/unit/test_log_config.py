"""Tests para src/log_config.py."""

from __future__ import annotations

import logging

from src.log_config import get_logger


def test_get_logger() -> None:
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_ensure_handler_no_duplica() -> None:
    from src.log_config import _ensure_handler

    root = logging.getLogger()
    before = len(root.handlers)
    _ensure_handler()
    assert len(root.handlers) == before

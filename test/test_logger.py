import railinsight.logger as logger
from railinsight.logger import get_logger


def test_logger_writes_to_both_files(tmp_path, monkeypatch):
    """Test that log messages are written to the correct files."""
    monkeypatch.setattr(logger, "LOG_DIR", tmp_path)

    log = get_logger("test_files")
    log.info("info message")
    log.error("error message")

    debug = (tmp_path / "debug.log").read_text(encoding="utf-8")
    errors = (tmp_path / "errors.log").read_text(encoding="utf-8")

    assert "info message" in debug
    assert "error message" in debug
    assert "error message" in errors
    assert "info message" not in errors


def test_logger_called_twice_returns_same_instance(tmp_path, monkeypatch):
    """Test that calling get_logger twice reuses the same logger and handlers."""
    monkeypatch.setattr(logger, "LOG_DIR", tmp_path)

    first = get_logger("test_double")
    second = get_logger("test_double")

    assert first is second
    assert len(second.handlers) == 2

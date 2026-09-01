import logging
from logging.handlers import RotatingFileHandler
import re

import main as main_module
from src.logging_config import (
    LOGGER_NAME,
    TERMINAL_PREFIX,
    configure_logging,
    get_logger,
)
from src.search_service import SearchService


def _flush_owl_handlers() -> None:
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()


def test_normal_mode_writes_info_to_file_without_terminal_logs(
    tmp_path,
    capsys,
):
    log_path = configure_logging(log_directory=tmp_path)
    logger = get_logger("test")

    logger.debug("debug details")
    logger.info("runtime started")
    _flush_owl_handlers()

    assert capsys.readouterr().err == ""
    contents = log_path.read_text(encoding="utf-8")
    assert "runtime started" in contents
    assert "debug details" not in contents


def test_debug_mode_writes_debug_to_file_and_terminal(tmp_path, capsys):
    log_path = configure_logging(debug=True, log_directory=tmp_path)

    get_logger("test").debug("diagnostic details")
    _flush_owl_handlers()

    terminal_output = capsys.readouterr().err
    assert TERMINAL_PREFIX in terminal_output
    assert "DEBUG" in terminal_output
    assert "TEST" in terminal_output
    assert "diagnostic details" in terminal_output

    file_output = log_path.read_text(encoding="utf-8")
    assert "diagnostic details" in file_output
    assert TERMINAL_PREFIX not in file_output
    assert "\033[" not in file_output


def test_debug_terminal_uses_ansi_colors_when_supported(tmp_path, capsys):
    configure_logging(debug=True, color=True, log_directory=tmp_path)

    get_logger("search_service").warning("service unavailable")
    _flush_owl_handlers()

    terminal_output = capsys.readouterr().err
    assert "\033[1;36m[OWL LOG]\033[0m" in terminal_output
    assert "\033[33mWARNING" in terminal_output
    assert "\033[35mSEARCH_SERVICE" in terminal_output


def test_no_color_environment_disables_ansi_sequences(
    monkeypatch,
    tmp_path,
    capsys,
):
    monkeypatch.setenv("NO_COLOR", "1")
    configure_logging(debug=True, color=True, log_directory=tmp_path)

    get_logger("test").error("plain diagnostic")
    _flush_owl_handlers()

    terminal_output = capsys.readouterr().err
    assert TERMINAL_PREFIX in terminal_output
    assert re.search(r"\x1b\[[0-9;]*m", terminal_output) is None


def test_logging_uses_bounded_rotating_file_handler(tmp_path):
    configure_logging(log_directory=tmp_path)

    handlers = logging.getLogger(LOGGER_NAME).handlers
    rotating_handlers = [
        handler for handler in handlers if isinstance(handler, RotatingFileHandler)
    ]

    assert len(rotating_handlers) == 1
    assert rotating_handlers[0].maxBytes == 5 * 1024 * 1024
    assert rotating_handlers[0].backupCount == 3


def test_search_logs_metadata_without_query_content(tmp_path):
    log_path = configure_logging(debug=True, log_directory=tmp_path)
    private_query = "private-search-phrase"
    service = SearchService(completion_search=lambda query: [])

    service.search(private_query)
    _flush_owl_handlers()

    contents = log_path.read_text(encoding="utf-8")
    assert private_query not in contents
    assert f"query_length={len(private_query)}" in contents


def test_main_forwards_normal_and_debug_modes(monkeypatch):
    configured_modes = []
    runs = []
    monkeypatch.setattr(
        main_module,
        "configure_logging",
        lambda *, debug: configured_modes.append(debug),
    )
    monkeypatch.setattr(main_module, "run_program", lambda: runs.append(True))

    main_module.main([])
    main_module.main(["--debug"])

    assert configured_modes == [False, True]
    assert runs == [True, True]

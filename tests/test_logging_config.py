import logging
from logging.handlers import RotatingFileHandler

import main as main_module
from src.logging_config import LOGGER_NAME, configure_logging, get_logger
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

    assert "diagnostic details" in capsys.readouterr().err
    assert "diagnostic details" in log_path.read_text(encoding="utf-8")


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

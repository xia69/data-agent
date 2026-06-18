import sys
from pathlib import Path

from loguru import logger

from app.conf.app_config import app_config


def setup_logger() -> None:
    logger.remove()

    console_config = app_config.logging.console
    if console_config.enable:
        logger.add(sys.stdout, level=console_config.level)

    file_config = app_config.logging.file
    if file_config.enable:
        log_dir = Path(file_config.path)
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "main.log",
            level=file_config.level,
            rotation=file_config.rotation,
            retention=file_config.retention,
            encoding="utf-8",
        )


def main() -> None:
    setup_logger()
    logger.info("Loguru test started.")
    logger.debug("Console level may hide this debug line if level is above DEBUG.")
    logger.success("Loguru is working.")

    try:
        test_value = 1 + 1
        logger.info("Simple calculation result: {}", test_value)
    except Exception:
        logger.exception("Unexpected error during Loguru smoke test.")
        raise


if __name__ == "__main__":
    main()

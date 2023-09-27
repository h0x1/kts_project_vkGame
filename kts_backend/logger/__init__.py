import logging
import typing
from logging.handlers import RotatingFileHandler

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


def setup_logging(app: "Application") -> None:
    logger = logging.getLogger(app.config.logger.name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s (%(funcName)s) | %(message)s"
    )

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    sh.setLevel(logging.DEBUG)

    fh = RotatingFileHandler(
        app.config.logger.file,
        maxBytes=1024**2,
        backupCount=1,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)

    logger.addHandler(sh)
    logger.addHandler(fh)

    app.logger = logger

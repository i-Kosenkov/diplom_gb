import logging
from logging.handlers import RotatingFileHandler


def init_logger(name):
    logger = logging.getLogger(name)
    FORMAT = "%(asctime)s - %(name)s: %(lineno)d - %(levelname)s - %(message)s"
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(FORMAT))
    ch.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(
        filename="/logs/log.log",
        mode="a",
        maxBytes=2048,
        backupCount=0,
        encoding=None
    )
    fh.setFormatter(logging.Formatter(FORMAT))
    fh.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

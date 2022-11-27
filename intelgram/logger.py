import logging

from inteltk.colors import *


class Formatter(logging.Formatter):
    FORMAT = "%(levelname)s - %(asctime)s - %(message)s (%(filename)s:%(lineno)d)"
    FORMATS = {
        logging.DEBUG: f"{WHITE}{FORMAT}{RESET}",
        logging.INFO: f"{GREEN}{FORMAT}{RESET}",
        logging.WARNING: f"{YELLOW}{FORMAT}{RESET}",
        logging.ERROR: f"{RED}{FORMAT}{RESET}",
        logging.CRITICAL: f"{RED}{FORMAT}{RESET}"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%H:%M:%S")
        return formatter.format(record)


def setup_logger():
    logger = logging.getLogger("instagrapi")

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(Formatter())

    logger.addHandler(handler)

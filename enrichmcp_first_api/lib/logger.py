import logging
import os


class FileLogger:
    def __init__(self, log_file, level=logging.INFO, domain=None):
        """
        Initialize the FileLogger.

        :param log_file: Path to the log file
        :param level: Logging level threshold (default: logging.INFO)
        :param domain: Optional domain name for the logger
        """
        self.logger = logging.getLogger(domain or "NFLOG")
        self.logger.setLevel(level)
        self.logger.propagate = False  # Prevent messages from bubbling up to root logger

        # Only add handler if none exist (prevents duplicate logs)
        if not self.logger.handlers:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, level, message):
        if level >= self.logger.level:
            self.logger.log(level, message)

    def debug(self, message):
        self.log(logging.DEBUG, message)

    def info(self, message):
        self.log(logging.INFO, message)

    def warning(self, message):
        self.log(logging.WARNING, message)

    def error(self, message):
        self.log(logging.ERROR, message)

    def critical(self, message):
        self.log(logging.CRITICAL, message)

    def exception(self, message):
        self.logger.exception(message)

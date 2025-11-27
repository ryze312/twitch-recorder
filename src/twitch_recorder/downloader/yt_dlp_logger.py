import logging


class YtDlpLogger:
    logger = logging.getLogger("yt-dlp")

    def debug(self, message: str) -> None:
        if not message.startswith("[debug] "):
            self.info(message)
            return

        message = message.removeprefix("[debug] ")
        self.logger.debug(message)

    def info(self, message: str) -> None:
        message = message.removeprefix("[info] ")
        self.logger.info(message)

    def warning(self, message: str) -> None:
        message = message.removeprefix("[warning] ")
        self.logger.warning(message)

    def error(self, message: str) -> None:
        # yt-dlp prints just the newline character sometimes
        if message == "\n":
            return

        # yt-dlp prepends colored ERROR prefix for the error log
        # Remove both regular and colored prefix
        message = message.removeprefix("ERROR")
        message = message.removeprefix("\x1b[0;31mERROR:\x1b[0m ")

        self.logger.error(message)

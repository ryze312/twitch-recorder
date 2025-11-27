import argparse
import logging
import sys
from argparse import Namespace
from logging import Logger

import twitchio.utils

from . import __version__
from .config import Config, ConfigError, Log, LogLevel
from .downloader import StreamDownloader
from .recorder import Recorder


def main() -> None:
    # Use INFO for everything by default,
    # config will override individual loggers later
    twitchio.utils.setup_logging(level=logging.INFO)
    logger = logging.getLogger("twitch-recorder")


    args = load_arguments()
    config = load_config(args, logger)

    setup_logging(config.log, logger)

    downloader = StreamDownloader(config.downloader, logger)
    recorder = Recorder(config.twitch, downloader, logger)

    recorder.run()

def load_arguments() -> Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config",
        help="specify path to configuration file",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser.parse_args()

def load_config(args: Namespace, logger: logging.Logger) -> Config:
    try:
        return Config.build(args, logger)
    except ConfigError as e:
        logger.critical(e)
        sys.exit(-1)

def setup_logging(config: Log, logger: Logger) -> None:
    setup_twitchio(config.twitch_io)
    setup_yt_dlp(config.yt_dlp)
    setup_recorder(logger, config.recorder)

def setup_twitchio(log_level: LogLevel) -> None:
    logger = logging.getLogger("twitchio")
    log_level.configure_logger(logger)

    # Filter out StarletteAdapater warning as we don't need it
    logging.getLogger("twitchio.client").addFilter(
        lambda rec: not rec.msg.startswith("If you require the StarletteAdapter"),
    )

def setup_yt_dlp(log_level: LogLevel) -> None:
    log_level.configure_logger(logging.getLogger("yt-dlp"))

def setup_recorder(logger: Logger, log_level: LogLevel) -> None:
    log_level.configure_logger(logger)

if __name__ == "__main__":
    main()

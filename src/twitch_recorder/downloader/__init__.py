import asyncio
from logging import Logger
from pathlib import Path
from typing import Any

from yt_dlp import DownloadError, YoutubeDL
from yt_dlp.postprocessor import PostProcessor

from twitch_recorder.config import DownloaderConfig, YtDlpOptions

from .lock_file import LockFile, LockFileAcquiredError
from .yt_dlp_logger import YtDlpLogger


class StreamDownloader:
    def __init__(self, config: DownloaderConfig, logger: Logger) -> None:
        config.yt_dlp_options.update({
            "outtmpl": {
                "default": config.output_template,
            },

            # Suppress ffmpeg output as it's not passed through the logger
            "quiet": True,
            "logger": YtDlpLogger(),
        })

        self.output_path = config.output_path
        self.yt_dlp_options = config.yt_dlp_options
        self.logger = logger

    async def download_stream(self, username: str) -> None:
        options = self._make_yt_dlp_instance_options(username)

        self.logger.debug(
            "Spawning download task for %s with options %s",
            username,
            options,
        )

        await asyncio.to_thread(_download_task, username, options, self.logger)

    def _make_yt_dlp_instance_options(self, username: str) -> YtDlpOptions:
        options = self.yt_dlp_options.copy()
        options.update({
            "paths": {
                "home": str(self.output_path / username),
            },
        })

        return options

# We have to ignore disallow-subclassing-any
class LockFilePostProcessor(PostProcessor): # type: ignore[misc]
    def __init__(self, lock: LockFile) -> None:
        super().__init__()
        self.lock = lock

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        lock_path = Path(info["filename"])
        self.lock.lock(lock_path)

        return [], info

def _download_task(username: str, yt_dlp_options: YtDlpOptions, logger: Logger) -> None:
    with (
        YoutubeDL(yt_dlp_options) as yt,
        LockFile() as lock,
    ):
        yt.add_post_processor(LockFilePostProcessor(lock), when="before_dl")
        _start_download(yt, username, logger)


def _start_download(yt: YoutubeDL, username: str, logger: Logger) -> None:
    logger.info("Download started for stream %s", username)

    url = f"https://twitch.tv/{username}"

    try:
        yt.download([url])
    except LockFileAcquiredError as e:
        logger.error(
            "Failed to acquire lock file for stream %s at %s",
            username,
            e.lock_file_path,
        )

        logger.error("Consider changing output template to avoid filename collisions")
    except DownloadError:
        logger.error("Download failed for stream %s", username)
    else:
        logger.info("Download finished for stream %s", username)

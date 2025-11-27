from logging import Logger

from .config import TwitchConfig
from .downloader import StreamDownloader
from .twitch import TwitchClient


class Recorder:
    def __init__(
        self,
        twitch_config: TwitchConfig,
        downloader: StreamDownloader,
        logger: Logger,
    ) -> None:
        self.twitch_client = TwitchClient(twitch_config, logger, self.on_stream_start)
        self.downloader = downloader

    def run(self) -> None:
        self.twitch_client.run()

    async def on_stream_start(self, username: str) -> None:
        await self.downloader.download_stream(username)

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from logging import Logger

from twitchio import Client, PartialUser, StreamOnline
from twitchio.eventsub import StreamOnlineSubscription

from .config import TwitchConfig


class TwitchClient:
    def __init__(
        self,
        config: TwitchConfig,
        logger: Logger,
        on_stream_online: Callable[[str], Awaitable[None]],
    ) -> None:
        self.client = Client(
            client_id=config.client_id,
            client_secret=config.client_secret,
        )

        self.client.add_listener(self._event_ready, event="event_ready")
        self.client.add_listener(self._event_stream_online, event="event_stream_online")

        self.token = config.token
        self.usernames = list(config.users)

        self.on_stream_online = on_stream_online
        self.logger = logger

    def run(self) -> None:
        self.client.run(
            token=self.token,
            save_tokens=False,
            with_adapter=False,
        )

    async def _event_ready(self) -> None:
        self.logger.info("Started Twitch client")

        # Make sure to fetch currently live users before subscribing
        # to avoid possibility of getting an event and an entry here for the same stream
        users = await self._get_currently_live_users()

        await self._subscribe_to_stream_events()
        await self._dispatch_batch(users)

    async def _event_stream_online(self, event: StreamOnline) -> None:
        await self._dispatch_stream_online(event.broadcaster)

    async def _get_currently_live_users(self) -> list[PartialUser]:
        # mypy complains about list[str] being invariant of list[int | str]
        streams = await self.client.fetch_streams(user_logins=self.usernames) # type: ignore[arg-type]

        return [
            stream.user
            for stream in streams
            if stream.type == "live"
        ]

    async def _subscribe_to_stream_events(self) -> None:
        self.logger.debug("Subscribing to users: %s", self.usernames)

        async for sub in self._make_stream_online_subscriptions(self.usernames):
            await self.client.subscribe_websocket(sub, token_for=self.token)

    async def _dispatch_batch(self, users: list[PartialUser]) -> None:
        tasks = ( self._dispatch_stream_online(user) for user in users )
        await asyncio.gather(*tasks)

    async def _dispatch_stream_online(self, user: PartialUser) -> None:
        user_id = user.id
        name = user.name

        if not name:
            self.logger.error("User ID %s is online, but missing username", user_id)
            return

        self.logger.info("User %s is online", name)
        await self.on_stream_online(name)

    async def _make_stream_online_subscriptions(
        self,
        usernames: list[str],
    ) -> AsyncGenerator[StreamOnlineSubscription]:
        users = await self.client.fetch_users(logins=usernames)

        for user in users:
            yield StreamOnlineSubscription(broadcaster_user_id=user.id)

import contextlib
import logging
import os
import platform
from argparse import Namespace
from dataclasses import dataclass, field
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import Any, Self, assert_never

import serde.toml
from serde import SerdeError, deserialize

YtDlpOptions = dict[str, Any]

class LogLevel(Enum):
    NONE = "none"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

    def configure_logger(self, logger: Logger) -> None:
        if self == LogLevel.NONE:
            logger.disabled = True
            return

        # Amusing way to make exhaustiveness check work
        # without having to repeat logging.setLevel for each case
        def get_level() -> int:
            match self:
                case LogLevel.CRITICAL:
                    return logging.CRITICAL
                case LogLevel.ERROR:
                    return logging.ERROR
                case LogLevel.WARNING:
                    return logging.WARNING
                case LogLevel.INFO:
                    return logging.INFO
                case LogLevel.DEBUG:
                    return logging.DEBUG
                case v:
                    assert_never(v)

        logger.setLevel(get_level())

@deserialize
@dataclass
class DownloaderConfig:
    output_template: str = "[%(timestamp>%Y-%m-%d %H:%M:%S)s] %(description)s.%(ext)s"
    output_path: Path = Path("recordings")

    yt_dlp_options: YtDlpOptions = field(default_factory=YtDlpOptions)

@deserialize
@dataclass
class TwitchConfig:
    client_id: str
    client_secret: str
    token: str

    # This is a set so we don't get duplicate entries
    users: set[str] = field(default_factory=set)

@deserialize
@dataclass
class Log:
    recorder: LogLevel = LogLevel.INFO
    twitch_io: LogLevel = LogLevel.WARNING
    yt_dlp: LogLevel = LogLevel.INFO

@deserialize
@dataclass
class Config:
    twitch: TwitchConfig
    downloader: DownloaderConfig = field(default_factory=DownloaderConfig)
    log: Log = field(default_factory=Log)

    @classmethod
    def build(cls, args: Namespace, logger: Logger) -> Self:
        if path := cls._path_from_args(args):
            logger.info("Using config from arguments: %s", path)
            return cls.from_file(path)

        if path := cls._path_from_environment():
            logger.info("Using config from environment: %s", path)
            return cls.from_file(path)

        config, path = cls.from_platform_config()
        logger.info("Using config: %s", path)

        return config

    @classmethod
    def from_file(cls, path: Path) -> Self:
        try:
            with path.open() as f:
                return serde.toml.from_toml(cls, f.read())
        except FileNotFoundError as e:
            raise ConfigNotFoundError({path}) from e

    @classmethod
    def from_platform_config(cls) -> tuple[Self, Path]:
        paths = cls._paths_from_platform()

        for path in paths:
            with contextlib.suppress(ConfigNotFoundError):
                config = cls.from_file(path)
                return config, path

        raise ConfigNotFoundError(paths)

    @staticmethod
    def _path_from_args(args: Namespace) -> Path | None:
        if path := args.config:
            return Path(path)

        return None

    @staticmethod
    def _path_from_environment() -> Path | None:
        if path := os.getenv("TWITCH_RECORDER_CONFIG"):
            return Path(path)

        return None

    @staticmethod
    def _paths_from_platform() -> set[Path]:
        base_paths = _get_platform_config_paths()

        return {
            path / "twitch-recoder.toml"
            for path in base_paths
        }


class ConfigError(Exception):
    pass

@dataclass
class ConfigNotFoundError(ConfigError):
    paths: set[Path]

    def __str__(self) -> str:
        return f"Config file not found at paths: {self.paths}"


@dataclass
class ConfigParseError(ConfigError):
    error: SerdeError

    def __str__(self) -> str:
        return f"Couldn't parse config: {self.error}"

@dataclass
class UnsupportedSystemError(Exception):
    system: str

@dataclass
class NoAppDataError(Exception):
    pass

def _get_platform_config_paths() -> list[Path]:
    match platform.system():
        case "Linux" | "Darwin":
            return _get_unix_config_paths()
        case "Windows":
            return _get_windows_config_paths()
        case system:
            raise UnsupportedSystemError(system)

def _get_unix_config_paths() -> list[Path]:
    paths = []

    if xdg := os.getenv("XDG_CONFIG_HOME"):
        paths.append(Path(xdg))

    if home := os.getenv("HOME"):
        paths.append(Path(home) / ".config")

    paths.append(Path("/etc"))

    return paths

def _get_windows_config_paths() -> list[Path]:
    match os.getenv("APPDATA"):
        case None:
            raise NoAppDataError
        case appdata:
            return [Path(appdata) / "twitch-recorder"]

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self, TextIO


class LockFile:
    def __init__(self) -> None:
        self.lock_file: LockFileStore | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.lock_file:
            self.unlock()

    def lock(self, path: Path) -> None:
        if self.lock_file:
            raise LockFileAlreadyAcquiredError(self.lock_file.path)

        filename = path.name + ".lock"
        path = path.with_name(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file = path.open("x")
        except FileExistsError as e:
            raise LockFileAcquiredError(path) from e

        self.lock_file = LockFileStore(file, path)

    def unlock(self) -> None:
        if not self.lock_file:
            raise LockFileNotAcquiredError

        # Make sure to remove file before closing
        # to prevent accidentally removing the file of another instance
        self.lock_file.path.unlink(missing_ok=True)

        self.lock_file.file.close()
        self.lock_file = None

@dataclass
class LockFileStore:
    file: TextIO
    path: Path

@dataclass
class LockFileAcquiredError(Exception):
    lock_file_path: Path

    def __str__(self) -> str:
        return f"Tried to acquire existing lock at {self.lock_file_path}"

class LockFileAlreadyAcquiredError(Exception):
    def __str__(self) -> str:
        return "Tried to lock already acquired lock"

class LockFileNotAcquiredError(Exception):
    def __str__(self) -> str:
        return "Tried to unlock unacquired lock"

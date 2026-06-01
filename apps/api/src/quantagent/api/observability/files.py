from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import threading
from typing import TextIO


SUPPORTED_STREAMS = ("access", "app", "error", "security", "audit")
_STREAM_PATTERN = "|".join(SUPPORTED_STREAMS)
_LOG_FILENAME_PATTERN = re.compile(
    rf"^(?P<service>[^.]+)\.(?P<env>[^.]+)\.(?P<instance_id>.+?)\.pid-(?P<pid>\d+)"
    rf"\.(?P<stream>{_STREAM_PATTERN})\.(?P<date_slice>\d{{8}})"
    rf"(?:\.part-(?P<part>\d{{3}}))?\.jsonl(?P<compressed>\.gz)?$"
)


@dataclass(frozen=True)
class FileLayoutConfig:
    root_dir: Path
    service: str
    env: str
    instance_id: str
    pid: int
    rotate_max_bytes: int


@dataclass(frozen=True)
class ParsedLogFile:
    path: Path
    service: str
    env: str
    instance_id: str
    pid: int
    stream: str
    date_slice: str
    part: int
    compressed: bool

    def date_start(self) -> datetime:
        return datetime.strptime(self.date_slice, "%Y%m%d").replace(tzinfo=UTC)


def build_stream_directory(root_dir: Path, stream: str, timestamp: datetime) -> Path:
    return root_dir / stream / timestamp.strftime("%Y/%m/%d")


def build_stream_filename(
    *,
    service: str,
    env: str,
    instance_id: str,
    pid: int,
    stream: str,
    timestamp: datetime,
    part: int,
) -> str:
    filename = f"{service}.{env}.{instance_id}.pid-{pid}.{stream}.{timestamp.strftime('%Y%m%d')}"
    if part > 0:
        filename += f".part-{part:03d}"
    return f"{filename}.jsonl"


def parse_log_file(path: Path) -> ParsedLogFile | None:
    match = _LOG_FILENAME_PATTERN.fullmatch(path.name)
    if match is None:
        return None
    return ParsedLogFile(
        path=path,
        service=match.group("service"),
        env=match.group("env"),
        instance_id=match.group("instance_id"),
        pid=int(match.group("pid")),
        stream=match.group("stream"),
        date_slice=match.group("date_slice"),
        part=int(match.group("part") or "0"),
        compressed=bool(match.group("compressed")),
    )


class StreamFileWriter:
    def __init__(self, config: FileLayoutConfig, stream: str) -> None:
        self._config = config
        self._stream = stream
        self._file: TextIO | None = None
        self._active_path: Path | None = None
        self._active_date: str | None = None
        self._active_part = 0
        self._active_size = 0

    def close(self) -> Path | None:
        closed_path = self._active_path
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
        self._active_path = None
        self._active_date = None
        self._active_part = 0
        self._active_size = 0
        return closed_path

    def active_path(self) -> Path | None:
        return self._active_path

    def write_line(self, line: str, created_at: float) -> Path:
        timestamp = datetime.fromtimestamp(created_at, UTC)
        date_slice = timestamp.strftime("%Y%m%d")
        encoded_size = len(line.encode("utf-8")) + 1

        if self._file is None or self._active_date != date_slice:
            self._open_file(timestamp, part=0)
        elif self._active_size + encoded_size > self._config.rotate_max_bytes:
            self._open_file(timestamp, part=self._active_part + 1)

        assert self._file is not None
        self._file.write(line)
        self._file.write("\n")
        self._file.flush()
        self._active_size += encoded_size
        assert self._active_path is not None
        return self._active_path

    def _open_file(self, timestamp: datetime, *, part: int) -> None:
        self.close()
        directory = build_stream_directory(self._config.root_dir, self._stream, timestamp)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / build_stream_filename(
            service=self._config.service,
            env=self._config.env,
            instance_id=self._config.instance_id,
            pid=self._config.pid,
            stream=self._stream,
            timestamp=timestamp,
            part=part,
        )
        self._file = path.open("a", encoding="utf-8")
        self._active_path = path
        self._active_date = timestamp.strftime("%Y%m%d")
        self._active_part = part
        self._active_size = path.stat().st_size if path.exists() else 0


class StreamFileWriterSet:
    def __init__(self, config: FileLayoutConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._writers = {stream: StreamFileWriter(config, stream) for stream in SUPPORTED_STREAMS}
        self._closed_paths: set[Path] = set()

    def close(self) -> set[Path]:
        with self._lock:
            closed_paths: set[Path] = set()
            for writer in self._writers.values():
                if (closed_path := writer.close()) is not None:
                    closed_paths.add(closed_path)
            self._closed_paths.update(closed_paths)
            return closed_paths

    def write(self, *, stream: str, line: str, created_at: float) -> Path:
        if stream not in self._writers:
            raise ValueError(f"Unsupported log stream: {stream}")
        with self._lock:
            writer = self._writers[stream]
            before_path = writer.active_path()
            path = writer.write_line(line, created_at)
            if before_path is not None and before_path != path:
                self._closed_paths.add(before_path)
            return path

    def active_path(self, stream: str) -> Path | None:
        with self._lock:
            writer = self._writers[stream]
            return writer.active_path()

    def active_paths(self) -> set[Path]:
        with self._lock:
            return {
                path
                for writer in self._writers.values()
                if (path := writer.active_path()) is not None
            }

    def closed_paths(self) -> set[Path]:
        with self._lock:
            return set(self._closed_paths)

from __future__ import annotations

import os
from collections.abc import Iterable

import psutil

from .models import ProcessSnapshot


class ProcessMonitor:
    def __init__(self) -> None:
        self._known: dict[int, float] = {}
        self._prime_cpu_counters()

    @staticmethod
    def _prime_cpu_counters() -> None:
        for process in psutil.process_iter():
            try:
                process.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def snapshot(self) -> list[ProcessSnapshot]:
        records: list[ProcessSnapshot] = []
        attrs = ["pid", "name", "exe", "create_time", "memory_info", "memory_percent", "status"]
        for process in psutil.process_iter(attrs=attrs, ad_value=None):
            try:
                info = process.info
                if not info["name"] or info["create_time"] is None:
                    continue
                memory_info = info["memory_info"]
                records.append(
                    ProcessSnapshot(
                        pid=int(info["pid"]),
                        name=str(info["name"]),
                        executable=info["exe"],
                        create_time=float(info["create_time"]),
                        cpu_percent=max(0.0, float(process.cpu_percent(None))),
                        memory_bytes=int(memory_info.rss if memory_info else 0),
                        memory_percent=max(0.0, float(info["memory_percent"] or 0)),
                        status=str(info["status"] or "unknown"),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return sorted(records, key=lambda item: item.pid)

    def new_processes(self, snapshot: Iterable[ProcessSnapshot]) -> list[ProcessSnapshot]:
        current = {item.pid: item.create_time for item in snapshot}
        new = [item for item in snapshot if self._known.get(item.pid) != item.create_time]
        self._known = current
        return new

    @staticmethod
    def is_self(process: ProcessSnapshot) -> bool:
        return process.pid == os.getpid()


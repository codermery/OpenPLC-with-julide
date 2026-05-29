"""Event and alarm logging utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass(slots=True)
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str


@dataclass(slots=True)
class AlarmEntry:
    timestamp: str
    severity: str
    message: str
    acknowledged: bool = False


class EventLogger:
    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def add(self, level: str, source: str, message: str) -> None:
        self.entries.append(
            LogEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                level=level,
                source=source,
                message=message,
            )
        )

    def export_csv(self, path: str | Path) -> None:
        output_path = Path(path)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["timestamp", "level", "source", "message"])
            for entry in self.entries:
                writer.writerow([entry.timestamp, entry.level, entry.source, entry.message])


class AlarmManager:
    def __init__(self) -> None:
        self.alarms: List[AlarmEntry] = []

    def raise_alarm(self, severity: str, message: str) -> None:
        if any((alarm.message == message and not alarm.acknowledged) for alarm in self.alarms):
            return
        self.alarms.append(
            AlarmEntry(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                severity=severity,
                message=message,
                acknowledged=False,
            )
        )

    def acknowledge_all(self) -> None:
        for alarm in self.alarms:
            alarm.acknowledged = True

    def clear_acknowledged(self) -> None:
        self.alarms = [alarm for alarm in self.alarms if not alarm.acknowledged]

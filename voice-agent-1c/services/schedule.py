"""Сервис рабочего расписания.

Определяет рабочие часы для обработки звонков:
  - Пн-Пт: 9:00 - 18:00
  - Сб: 10:00 - 15:00
  - Вс: выходной
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

logger = logging.getLogger(__name__)

# Часовой пояс — Москва (UTC+3)
MSK = timezone(timedelta(hours=3))

# Дни недели: 0=Пн, 6=Вс
WEEKDAY_NAMES_RU = [
    "понедельник",
    "вторник",
    "среду",
    "четверг",
    "пятницу",
    "субботу",
    "воскресенье",
]


@dataclass
class DaySchedule:
    """Расписание на один день."""

    start: time
    end: time
    is_working: bool = True


@dataclass
class WorkingHours:
    """Расписание рабочих часов."""

    # Пн=0 .. Вс=6
    schedule: dict[int, DaySchedule] = field(default_factory=lambda: {
        0: DaySchedule(start=time(9, 0), end=time(18, 0)),   # Пн
        1: DaySchedule(start=time(9, 0), end=time(18, 0)),   # Вт
        2: DaySchedule(start=time(9, 0), end=time(18, 0)),   # Ср
        3: DaySchedule(start=time(9, 0), end=time(18, 0)),   # Чт
        4: DaySchedule(start=time(9, 0), end=time(18, 0)),   # Пт
        5: DaySchedule(start=time(10, 0), end=time(15, 0)),  # Сб
        6: DaySchedule(start=time(0, 0), end=time(0, 0), is_working=False),  # Вс
    })


class ScheduleService:
    """Сервис проверки рабочего времени.

    Usage:
        service = ScheduleService()
        if not service.is_working_hours():
            next_time = service.format_next_working_time()
            # "в понедельник в 9:00"
    """

    def __init__(self, working_hours: WorkingHours | None = None) -> None:
        self._hours = working_hours or WorkingHours()

    def is_working_hours(self, dt: datetime | None = None) -> bool:
        """Проверяет, попадает ли время в рабочие часы."""
        now = dt or datetime.now(MSK)
        if now.tzinfo is None:
            now = now.replace(tzinfo=MSK)
        else:
            now = now.astimezone(MSK)

        weekday = now.weekday()
        day = self._hours.schedule.get(weekday)

        if not day or not day.is_working:
            return False

        current_time = now.time()
        return day.start <= current_time < day.end

    def next_working_time(self, dt: datetime | None = None) -> datetime:
        """Возвращает datetime следующего начала рабочего дня."""
        now = dt or datetime.now(MSK)
        if now.tzinfo is None:
            now = now.replace(tzinfo=MSK)
        else:
            now = now.astimezone(MSK)

        # Проверяем текущий день — может ещё не начался
        weekday = now.weekday()
        day = self._hours.schedule.get(weekday)
        if day and day.is_working and now.time() < day.start:
            return now.replace(
                hour=day.start.hour,
                minute=day.start.minute,
                second=0,
                microsecond=0,
            )

        # Ищем следующий рабочий день (до 7 дней вперёд)
        for offset in range(1, 8):
            next_day = now + timedelta(days=offset)
            next_weekday = next_day.weekday()
            day = self._hours.schedule.get(next_weekday)

            if day and day.is_working:
                return next_day.replace(
                    hour=day.start.hour,
                    minute=day.start.minute,
                    second=0,
                    microsecond=0,
                )

        # Fallback (не должно случиться при корректном расписании)
        return now + timedelta(days=1)

    def format_next_working_time(self, dt: datetime | None = None) -> str:
        """Форматирует следующее рабочее время для озвучивания.

        Примеры:
        - "сегодня в 9:00" (если до начала рабочего дня)
        - "в понедельник в 9:00"
        - "завтра в 9:00"
        """
        now = dt or datetime.now(MSK)
        if now.tzinfo is None:
            now = now.replace(tzinfo=MSK)
        else:
            now = now.astimezone(MSK)

        next_time = self.next_working_time(now)
        time_str = f"{next_time.hour}:{next_time.minute:02d}"

        # Сегодня
        if next_time.date() == now.date():
            return f"сегодня в {time_str}"

        # Завтра
        if next_time.date() == (now + timedelta(days=1)).date():
            return f"завтра в {time_str}"

        # День недели
        day_name = WEEKDAY_NAMES_RU[next_time.weekday()]
        return f"в {day_name} в {time_str}"

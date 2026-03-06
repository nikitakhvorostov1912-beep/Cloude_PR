"""Тесты сервиса рабочего расписания."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pytest

from services.schedule import MSK, DaySchedule, ScheduleService, WorkingHours


@pytest.fixture
def service():
    return ScheduleService()


# --- Рабочие часы ---


class TestIsWorkingHours:
    def test_weekday_morning(self, service):
        """Пн 10:00 -> рабочее время."""
        dt = datetime(2024, 1, 15, 10, 0, tzinfo=MSK)  # Пн
        assert service.is_working_hours(dt) is True

    def test_weekday_afternoon(self, service):
        """Ср 15:30 -> рабочее время."""
        dt = datetime(2024, 1, 17, 15, 30, tzinfo=MSK)  # Ср
        assert service.is_working_hours(dt) is True

    def test_weekday_before_start(self, service):
        """Пн 8:00 -> нерабочее."""
        dt = datetime(2024, 1, 15, 8, 0, tzinfo=MSK)
        assert service.is_working_hours(dt) is False

    def test_weekday_after_end(self, service):
        """Пн 18:30 -> нерабочее."""
        dt = datetime(2024, 1, 15, 18, 30, tzinfo=MSK)
        assert service.is_working_hours(dt) is False

    def test_weekday_exactly_end(self, service):
        """Пн 18:00 -> нерабочее (end is exclusive)."""
        dt = datetime(2024, 1, 15, 18, 0, tzinfo=MSK)
        assert service.is_working_hours(dt) is False

    def test_weekday_exactly_start(self, service):
        """Пн 9:00 -> рабочее."""
        dt = datetime(2024, 1, 15, 9, 0, tzinfo=MSK)
        assert service.is_working_hours(dt) is True

    def test_saturday_working(self, service):
        """Сб 12:00 -> рабочее."""
        dt = datetime(2024, 1, 20, 12, 0, tzinfo=MSK)  # Сб
        assert service.is_working_hours(dt) is True

    def test_saturday_too_early(self, service):
        """Сб 9:00 -> нерабочее (начало в 10:00)."""
        dt = datetime(2024, 1, 20, 9, 0, tzinfo=MSK)
        assert service.is_working_hours(dt) is False

    def test_sunday(self, service):
        """Вс -> нерабочее."""
        dt = datetime(2024, 1, 21, 12, 0, tzinfo=MSK)  # Вс
        assert service.is_working_hours(dt) is False


# --- Следующее рабочее время ---


class TestNextWorkingTime:
    def test_same_day_before_start(self, service):
        """Пн 7:00 -> Пн 9:00."""
        dt = datetime(2024, 1, 15, 7, 0, tzinfo=MSK)
        result = service.next_working_time(dt)
        assert result.hour == 9
        assert result.minute == 0
        assert result.date() == dt.date()

    def test_after_hours_weekday(self, service):
        """Пн 19:00 -> Вт 9:00."""
        dt = datetime(2024, 1, 15, 19, 0, tzinfo=MSK)
        result = service.next_working_time(dt)
        assert result.weekday() == 1  # Вт
        assert result.hour == 9

    def test_friday_evening(self, service):
        """Пт 19:00 -> Сб 10:00."""
        dt = datetime(2024, 1, 19, 19, 0, tzinfo=MSK)  # Пт
        result = service.next_working_time(dt)
        assert result.weekday() == 5  # Сб
        assert result.hour == 10

    def test_saturday_evening(self, service):
        """Сб 16:00 -> Пн 9:00."""
        dt = datetime(2024, 1, 20, 16, 0, tzinfo=MSK)  # Сб
        result = service.next_working_time(dt)
        assert result.weekday() == 0  # Пн
        assert result.hour == 9

    def test_sunday(self, service):
        """Вс -> Пн 9:00."""
        dt = datetime(2024, 1, 21, 12, 0, tzinfo=MSK)  # Вс
        result = service.next_working_time(dt)
        assert result.weekday() == 0  # Пн
        assert result.hour == 9


# --- Форматирование ---


class TestFormatNextWorkingTime:
    def test_today(self, service):
        """До начала рабочего дня -> 'сегодня в ...'."""
        dt = datetime(2024, 1, 15, 7, 0, tzinfo=MSK)  # Пн
        result = service.format_next_working_time(dt)
        assert result == "сегодня в 9:00"

    def test_tomorrow(self, service):
        """После конца рабочего дня -> 'завтра в ...'."""
        dt = datetime(2024, 1, 15, 19, 0, tzinfo=MSK)  # Пн
        result = service.format_next_working_time(dt)
        assert result == "завтра в 9:00"

    def test_day_of_week(self, service):
        """Сб 16:00 -> 'в понедельник в 9:00'."""
        dt = datetime(2024, 1, 20, 16, 0, tzinfo=MSK)  # Сб
        result = service.format_next_working_time(dt)
        assert result == "в понедельник в 9:00"

    def test_sunday_format(self, service):
        """Вс -> 'завтра в 9:00' (next day is Mon)."""
        dt = datetime(2024, 1, 21, 12, 0, tzinfo=MSK)  # Вс
        result = service.format_next_working_time(dt)
        assert "завтра" in result
        assert "9:00" in result

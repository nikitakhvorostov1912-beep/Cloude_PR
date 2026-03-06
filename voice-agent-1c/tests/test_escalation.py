"""Тесты логики эскалации."""
from __future__ import annotations

import pytest

from services.escalation import EscalationReason, EscalationService


@pytest.fixture
def service():
    return EscalationService()


# --- Клиент просит оператора ---


class TestClientRequested:
    def test_operator_keyword(self, service):
        """'Позовите оператора' -> эскалация."""
        decision = service.evaluate("Позовите оператора!")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_REQUESTED

    def test_live_person_keyword(self, service):
        """'Живой человек' -> эскалация."""
        decision = service.evaluate("Хочу поговорить с живым человеком")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_REQUESTED

    def test_specialist_keyword(self, service):
        """'Переведите на специалиста' -> эскалация."""
        decision = service.evaluate("Переведите меня на специалиста")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_REQUESTED


# --- Производственная авария ---


class TestProductionOutage:
    def test_work_stopped(self, service):
        """'Встала работа' -> эскалация."""
        decision = service.evaluate("У нас встала работа!")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.PRODUCTION_OUTAGE

    def test_nothing_works(self, service):
        """'Ничего не работает' -> эскалация."""
        decision = service.evaluate("Ничего не работает вообще")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.PRODUCTION_OUTAGE

    def test_server_down(self, service):
        """'Сервер упал' -> эскалация."""
        decision = service.evaluate("У нас сервер упал")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.PRODUCTION_OUTAGE


# --- Фрустрация клиента ---


class TestClientFrustrated:
    def test_bot_frustration(self, service):
        """'Тупой бот' -> эскалация."""
        decision = service.evaluate("Тупой бот, ничего не понимаешь")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_FRUSTRATED

    def test_complaint_keyword(self, service):
        """'Жалоба' -> эскалация."""
        decision = service.evaluate("Хочу написать жалобу")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_FRUSTRATED

    def test_manager_keyword(self, service):
        """'Руководитель' -> эскалация."""
        decision = service.evaluate("Хочу говорить с руководителем")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.CLIENT_FRUSTRATED


# --- Чувствительная тема ---


class TestSensitiveTopic:
    def test_money_topic(self, service):
        """'Деньги' -> эскалация."""
        decision = service.evaluate("Вопрос по поводу денег")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.SENSITIVE_TOPIC

    def test_contract_topic(self, service):
        """'Договор' -> эскалация."""
        decision = service.evaluate("Хочу обсудить договор")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.SENSITIVE_TOPIC

    def test_price_topic(self, service):
        """'Стоимость' -> эскалация."""
        decision = service.evaluate("Какова стоимость услуги?")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.SENSITIVE_TOPIC

    def test_court_topic(self, service):
        """'Суд' -> эскалация."""
        decision = service.evaluate("Мы подадим в суд")
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.SENSITIVE_TOPIC


# --- Низкая уверенность ---


class TestLowConfidence:
    def test_consecutive_low_confidence(self, service):
        """2+ раза низкая уверенность -> эскалация."""
        decision = service.evaluate(
            "Что-то непонятное",
            consecutive_low_confidence=2,
        )
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.LOW_CONFIDENCE

    def test_single_low_confidence_ok(self, service):
        """1 раз низкая уверенность -> нет эскалации."""
        decision = service.evaluate(
            "Что-то непонятное",
            consecutive_low_confidence=1,
        )
        assert decision.should_escalate is False


# --- Превышен лимит вопросов ---


class TestMaxQuestions:
    def test_max_questions_reached(self, service):
        """5/5 вопросов -> эскалация."""
        decision = service.evaluate(
            "Обычный текст",
            questions_asked=5,
            max_questions=5,
        )
        assert decision.should_escalate is True
        assert decision.reason == EscalationReason.MAX_QUESTIONS

    def test_under_limit_ok(self, service):
        """3/5 вопросов -> нет эскалации."""
        decision = service.evaluate(
            "Обычный текст",
            questions_asked=3,
            max_questions=5,
        )
        assert decision.should_escalate is False


# --- Нет эскалации ---


class TestNoEscalation:
    def test_normal_text(self, service):
        """Обычный текст -> нет эскалации."""
        decision = service.evaluate("У нас не проводятся документы")
        assert decision.should_escalate is False
        assert decision.reason is None

    def test_empty_text(self, service):
        """Пустой текст -> нет эскалации."""
        decision = service.evaluate("")
        assert decision.should_escalate is False

    def test_technical_question(self, service):
        """Технический вопрос -> нет эскалации."""
        decision = service.evaluate(
            "Как настроить печатную форму в 1С?"
        )
        assert decision.should_escalate is False


# --- Приоритет причин ---


class TestPriority:
    def test_operator_over_frustration(self, service):
        """'Оператора, тупой бот' -> CLIENT_REQUESTED (не FRUSTRATED)."""
        decision = service.evaluate(
            "Позовите оператора, тупой бот!"
        )
        assert decision.reason == EscalationReason.CLIENT_REQUESTED

    def test_outage_over_sensitive(self, service):
        """Авария + деньги -> PRODUCTION_OUTAGE."""
        decision = service.evaluate(
            "Встала работа, теряем деньги"
        )
        assert decision.reason == EscalationReason.PRODUCTION_OUTAGE

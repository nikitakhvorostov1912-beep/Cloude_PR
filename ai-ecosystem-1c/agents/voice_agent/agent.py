"""Voice agent — manages the full dialog lifecycle for an incoming call."""

from __future__ import annotations

import logging
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.voice_agent.dialogue_manager import DialogState, DialogueManager
from agents.voice_agent.prompts import (
    build_clarification_prompt,
    build_greeting,
    build_voice_system_prompt,
)
from services.llm.claude_client import ClaudeClient, LLMResponse
from services.llm.function_calling import get_voice_tools

logger = logging.getLogger(__name__)


class VoiceAgent(BaseAgent):
    """Conducts voice dialog: greeting → questions → classification → task."""

    def __init__(self, llm: ClaudeClient, *, max_questions: int = 5) -> None:
        super().__init__(name="voice_agent", max_retries=2)
        self._llm = llm
        self._max_questions = max_questions
        self._managers: dict[str, DialogueManager] = {}

    def start_session(
        self,
        call_id: str,
        *,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        product: Optional[str] = None,
    ) -> str:
        """Initialize a dialog session and return the greeting text."""
        mgr = DialogueManager(call_id, max_questions=self._max_questions)
        mgr.set_client_info(name=client_name, phone=client_phone, product=product)
        self._managers[call_id] = mgr

        greeting = build_greeting(client_name)
        mgr.add_assistant_message(greeting)
        mgr.transition(DialogState.LISTENING)
        return greeting

    def get_manager(self, call_id: str) -> Optional[DialogueManager]:
        return self._managers.get(call_id)

    def end_session(self, call_id: str) -> Optional[DialogueManager]:
        """Remove and return the manager for cleanup."""
        return self._managers.pop(call_id, None)

    async def process_utterance(
        self,
        call_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Process a recognized utterance and return the agent's response.

        Returns:
            {
                "text": str,           # Response text for TTS
                "action": str | None,  # "create_task" | "escalate" | None
                "action_data": dict,   # Tool call input (if action)
                "state": str,          # Current dialog state
            }
        """
        return await self.execute_with_retry(call_id=call_id, text=text)

    async def _execute(self, *, call_id: str, **kwargs: Any) -> dict[str, Any]:
        text: str = kwargs["text"]
        mgr = self._managers.get(call_id)
        if mgr is None:
            return {
                "text": "Сессия не найдена. Попробуйте перезвонить.",
                "action": None,
                "action_data": {},
                "state": "closed",
            }

        mgr.add_user_message(text)

        system_prompt = build_voice_system_prompt(
            client_name=mgr.context.client_name,
            product=mgr.context.product,
            has_active_tasks=False,
            max_questions=mgr.context.max_questions,
        )

        # Inject question count hint
        if mgr.context.questions_asked > 0:
            hint = build_clarification_prompt(
                mgr.context.questions_asked, mgr.context.max_questions
            )
            system_prompt += f"\n\n[{hint}]"

        response: LLMResponse = await self._llm.dialog(
            system=system_prompt,
            messages=mgr.context.messages,
            tools=get_voice_tools(),
        )

        # Track tokens
        self._metrics.total_tokens += response.total_tokens

        # Handle tool calls
        if response.has_tool_calls:
            tool = response.tool_calls[0]
            return self._handle_tool_call(mgr, tool, response.text)

        # Regular text response — it's a question or answer
        reply_text = response.text.strip()
        mgr.add_assistant_message(reply_text)
        mgr.increment_questions()

        if mgr.state == DialogState.LISTENING:
            mgr.transition(DialogState.CLARIFYING)

        return {
            "text": reply_text,
            "action": None,
            "action_data": {},
            "state": mgr.state.value,
        }

    def _handle_tool_call(
        self,
        mgr: DialogueManager,
        tool: dict[str, Any],
        accompanying_text: str,
    ) -> dict[str, Any]:
        """Process a tool call from the LLM response."""
        tool_name = tool["name"]
        tool_input = tool["input"]

        if tool_name == "create_task":
            mgr.set_classification(tool_input)
            mgr.transition(DialogState.CLASSIFYING)
            mgr.transition(DialogState.CREATING_TASK)

            farewell = accompanying_text or (
                "Спасибо за обращение. Задача будет создана, "
                "и специалист свяжется с вами."
            )
            mgr.add_assistant_message(farewell)

            return {
                "text": farewell,
                "action": "create_task",
                "action_data": tool_input,
                "state": mgr.state.value,
            }

        if tool_name == "escalate_to_operator":
            reason = tool_input.get("reason", "по запросу клиента")
            mgr.set_escalation(reason)
            mgr.transition(DialogState.ESCALATED)

            farewell = accompanying_text or (
                "Соединяю вас со специалистом. Пожалуйста, оставайтесь на линии."
            )
            mgr.add_assistant_message(farewell)

            return {
                "text": farewell,
                "action": "escalate",
                "action_data": tool_input,
                "state": mgr.state.value,
            }

        logger.warning("Unknown tool call: %s", tool_name)
        return {
            "text": accompanying_text or "Понял. Что-нибудь ещё?",
            "action": None,
            "action_data": {},
            "state": mgr.state.value,
        }

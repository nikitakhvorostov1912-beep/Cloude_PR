"""Build AI-enriched task card for Sakura CRM."""

from __future__ import annotations

from typing import Any, Optional

from integrations.sakura.models import SakuraTaskCreate
from models.api.client import ClientContext
from models.api.task import ClassificationResult


def build_task_card(
    classification: ClassificationResult,
    client: ClientContext,
    *,
    call_id: str,
    audio_url: Optional[str] = None,
    transcript_url: Optional[str] = None,
    call_duration_sec: Optional[int] = None,
    specialist_id: Optional[str] = None,
    solutions: Optional[list[dict[str, Any]]] = None,
) -> SakuraTaskCreate:
    """Assemble a full SakuraTaskCreate payload from AI results."""
    ai_classification = {
        "department": classification.department.value,
        "task_type": classification.task_type.value,
        "confidence_scores": {
            "department": classification.department_confidence,
            "priority": classification.priority_confidence,
            "task_type": classification.task_type_confidence,
        },
        "reasoning": classification.reasoning,
        "warnings": classification.warnings,
        "key_phrases": classification.key_phrases,
    }

    client_context_dict = None
    if client.found:
        client_context_dict = {
            "recent_tasks": [t.model_dump() if hasattr(t, "model_dump") else t
                            for t in client.recent_tasks],
            "product_version": client.product_version,
            "customizations": client.customizations,
        }

    return SakuraTaskCreate(
        title=classification.summary,
        description=classification.description,
        client_id=client.sakura_id or client.onec_id or "unknown",
        assigned_to=specialist_id,
        priority=classification.priority.value,
        product=classification.product.value if classification.product else None,
        ai_classification=ai_classification,
        client_context=client_context_dict,
        ai_solutions=solutions,
        call_id=call_id,
        audio_url=audio_url,
        transcript_url=transcript_url,
        call_duration_sec=call_duration_sec,
    )

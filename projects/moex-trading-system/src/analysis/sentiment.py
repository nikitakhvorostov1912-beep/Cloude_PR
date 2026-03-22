"""Sentiment analysis — keyword-based fallback + aggregation.

For LLM-powered sentiment, see src/strategy/news_reactor.py and src/core/llm_client.py.
This module provides lightweight, dependency-free sentiment scoring.
"""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# Russian and English positive/negative keywords for MOEX context
_POSITIVE_KEYWORDS = [
    "рост", "прибыль", "дивиденд", "повышение", "рекорд", "выручка",
    "buyback", "выкуп", "upgrade", "beat", "profit", "growth",
    "оптимизм", "восстановление", "экспансия", "сделка", "контракт",
]

_NEGATIVE_KEYWORDS = [
    "падение", "убыток", "санкции", "снижение", "дефолт", "штраф",
    "sell", "downgrade", "miss", "loss", "decline", "риск",
    "кризис", "обвал", "девальвация", "инфляция", "банкротство",
]


def aggregate_daily_sentiment(news_items: list[dict]) -> float:
    """Average sentiment scores from a list of news items.

    Each item should have a "sentiment" key with float value in [-1, 1].

    Returns:
        Aggregated sentiment in [-1.0, 1.0]. Returns 0.0 if no valid scores.
    """
    if not news_items:
        return 0.0

    scores = [
        item.get("sentiment", 0.0)
        for item in news_items
        if isinstance(item.get("sentiment"), (int, float))
    ]

    if not scores:
        return 0.0

    avg = sum(scores) / len(scores)
    return max(-1.0, min(1.0, avg))


async def analyze_sentiment(articles: list[dict]) -> list[dict]:
    """Analyze sentiment for a batch of articles.

    Uses keyword-based approach as fallback (no LLM dependency).
    For LLM-powered analysis, use src/core/llm_client.get_llm_client().

    Args:
        articles: List of dicts with "title" and "body" keys.

    Returns:
        List of dicts with "sentiment" (float) and "confidence" (float) added.
    """
    results = []
    for article in articles:
        title = article.get("title", "")
        body = article.get("body", "")
        text = f"{title} {body}"

        score = _keyword_sentiment(text)
        confidence = min(1.0, abs(score) * 2)

        results.append({
            **article,
            "sentiment": score,
            "confidence": round(confidence, 3),
        })

    return results


def _keyword_sentiment(text: str) -> float:
    """Simple keyword-based sentiment scoring.

    Returns:
        Score in [-1.0, 1.0]. 0.0 if no keywords found.
    """
    if not text:
        return 0.0

    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE_KEYWORDS if w in text_lower)
    neg = sum(1 for w in _NEGATIVE_KEYWORDS if w in text_lower)

    total = pos + neg
    if total == 0:
        return 0.0

    return round((pos - neg) / total, 3)


__all__ = ["aggregate_daily_sentiment", "analyze_sentiment"]

"""News Reactor — real-time news analysis for fast trading decisions.

Monitors news feeds continuously, detects market-moving events,
and generates urgent trading signals within minutes.

Architecture:
    RSS/Telegram → Parse → Detect Impact → Claude Analysis → Urgent Signal

Impact levels:
    CRITICAL: CBR rate decision, sanctions, war, force majeure → immediate action
    HIGH:     earnings surprise, dividend announcement, CEO change → fast analysis
    MEDIUM:   analyst upgrades, sector news → include in next daily cycle
    LOW:      general market commentary → log only

Public API:
    NewsReactor.check_feeds() -> list[NewsSignal]
    NewsReactor.analyze_article(article) -> NewsSignal | None
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class NewsImpact(str, Enum):
    """Impact level of a news article."""

    CRITICAL = "critical"  # immediate action required
    HIGH = "high"  # analyze within minutes
    MEDIUM = "medium"  # include in daily cycle
    LOW = "low"  # log only


@dataclass(frozen=True)
class NewsSignal:
    """Trading signal generated from news analysis."""

    ticker: str
    impact: NewsImpact
    direction: str  # "bullish" | "bearish" | "neutral"
    confidence: float  # 0.0 to 1.0
    headline: str
    summary: str
    source: str
    published_at: datetime
    suggested_action: str  # "buy" | "sell" | "hold" | "close"
    urgency_minutes: int  # how fast to act


# === CRITICAL keywords — immediate action ===
CRITICAL_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)ключев\w*\s+ставк\w*", "cbr_rate"),
    (r"(?i)центральн\w*\s+банк\w*.*решени", "cbr_rate"),
    (r"(?i)ЦБ\s+(повысил|снизил|сохранил)", "cbr_rate"),
    (r"(?i)санкци\w+", "sanctions"),
    (r"(?i)блокирующ\w+\s+санкци", "sanctions"),
    (r"(?i)SDN|OFAC|санкционн", "sanctions"),
    (r"(?i)мобилизац|военн\w+\s+операц|боевы", "geopolitics"),
    (r"(?i)делистинг|приостанов\w+\s+торг", "delisting"),
]

# === HIGH impact keywords ===
HIGH_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)дивиденд\w*", "dividend"),
    (r"(?i)прибыль\s+(вырос|упал|сократ|увелич)\w*\s+в\s+\d", "earnings"),
    (r"(?i)убыт\w+\s+за\s+(квартал|полугод|год)", "earnings_loss"),
    (r"(?i)обратн\w+\s+выкуп|buyback", "buyback"),
    (r"(?i)(IPO|SPO|размещени\w+\s+акци)", "offering"),
    (r"(?i)слияни|поглощени|M&A|покупк\w+\s+компани", "ma"),
    (r"(?i)CEO|генеральн\w+\s+директор\w*\s+(назначен|уволен|ушёл)", "management"),
    (r"(?i)нефть.*(обвал|рекорд|резк)|brent.*(упал|вырос)", "oil_shock"),
    (r"(?i)ОПЕК\+?\s*(сократ|увелич|квот)", "opec"),
]

# === Ticker extraction patterns ===
TICKER_ALIASES: dict[str, list[str]] = {
    "SBER": ["сбербанк", "сбер", "sber"],
    "GAZP": ["газпром", "gazprom"],
    "LKOH": ["лукойл", "lukoil"],
    "ROSN": ["роснефть", "rosneft"],
    "NVTK": ["новатэк", "novatek"],
    "GMKN": ["норникель", "norilsk", "норильский никель"],
    "VTBR": ["втб", "vtb"],
    "YDEX": ["яндекс", "yandex"],
    "TCSG": ["тинькофф", "т-банк", "tinkoff", "tbank"],
    "MGNT": ["магнит", "magnit"],
    "PLZL": ["полюс", "polyus"],
    "TATN": ["татнефть", "tatneft"],
    "CHMF": ["северсталь", "severstal"],
    "NLMK": ["нлмк", "nlmk"],
    "MTSS": ["мтс", "mts"],
    "ALRS": ["алроса", "alrosa"],
    "OZON": ["озон", "ozon"],
    "PHOR": ["фосагро", "phosagro"],
    "AFLT": ["аэрофлот", "aeroflot"],
    "MOEX": ["мосбиржа", "московская биржа"],
    "PIKK": ["пик", "pik"],
    "SNGS": ["сургутнефтегаз", "surgutneftegaz"],
    "RUAL": ["русал", "rusal"],
    "IRAO": ["интер рао", "inter rao"],
}


def extract_tickers_from_text(text: str) -> list[str]:
    """Extract ticker symbols from news text using aliases."""
    text_lower = text.lower()
    found: list[str] = []

    for ticker, aliases in TICKER_ALIASES.items():
        for alias in aliases:
            if alias in text_lower:
                if ticker not in found:
                    found.append(ticker)
                break

    # Also check for raw tickers in uppercase
    for ticker in TICKER_ALIASES:
        if ticker in text:
            if ticker not in found:
                found.append(ticker)

    return found


def classify_impact(title: str, body: str = "") -> tuple[NewsImpact, str]:
    """Classify news article impact level.

    Returns
    -------
    tuple[NewsImpact, str]
        Impact level and detected pattern type.
    """
    full_text = f"{title} {body}"

    for pattern, ptype in CRITICAL_PATTERNS:
        if re.search(pattern, full_text):
            return NewsImpact.CRITICAL, ptype

    for pattern, ptype in HIGH_PATTERNS:
        if re.search(pattern, full_text):
            return NewsImpact.HIGH, ptype

    # Check for ticker mentions (at least MEDIUM if about specific company)
    tickers = extract_tickers_from_text(full_text)
    if tickers:
        return NewsImpact.MEDIUM, "company_mention"

    return NewsImpact.LOW, "general"


async def analyze_article_with_claude(
    title: str,
    body: str,
    tickers: list[str],
    impact: NewsImpact,
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Send article to Claude for fast sentiment + action analysis.

    Uses Haiku for speed (< 2 sec). Only for HIGH/CRITICAL impact.
    """
    try:
        import anthropic
    except ImportError:
        return {"direction": "neutral", "confidence": 0.0, "action": "hold", "reasoning": ""}

    prompt = f"""Проанализируй новость о российском фондовом рынке. Ответь ТОЛЬКО JSON.

Новость: {title}
Текст: {body[:500]}
Тикеры: {', '.join(tickers)}
Важность: {impact.value}

Ответь JSON:
{{
  "direction": "bullish" | "bearish" | "neutral",
  "confidence": 0.0-1.0,
  "affected_tickers": [{{"ticker": "SBER", "impact": "bullish|bearish", "magnitude": 0.0-1.0}}],
  "suggested_action": "buy" | "sell" | "hold" | "close",
  "urgency_minutes": число (как быстро действовать),
  "reasoning": "краткое обоснование"
}}"""

    try:
        client = anthropic.AsyncAnthropic()
        response = await client.messages.create(
            model=model,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

        import json
        return json.loads(raw)

    except Exception as e:
        logger.error("news_claude_error", error=str(e))
        return {"direction": "neutral", "confidence": 0.0, "action": "hold", "reasoning": str(e)}


async def process_news_feed(
    articles: list[dict[str, Any]],
    min_impact: NewsImpact = NewsImpact.HIGH,
) -> list[NewsSignal]:
    """Process a batch of news articles and generate trading signals.

    Parameters
    ----------
    articles:
        List of dicts with: title, body/text, source, published_at.
    min_impact:
        Minimum impact level to trigger Claude analysis.

    Returns
    -------
    list[NewsSignal] for articles meeting the minimum impact threshold.
    """
    signals: list[NewsSignal] = []

    for article in articles:
        title = article.get("title", "")
        body = article.get("body", article.get("text", ""))
        source = article.get("source", "unknown")

        impact, impact_type = classify_impact(title, body)

        if impact.value > min_impact.value:
            # Below threshold — skip Claude analysis
            continue

        tickers = extract_tickers_from_text(f"{title} {body}")
        if not tickers:
            continue

        logger.info(
            "news_reactor.analyzing",
            title=title[:80],
            impact=impact.value,
            type=impact_type,
            tickers=tickers,
        )

        # Analyze with Claude (fast, Haiku)
        analysis = await analyze_article_with_claude(title, body, tickers, impact)

        direction = analysis.get("direction", "neutral")
        confidence = float(analysis.get("confidence", 0.0))
        action = analysis.get("suggested_action", "hold")
        urgency = int(analysis.get("urgency_minutes", 60))
        reasoning = analysis.get("reasoning", "")

        # Generate signal for each affected ticker
        affected = analysis.get("affected_tickers", [])
        if not affected:
            affected = [{"ticker": t, "impact": direction, "magnitude": confidence} for t in tickers]

        for at in affected:
            t = at.get("ticker", tickers[0] if tickers else "")
            if not t:
                continue

            pub_at = article.get("published_at")
            if isinstance(pub_at, str):
                try:
                    pub_at = datetime.fromisoformat(pub_at)
                except ValueError:
                    pub_at = datetime.now(tz=timezone.utc)
            elif not isinstance(pub_at, datetime):
                pub_at = datetime.now(tz=timezone.utc)

            signal = NewsSignal(
                ticker=t,
                impact=impact,
                direction=at.get("impact", direction),
                confidence=float(at.get("magnitude", confidence)),
                headline=title[:200],
                summary=reasoning[:300],
                source=source,
                published_at=pub_at,
                suggested_action=action,
                urgency_minutes=urgency,
            )
            signals.append(signal)

            logger.info(
                "news_reactor.signal",
                ticker=t,
                impact=impact.value,
                direction=signal.direction,
                confidence=signal.confidence,
                action=action,
                urgency_min=urgency,
            )

    return signals


class NewsReactor:
    """Continuous news monitoring and reaction engine.

    Designed to run alongside the daily pipeline, checking feeds
    every N minutes for market-moving events.
    """

    def __init__(
        self,
        check_interval_minutes: int = 5,
        min_impact: NewsImpact = NewsImpact.HIGH,
    ) -> None:
        self.check_interval = check_interval_minutes
        self.min_impact = min_impact
        self._seen_titles: set[str] = set()  # deduplication

    async def check_feeds(self) -> list[NewsSignal]:
        """Check all configured news feeds and return new signals.

        Deduplicates articles by title hash.
        """
        try:
            from src.data.news_parser import fetch_news
        except ImportError:
            logger.warning("news_parser not available")
            return []

        articles = await fetch_news()

        # Deduplicate
        new_articles = []
        for a in articles:
            title = a.get("title", "")
            if title and title not in self._seen_titles:
                self._seen_titles.add(title)
                new_articles.append(a)

        if not new_articles:
            return []

        logger.info("news_reactor.new_articles", count=len(new_articles))
        return await process_news_feed(new_articles, self.min_impact)

    def should_act(self, signal: NewsSignal) -> bool:
        """Determine if a news signal warrants immediate action.

        Returns True for CRITICAL signals with confidence > 0.6,
        or HIGH signals with confidence > 0.7.
        """
        if signal.impact == NewsImpact.CRITICAL and signal.confidence > 0.6:
            return True
        if signal.impact == NewsImpact.HIGH and signal.confidence > 0.7:
            return True
        return False

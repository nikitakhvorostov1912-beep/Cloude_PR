"""Extract business processes from interview transcripts using LLM (Ollama or Anthropic)."""
import json
import logging
import os
import re

import requests

from src.analysis.prompts import (
    EXTRACT_PROCESSES_PROMPT,
    GENERATE_BPMN_JSON_PROMPT,
    GENERATE_PROCESS_CARD_PROMPT,
    GENERATE_TO_BE_PROMPT,
    SYSTEM_PROMPT_ANALYST,
)
from src.exceptions import LLMConnectionError, LLMResponseError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM Backends
# ---------------------------------------------------------------------------

def _call_ollama(config: dict, system: str, user_prompt: str) -> str:
    """Call Ollama local LLM via HTTP API."""
    ollama_cfg = config.get("analysis", {}).get("ollama", {})
    url = ollama_cfg.get("url", "http://localhost:11434")
    model = ollama_cfg.get("model", "gemma2")
    timeout = ollama_cfg.get("timeout", 300)

    payload = {
        "model": model,
        "system": system,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "temperature": config.get("analysis", {}).get("temperature", 0.1),
            "num_predict": config.get("analysis", {}).get("max_tokens", 4096),
        },
    }

    try:
        resp = requests.post(
            f"{url}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.ConnectionError:
        raise LLMConnectionError(
            f"Не удалось подключиться к Ollama по адресу {url}.\n"
            "Убедитесь что Ollama запущена: ollama serve\n"
            "Скачать: https://ollama.com/download"
        )
    except requests.Timeout:
        raise LLMConnectionError(
            f"Ollama не ответила за {timeout} секунд. "
            "Попробуйте увеличить analysis.ollama.timeout в config.yaml "
            "или использовать более лёгкую модель (mistral, gemma2)."
        )


def _call_anthropic(config: dict, system: str, user_prompt: str) -> str:
    """Call Anthropic Claude API (платный fallback)."""
    from anthropic import Anthropic

    anthropic_cfg = config.get("analysis", {}).get("anthropic", {})
    api_key = (
        anthropic_cfg.get("api_key")
        or os.environ.get("ANTHROPIC_API_KEY", "")
    )
    if not api_key:
        raise ValueError(
            "Anthropic API key not set. Set ANTHROPIC_API_KEY env var or "
            "analysis.anthropic.api_key in config.yaml\n"
            "Или переключитесь на Ollama: analysis.provider: 'ollama'"
        )

    client = Anthropic(api_key=api_key)
    model = anthropic_cfg.get("model", "claude-sonnet-4-20250514")
    temperature = config.get("analysis", {}).get("temperature", 0.1)
    max_tokens = config.get("analysis", {}).get("max_tokens", 4096)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _call_llm(config: dict, system: str, user_prompt: str) -> str:
    """Route LLM call to the configured provider."""
    provider = config.get("analysis", {}).get("provider", "ollama")

    if provider == "ollama":
        return _call_ollama(config, system, user_prompt)
    elif provider == "anthropic":
        return _call_anthropic(config, system, user_prompt)
    else:
        raise ValueError(
            f"Неизвестный LLM провайдер: {provider}. "
            "Используйте 'ollama' или 'anthropic' в config.yaml"
        )


# ---------------------------------------------------------------------------
# JSON Parsing
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks and common LLM quirks."""
    # Try to extract from ```json ... ``` or ``` ... ``` blocks
    code_block = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()

    # Fix common LLM quirk: double braces {{ ... }}
    cleaned = text.strip()
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        cleaned = cleaned[1:-1]

    # Try direct parse
    for candidate in [cleaned, text]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        json_str = text[brace_start:brace_end + 1]
        # Fix double braces within extracted JSON
        if json_str.startswith("{{"):
            json_str = json_str[1:]
        if json_str.endswith("}}"):
            json_str = json_str[:-1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try original without double-brace fix
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

    raise LLMResponseError(
        f"Не удалось извлечь JSON из ответа LLM. "
        f"Начало ответа: {text[:200]}..."
    )


def _call_llm_with_retry(config: dict, system: str, user_prompt: str, max_retries: int = 3) -> str:
    """Call LLM with retry on failure."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = _call_llm(config, system, user_prompt)
            # Verify we can parse JSON from the response
            _parse_json_response(response)
            return response
        except (ValueError, LLMResponseError, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
            if attempt < max_retries - 1:
                user_prompt = (
                    f"{user_prompt}\n\n"
                    "ВАЖНО: Ответь ТОЛЬКО валидным JSON без пояснений. "
                    'Начни ответ с одной открывающей фигурной скобки и закончи одной закрывающей.'
                )
        except LLMConnectionError:
            raise  # Don't retry on connection issues
    raise LLMResponseError(f"Не удалось получить валидный JSON после {max_retries} попыток: {last_error}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def check_ollama_available(config: dict) -> None:
    """Check that Ollama is running and the configured model is available."""
    provider = config.get("analysis", {}).get("provider", "ollama")
    if provider != "ollama":
        return

    ollama_cfg = config.get("analysis", {}).get("ollama", {})
    url = ollama_cfg.get("url", "http://localhost:11434")
    model = ollama_cfg.get("model", "gemma2")

    # Check connection
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        raise LLMConnectionError(
            f"Ollama не запущена по адресу {url}.\n"
            "Запустите: ollama serve\n"
            "Скачать: https://ollama.com/download"
        )
    except requests.Timeout:
        raise LLMConnectionError(f"Ollama не отвечает по адресу {url}.")

    # Check model availability (compare both full name and base name)
    models_data = resp.json().get("models", [])
    available_full = [m.get("name", "") for m in models_data]
    available_base = [m.get("name", "").split(":")[0] for m in models_data]
    model_base = model.split(":")[0]
    if model not in available_full and model_base not in available_base:
        raise LLMConnectionError(
            f"Модель '{model}' не найдена в Ollama.\n"
            f"Доступные модели: {', '.join(available_full) or 'нет'}\n"
            f"Скачайте модель: ollama pull {model}"
        )


def _estimate_tokens(text: str) -> int:
    """Rough token estimate for Russian text (~4 chars per token)."""
    return len(text) // 4


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_processes(transcript: dict, config: dict) -> dict:
    """Extract AS IS business processes from transcript."""
    check_ollama_available(config)

    transcript_text = transcript.get("full_text", "")
    if not transcript_text:
        transcript_text = "\n".join(
            f"{seg['speaker']}: {seg['text']}"
            for seg in transcript.get("dialogue", transcript.get("segments", []))
            if seg.get("text")
        )

    max_tokens = config.get("analysis", {}).get("max_tokens", 4096)
    # Leave room for prompt template + response: use ~60% of context for transcript
    max_input_tokens = max_tokens * 3
    estimated_tokens = _estimate_tokens(transcript_text)

    if estimated_tokens > max_input_tokens:
        logger.warning(
            "Транскрипт слишком длинный (%d токенов, лимит %d). Разбиваю на части.",
            estimated_tokens, max_input_tokens,
        )
        return _extract_processes_chunked(transcript_text, transcript, config, max_input_tokens)

    prompt = EXTRACT_PROCESSES_PROMPT.format(transcript=transcript_text)
    response = _call_llm_with_retry(config, SYSTEM_PROMPT_ANALYST, prompt)

    processes = _parse_json_response(response)
    processes["transcript_metadata"] = transcript.get("metadata", {})

    return processes


def _extract_processes_chunked(text: str, transcript: dict, config: dict, max_tokens: int) -> dict:
    """Split long transcript into chunks and merge extracted processes."""
    # Split by paragraphs, keeping chunks under token limit
    chars_per_chunk = max_tokens * 4  # ~4 chars per token
    chunks = []
    current = []
    current_len = 0

    for line in text.split("\n"):
        line_len = len(line) + 1
        if current_len + line_len > chars_per_chunk and current:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    logger.info("Разбит на %d частей для обработки", len(chunks))

    all_processes = []
    for i, chunk in enumerate(chunks, 1):
        logger.info("Обработка части %d/%d", i, len(chunks))
        prompt = EXTRACT_PROCESSES_PROMPT.format(transcript=chunk)
        response = _call_llm_with_retry(config, SYSTEM_PROMPT_ANALYST, prompt)
        chunk_result = _parse_json_response(response)
        all_processes.extend(chunk_result.get("processes", []))

    # Re-number process IDs
    for i, proc in enumerate(all_processes, 1):
        proc["id"] = f"proc_{i}"

    result = {
        "processes": all_processes,
        "transcript_metadata": transcript.get("metadata", {}),
    }
    return result


def generate_to_be(as_is_processes: dict, config: dict) -> dict:
    """Generate TO BE processes based on AS IS analysis."""
    processes_json = json.dumps(as_is_processes, ensure_ascii=False, indent=2)
    prompt = GENERATE_TO_BE_PROMPT.format(processes_json=processes_json)
    response = _call_llm_with_retry(config, SYSTEM_PROMPT_ANALYST, prompt)

    return _parse_json_response(response)


def generate_bpmn_json(process: dict, config: dict, detail_level: str = "high_level") -> dict:
    """Generate BPMN JSON representation of a process."""
    process_json = json.dumps(process, ensure_ascii=False, indent=2)
    prompt = GENERATE_BPMN_JSON_PROMPT.format(
        process_json=process_json,
        detail_level=detail_level,
    )
    response = _call_llm_with_retry(config, SYSTEM_PROMPT_ANALYST, prompt)

    return _parse_json_response(response)


def generate_process_card(process: dict, config: dict) -> dict:
    """Generate a process card for documentation."""
    process_json = json.dumps(process, ensure_ascii=False, indent=2)
    prompt = GENERATE_PROCESS_CARD_PROMPT.format(process_json=process_json)
    response = _call_llm_with_retry(config, SYSTEM_PROMPT_ANALYST, prompt)

    return _parse_json_response(response)

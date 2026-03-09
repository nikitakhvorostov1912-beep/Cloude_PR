# Project: Interview-to-BPMN

## Stack
- Python 3.11, Streamlit 1.54, faster-whisper (CPU), Ollama (mistral 7B)
- lxml (BPMN XML), python-docx (Word), typer+rich (CLI)

## Architecture (refactored)
```
src/config.py           → AppConfig (frozen dataclass) + ProjectDir
src/exceptions.py       → Custom exception hierarchy (AppError base)
src/logging_config.py   → Centralized logging setup
src/services/           → Service Layer (orchestration)
  transcription_service → preprocess → transcribe → format → save
  analysis_service      → extract_processes → validate → generate_bpmn_json
  bpmn_service          → json_to_xml → render
src/transcription/      → preprocessor → transcriber → formatter
src/analysis/           → prompts → process_extractor → validator
src/bpmn/               → json_to_bpmn → layout → renderer
src/docs/               → doc_generator
src/web/                → app.py → pages/ (6 pages)
```

## Key Design Decisions
- AppConfig is frozen (immutable) — loaded once via `@st.cache_resource`
- Pages receive `ProjectDir` and `AppConfig` instead of raw Path + dict
- `config.to_dict()` used for backward compat with functions expecting dict
- json_to_bpmn.py decoupled from analysis (no longer imports generate_bpmn_json)
- Custom exceptions: LLMConnectionError, LLMResponseError, TranscriptionError, etc.

## Config
- `config.yaml` — single config for all settings
- `transcription.mode`: "local_cpu" (default), "local" (GPU), "api" (OpenAI)
- `analysis.provider`: "ollama" (default), "anthropic"

## Key Patterns
- WhisperModel cached via module-level `_whisper_model_cache` dict
- LLM calls use `_call_llm_with_retry()` (3 attempts for JSON parsing)
- BPMN: JSON intermediate format → lxml XML → bpmn-to-image PNG/SVG

## Tests
- 33 tests in `tests/` covering formatter, json_to_bpmn, layout, validator
- Run: `python -m pytest tests/ -v`

## Launch
- `start.bat` / `start.pyw` — auto-starts Ollama, launches Streamlit, opens browser
- Desktop shortcut created via `create_shortcut.vbs`

## Completed Work
- Full review: 13 bugs found and fixed, ruff 0 errors, 33/33 tests pass
- Architecture refactored: immutable config, service layer, decoupled modules, custom exceptions

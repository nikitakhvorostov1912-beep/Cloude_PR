"""Custom exception hierarchy for Interview-to-BPMN."""


class AppError(Exception):
    """Base exception for all application errors."""


class TranscriptionError(AppError):
    """Error during audio transcription."""


class PreprocessingError(AppError):
    """Error during audio preprocessing."""


class LLMConnectionError(AppError):
    """Cannot connect to LLM backend (Ollama or Anthropic)."""


class LLMResponseError(AppError):
    """LLM returned invalid or unparseable response."""


class BPMNGenerationError(AppError):
    """Error during BPMN generation or conversion."""


class ConfigError(AppError):
    """Invalid or missing configuration."""


class ProjectError(AppError):
    """Error related to project directory or files."""

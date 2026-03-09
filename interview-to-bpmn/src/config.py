"""Immutable application configuration and project directory management."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TranscriptionLocalCpuConfig:
    model: str = "medium"
    language: str = "ru"
    compute_type: str = "int8"
    beam_size: int = 5


@dataclass(frozen=True)
class TranscriptionLocalConfig:
    server_url: str = "http://localhost:8000"
    model: str = "large-v3"
    language: str = "ru"
    device: str = "cuda"
    batch_size: int = 16
    compute_type: str = "float16"
    use_remote: bool = False


@dataclass(frozen=True)
class TranscriptionApiConfig:
    api_key: str = ""
    model: str = "whisper-1"
    language: str = "ru"


@dataclass(frozen=True)
class TranscriptionConfig:
    mode: str = "local_cpu"
    local_cpu: TranscriptionLocalCpuConfig = field(default_factory=TranscriptionLocalCpuConfig)
    local: TranscriptionLocalConfig = field(default_factory=TranscriptionLocalConfig)
    api: TranscriptionApiConfig = field(default_factory=TranscriptionApiConfig)


@dataclass(frozen=True)
class DiarizationConfig:
    min_speakers: int = 0
    max_speakers: int = 0
    hf_token: str = ""


@dataclass(frozen=True)
class OllamaConfig:
    url: str = "http://localhost:11434"
    model: str = "mistral"
    timeout: int = 300


@dataclass(frozen=True)
class AnthropicConfig:
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""


@dataclass(frozen=True)
class AnalysisConfig:
    provider: str = "ollama"
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass(frozen=True)
class BpmnConfig:
    output_format: str = "png"
    scale: int = 2
    generate_both_levels: bool = True


@dataclass(frozen=True)
class DocsConfig:
    gost_compliance: bool = True
    templates_dir: str = "src/docs/templates"
    output_format: str = "docx"
    language: str = "ru"


@dataclass(frozen=True)
class ProjectConfig:
    data_dir: str = "data/projects"
    auto_save: bool = True


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    supported_formats: tuple = ("mp3", "wav", "m4a", "ogg", "flac", "wma", "aac")


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration loaded from config.yaml."""
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    diarization: DiarizationConfig = field(default_factory=DiarizationConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    bpmn: BpmnConfig = field(default_factory=BpmnConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "AppConfig":
        """Load config from YAML file."""
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, raw: dict) -> "AppConfig":
        """Build AppConfig from a raw dict."""
        t = raw.get("transcription", {})
        return cls(
            transcription=TranscriptionConfig(
                mode=t.get("mode", "local_cpu"),
                local_cpu=TranscriptionLocalCpuConfig(**{
                    k: v for k, v in t.get("local_cpu", {}).items()
                    if k in TranscriptionLocalCpuConfig.__dataclass_fields__
                }),
                local=TranscriptionLocalConfig(**{
                    k: v for k, v in t.get("local", {}).items()
                    if k in TranscriptionLocalConfig.__dataclass_fields__
                }),
                api=TranscriptionApiConfig(**{
                    k: v for k, v in t.get("api", {}).items()
                    if k in TranscriptionApiConfig.__dataclass_fields__
                }),
            ),
            diarization=DiarizationConfig(**{
                k: v for k, v in raw.get("diarization", {}).items()
                if k in DiarizationConfig.__dataclass_fields__
            }),
            analysis=AnalysisConfig(
                provider=raw.get("analysis", {}).get("provider", "ollama"),
                ollama=OllamaConfig(**{
                    k: v for k, v in raw.get("analysis", {}).get("ollama", {}).items()
                    if k in OllamaConfig.__dataclass_fields__
                }),
                anthropic=AnthropicConfig(**{
                    k: v for k, v in raw.get("analysis", {}).get("anthropic", {}).items()
                    if k in AnthropicConfig.__dataclass_fields__
                }),
                temperature=raw.get("analysis", {}).get("temperature", 0.1),
                max_tokens=raw.get("analysis", {}).get("max_tokens", 4096),
            ),
            bpmn=BpmnConfig(**{
                k: v for k, v in raw.get("bpmn", {}).items()
                if k in BpmnConfig.__dataclass_fields__
            }),
            docs=DocsConfig(**{
                k: v for k, v in raw.get("docs", {}).items()
                if k in DocsConfig.__dataclass_fields__
            }),
            project=ProjectConfig(**{
                k: v for k, v in raw.get("project", {}).items()
                if k in ProjectConfig.__dataclass_fields__
            }),
            audio=AudioConfig(**{
                k: v for k, v in raw.get("audio", {}).items()
                if k in AudioConfig.__dataclass_fields__ and k != "supported_formats"
            }, supported_formats=tuple(raw.get("audio", {}).get(
                "supported_formats", ["mp3", "wav", "m4a", "ogg", "flac", "wma", "aac"]
            ))),
        )

    def to_dict(self) -> dict:
        """Convert back to plain dict (for backward compatibility)."""
        import dataclasses
        result = {}
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if dataclasses.is_dataclass(val):
                result[f.name] = self._dataclass_to_dict(val)
            else:
                result[f.name] = val
        return result

    @staticmethod
    def _dataclass_to_dict(obj) -> dict:
        import dataclasses
        result = {}
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            if dataclasses.is_dataclass(val):
                result[f.name] = AppConfig._dataclass_to_dict(val)
            elif isinstance(val, tuple):
                result[f.name] = list(val)
            else:
                result[f.name] = val
        return result


class ProjectDir:
    """Manages project directory structure. Single source of truth for all paths."""

    def __init__(self, project_name: str, base: str | Path = "data/projects"):
        self.name = project_name
        self.root = Path(base) / project_name
        self.audio = self.root / "audio"
        self.transcripts = self.root / "transcripts"
        self.processes = self.root / "processes"
        self.bpmn = self.root / "bpmn"
        self.output = self.root / "output"

    def ensure_dirs(self):
        """Create all project subdirectories if they don't exist."""
        for d in [self.audio, self.transcripts, self.processes,
                  self.bpmn, self.output]:
            d.mkdir(parents=True, exist_ok=True)

    def audio_count(self) -> int:
        if not self.audio.exists():
            return 0
        exts = ("*.mp3", "*.wav", "*.m4a", "*.ogg", "*.flac", "*.wma", "*.aac")
        return sum(len(list(self.audio.glob(e))) for e in exts)

    def transcript_count(self) -> int:
        return len(list(self.transcripts.glob("*.json")))

    def process_count(self) -> int:
        return len(list(self.processes.glob("*.json")))

    def bpmn_count(self) -> int:
        return len(list(self.bpmn.glob("*.bpmn")))

    def doc_count(self) -> int:
        return len(list(self.output.glob("*.docx")))

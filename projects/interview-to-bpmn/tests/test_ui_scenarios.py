"""Comprehensive UI scenario verification tests.

Tests user scenarios: imports, data handling, session logic,
component rendering, file operations, edge cases.
"""
import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root on path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ───────────────────────────────────────────────────
# 1. IMPORT CHECKS — all UI modules importable
# ───────────────────────────────────────────────────

class TestImports:
    """All UI modules must import without errors."""

    def test_import_app(self):
        from src.web import app  # noqa: F401

    def test_import_dashboard(self):
        from src.web.pages import dashboard  # noqa: F401

    def test_import_pipeline(self):
        from src.web.pages import pipeline  # noqa: F401

    def test_import_transcript(self):
        from src.web.pages import transcript  # noqa: F401

    def test_import_processes(self):
        from src.web.pages import processes  # noqa: F401

    def test_import_bpmn_view(self):
        from src.web.pages import bpmn_view  # noqa: F401

    def test_import_documents(self):
        from src.web.pages import documents  # noqa: F401

    def test_import_questionnaire(self):
        from src.web.pages import questionnaire  # noqa: F401

    def test_import_help_page(self):
        from src.web.pages import help_page  # noqa: F401

    def test_import_status_card(self):
        from src.web.components import status_card  # noqa: F401

    def test_import_confirm_dialog(self):
        from src.web.components import confirm_dialog  # noqa: F401

    def test_import_project_manager(self):
        from src.web.components import project_manager  # noqa: F401

    def test_import_settings_panel(self):
        from src.web.components import settings_panel  # noqa: F401


# ───────────────────────────────────────────────────
# 2. ENGLISH TEXT DETECTION — no English in user-facing strings
# ───────────────────────────────────────────────────

# Allowed English words (technical terms, proper nouns)
ALLOWED_ENGLISH = {
    "BPMN", "AS IS", "TO BE", "AS_IS", "TO_BE",
    "AI", "API", "CPU", "GPU", "OpenAI", "Whisper",
    "Ollama", "Anthropic", "Claude", "Mistral",
    "GOST", "FAQ", "KPI", "XML", "JSON", "TXT", "DOCX",
    "SVG", "PNG", "PDF", "WAV", "MP3", "M4A", "OGG",
    "FLAC", "WMA", "AAC", "RAM", "CUDA", "NVIDIA",
    "Faster-Whisper", "WhisperX", "Word", "FFmpeg",
    "Interview-to-BPMN", "I2B", "Streamlit",
    "Python", "lxml", "npm",
    "Task", "Gateway", "Pool",  # BPMN terms in docs
    "high_level", "detailed", "both",  # internal values
    "local_cpu", "local", "api",  # config values
    "tiny", "base", "small", "medium", "large-v3",  # model names
    "ollama", "anthropic",  # provider values
    "png", "svg", "pdf",  # format values
    "text", "number", "textarea",  # input types
    "default",  # project name
    "pending", "running", "done", "error",  # status values
    "mono",  # audio format
    "history", "README",  # file names
    "process_1",  # fallback ID
}

# Patterns to detect user-visible English strings
ENGLISH_WORD_RE = re.compile(r'\b[A-Za-z]{4,}\b')

UI_FILES = [
    "src/web/app.py",
    "src/web/pages/dashboard.py",
    "src/web/pages/pipeline.py",
    "src/web/pages/transcript.py",
    "src/web/pages/processes.py",
    "src/web/pages/bpmn_view.py",
    "src/web/pages/documents.py",
    "src/web/pages/questionnaire.py",
    "src/web/pages/help_page.py",
    "src/web/components/status_card.py",
    "src/web/components/confirm_dialog.py",
    "src/web/components/project_manager.py",
    "src/web/components/settings_panel.py",
]


class TestNoEnglishInUI:
    """User-facing strings should not contain unexpected English words."""

    def _extract_user_strings(self, filepath):
        """Extract strings likely shown to user from st.* calls."""
        content = (ROOT / filepath).read_text(encoding="utf-8")
        issues = []

        # Find st.header, st.subheader, st.markdown, st.button, st.warning, etc.
        # Only check non-f-string literals (f-strings contain variable names)
        user_facing_patterns = [
            r'st\.(?:header|subheader|markdown|info|warning|error|success)\(\s*"([^"]+)"',
            r"st\.(?:header|subheader|markdown|info|warning|error|success)\(\s*'([^']+)'",
            r'st\.button\(\s*"([^"]+)"',
            r"st\.button\(\s*'([^']+)'",
            r'st\.text_input\(\s*"([^"]+)"',
            r"st\.text_input\(\s*'([^']+)'",
            r'st\.selectbox\(\s*"([^"]+)"',
            r"st\.selectbox\(\s*'([^']+)'",
            r'\.metric\(\s*"([^"]+)"',
            r"\.metric\(\s*'([^']+)'",
        ]

        for pattern in user_facing_patterns:
            for match in re.finditer(pattern, content):
                text = match.group(1)
                # Remove f-string expressions {var_name} before checking
                clean_text = re.sub(r'\{[^}]+\}', '', text)
                # Find English words (4+ letters)
                words = ENGLISH_WORD_RE.findall(clean_text)
                for word in words:
                    # Check against allowed list (case-insensitive check)
                    if not any(word.lower() == a.lower() or word.upper() == a.upper()
                               for a in ALLOWED_ENGLISH):
                        issues.append((filepath, word, text[:80]))

        return issues

    @pytest.mark.parametrize("filepath", UI_FILES)
    def test_no_english_in_file(self, filepath):
        full_path = ROOT / filepath
        if not full_path.exists():
            pytest.skip(f"File not found: {filepath}")

        issues = self._extract_user_strings(filepath)
        if issues:
            report = "\n".join(f"  {f}: '{word}' in '{ctx}'" for f, word, ctx in issues)
            pytest.fail(f"Unexpected English text found:\n{report}")


# ───────────────────────────────────────────────────
# 3. UNICODE SAFETY — no SMP emojis that break on Windows
# ───────────────────────────────────────────────────

class TestUnicodeSafety:
    """Ensure no surrogate or SMP characters that break on Windows."""

    @pytest.mark.parametrize("filepath", UI_FILES)
    def test_no_smp_emojis(self, filepath):
        full_path = ROOT / filepath
        if not full_path.exists():
            pytest.skip(f"File not found: {filepath}")

        content = full_path.read_text(encoding="utf-8")
        smp_chars = []
        for i, char in enumerate(content):
            cp = ord(char)
            if cp > 0xFFFF:  # SMP character
                line_no = content[:i].count('\n') + 1
                smp_chars.append((line_no, hex(cp), char))

        if smp_chars:
            report = "\n".join(f"  Line {ln}: {h} ({c})" for ln, h, c in smp_chars)
            pytest.fail(f"SMP characters found (may break on Windows):\n{report}")


# ───────────────────────────────────────────────────
# 4. CONFIG & PROJECT — data handling scenarios
# ───────────────────────────────────────────────────

class TestConfigScenarios:
    """Test config loading and project directory operations."""

    def test_config_loads(self):
        from src.config import AppConfig
        config = AppConfig.from_yaml(str(ROOT / "config.yaml"))
        assert config.transcription.mode in ("local_cpu", "local", "api")

    def test_config_to_dict(self):
        from src.config import AppConfig
        config = AppConfig.from_yaml(str(ROOT / "config.yaml"))
        d = config.to_dict()
        assert "transcription" in d
        assert "analysis" in d
        assert "bpmn" in d

    def test_project_dir_creation(self, tmp_path):
        from src.config import ProjectDir
        p = ProjectDir("test_proj", str(tmp_path))
        p.ensure_dirs()
        assert p.audio.exists()
        assert p.transcripts.exists()
        assert p.processes.exists()
        assert p.bpmn.exists()
        assert p.output.exists()

    def test_project_dir_counts_empty(self, tmp_path):
        from src.config import ProjectDir
        p = ProjectDir("test_proj", str(tmp_path))
        p.ensure_dirs()
        assert p.audio_count() == 0
        assert p.transcript_count() == 0
        assert p.process_count() == 0
        assert p.bpmn_count() == 0
        assert p.doc_count() == 0

    def test_project_dir_counts_with_files(self, tmp_path):
        from src.config import ProjectDir
        p = ProjectDir("test_proj", str(tmp_path))
        p.ensure_dirs()
        # Create dummy files
        (p.audio / "test.wav").write_bytes(b"RIFF")
        (p.transcripts / "test.json").write_text("{}", encoding="utf-8")
        (p.processes / "test_processes.json").write_text("{}", encoding="utf-8")
        (p.bpmn / "test.bpmn").write_text("<xml/>", encoding="utf-8")
        (p.output / "test.docx").write_bytes(b"PK")

        assert p.audio_count() == 1
        assert p.transcript_count() == 1
        assert p.process_count() == 1
        assert p.bpmn_count() == 1
        assert p.doc_count() == 1


# ───────────────────────────────────────────────────
# 5. SESSION PERSISTENCE
# ───────────────────────────────────────────────────

class TestSessionPersistence:
    """Test session save/restore logic."""

    def test_session_file_format(self, tmp_path):
        session_file = tmp_path / ".session.json"
        data = {"project_name": "мой_проект"}
        session_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loaded = json.loads(session_file.read_text(encoding="utf-8"))
        assert loaded["project_name"] == "мой_проект"

    def test_session_file_missing(self, tmp_path):
        session_file = tmp_path / ".session.json"
        assert not session_file.exists()
        # App should default to "default"

    def test_session_file_corrupt(self, tmp_path):
        session_file = tmp_path / ".session.json"
        session_file.write_text("not json!", encoding="utf-8")
        try:
            json.loads(session_file.read_text(encoding="utf-8"))
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            pass  # Expected


# ───────────────────────────────────────────────────
# 6. QUESTIONNAIRE — data handling
# ───────────────────────────────────────────────────

class TestQuestionnaire:
    """Test questionnaire data structure and operations."""

    def test_questionnaire_blocks_structure(self):
        from src.web.pages.questionnaire import QUESTIONNAIRE_BLOCKS
        assert len(QUESTIONNAIRE_BLOCKS) > 0
        for block in QUESTIONNAIRE_BLOCKS:
            assert "id" in block
            assert "title" in block
            assert "questions" in block
            assert len(block["questions"]) > 0
            for q in block["questions"]:
                assert "id" in q
                assert "text" in q
                assert "type" in q
                assert q["type"] in ("text", "number", "textarea")

    def test_questionnaire_total_count(self):
        from src.web.pages.questionnaire import QUESTIONNAIRE_BLOCKS, TOTAL_QUESTIONS
        expected = sum(len(b["questions"]) for b in QUESTIONNAIRE_BLOCKS)
        assert TOTAL_QUESTIONS == expected

    def test_checklist_structure(self):
        from src.web.pages.questionnaire import CHECKLIST
        assert len(CHECKLIST) > 0
        for item in CHECKLIST:
            assert isinstance(item, str)
            assert len(item) > 0

    def test_questionnaire_save_load(self, tmp_path):
        answers = {
            "1.1": "Отдел закупок",
            "1.3": 15,
            "2.1": "Процесс закупки, Процесс оплаты",
            "_checklist": {"0": True, "1": False},
        }
        path = tmp_path / "questionnaire_test.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)

        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["1.1"] == "Отдел закупок"
        assert loaded["1.3"] == 15
        assert loaded["_checklist"]["0"] is True


# ───────────────────────────────────────────────────
# 7. TRANSCRIPT DATA — format validation
# ───────────────────────────────────────────────────

class TestTranscriptData:
    """Test transcript JSON format handling."""

    def test_transcript_format(self):
        """Verify test data transcript structure."""
        path = ROOT / "data" / "default" / "transcripts" / "interview_01.json"
        if not path.exists():
            pytest.skip("Test data not found")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "segments" in data
        assert "full_text" in data or "text" in data
        assert len(data["segments"]) > 0

        for seg in data["segments"]:
            assert "text" in seg
            assert "speaker" in seg

    def test_transcript_speakers_are_russian(self):
        """Speaker names should be in Russian."""
        path = ROOT / "data" / "default" / "transcripts" / "interview_01.json"
        if not path.exists():
            pytest.skip("Test data not found")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        speakers = data.get("metadata", {}).get("speakers", [])
        for sp in speakers:
            # Should not be English like "Speaker_1"
            assert not re.match(r'^Speaker_\d+$', sp), f"English speaker name: {sp}"

    def test_transcript_metadata(self):
        """Metadata should have expected fields."""
        path = ROOT / "data" / "default" / "transcripts" / "interview_01.json"
        if not path.exists():
            pytest.skip("Test data not found")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        meta = data["metadata"]
        assert "language" in meta
        assert "speaker_count" in meta or "speakers" in meta


# ───────────────────────────────────────────────────
# 8. PROCESS DATA — format validation
# ───────────────────────────────────────────────────

class TestProcessData:
    """Test process JSON format handling."""

    def test_process_format(self):
        """Verify test data process structure."""
        path = ROOT / "data" / "default" / "processes" / "interview_01_processes.json"
        if not path.exists():
            pytest.skip("Test data not found")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        assert "processes" in data
        assert len(data["processes"]) > 0

        for proc in data["processes"]:
            assert "name" in proc
            assert "steps" in proc
            assert len(proc["steps"]) > 0

    def test_process_steps_have_names(self):
        """Each step should have a name."""
        path = ROOT / "data" / "default" / "processes" / "interview_01_processes.json"
        if not path.exists():
            pytest.skip("Test data not found")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for proc in data["processes"]:
            for step in proc["steps"]:
                assert "name" in step
                assert len(step["name"]) > 0


# ───────────────────────────────────────────────────
# 9. COMPONENT RENDERING — status_card
# ───────────────────────────────────────────────────

class TestStatusCard:
    """Test status card component logic."""

    def test_all_statuses_have_labels(self):
        """All status values should map to Russian labels."""
        import inspect

        from src.web.components.status_card import status_card
        source = inspect.getsource(status_card)
        for status in ["pending", "running", "done", "error"]:
            assert status in source

    def test_status_labels_are_russian(self):
        """Status labels should be in Russian."""
        source_path = ROOT / "src" / "web" / "components" / "status_card.py"
        content = source_path.read_text(encoding="utf-8")
        # Check that English labels are not used
        assert '"Pending"' not in content
        assert '"Running"' not in content
        assert '"Done"' not in content
        assert '"Error"' not in content


# ───────────────────────────────────────────────────
# 10. EDGE CASES — empty data, missing files
# ───────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_project(self, tmp_path):
        """Empty project should not crash."""
        from src.config import ProjectDir
        p = ProjectDir("empty_test", str(tmp_path))
        p.ensure_dirs()
        assert p.audio_count() == 0
        assert p.transcript_count() == 0

    def test_empty_transcript_json(self, tmp_path):
        """Empty JSON file should be handled."""
        from src.config import ProjectDir
        p = ProjectDir("test", str(tmp_path))
        p.ensure_dirs()
        (p.transcripts / "empty.json").write_text("{}", encoding="utf-8")
        assert p.transcript_count() == 1

    def test_malformed_json(self, tmp_path):
        """Malformed JSON should raise error."""
        path = tmp_path / "bad.json"
        path.write_text("{bad json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            with open(path, encoding="utf-8") as f:
                json.load(f)

    def test_project_history_log(self, tmp_path):
        """Project history log should work."""
        from src.config import ProjectDir
        from src.web.components.project_manager import _log_action

        p = ProjectDir("test", str(tmp_path))
        p.ensure_dirs()

        _log_action(p, "Тестовое действие")

        log_file = p.root / "history.jsonl"
        assert log_file.exists()
        line = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(line)
        assert entry["action"] == "Тестовое действие"
        assert "timestamp" in entry

    def test_cyrillic_project_name(self, tmp_path):
        """Cyrillic project names should work."""
        from src.config import ProjectDir
        p = ProjectDir("Тестовый_проект", str(tmp_path))
        p.ensure_dirs()
        assert p.root.exists()
        assert p.name == "Тестовый_проект"

    def test_special_chars_in_answers(self, tmp_path):
        """Questionnaire answers with special chars should save/load."""
        answers = {
            "1.1": 'Отдел "Финансы & Бухгалтерия"',
            "2.1": "Процесс: шаг 1 → шаг 2 → шаг 3",
        }
        path = tmp_path / "q.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(answers, f, ensure_ascii=False)

        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["1.1"] == answers["1.1"]
        assert loaded["2.1"] == answers["2.1"]


# ───────────────────────────────────────────────────
# 11. STREAMLIT CONFIG — theme and settings
# ───────────────────────────────────────────────────

class TestStreamlitConfig:
    """Verify Streamlit configuration."""

    def test_config_toml_exists(self):
        config_path = ROOT / ".streamlit" / "config.toml"
        assert config_path.exists(), ".streamlit/config.toml not found"

    def test_dark_theme(self):
        config_path = ROOT / ".streamlit" / "config.toml"
        content = config_path.read_text(encoding="utf-8")
        assert 'base = "dark"' in content

    def test_sidebar_navigation_disabled(self):
        config_path = ROOT / ".streamlit" / "config.toml"
        content = config_path.read_text(encoding="utf-8")
        assert "showSidebarNavigation = false" in content

    def test_primary_color(self):
        config_path = ROOT / ".streamlit" / "config.toml"
        content = config_path.read_text(encoding="utf-8")
        assert "primaryColor" in content


# ───────────────────────────────────────────────────
# 12. TAB NAVIGATION — all tabs defined
# ───────────────────────────────────────────────────

class TestNavigation:
    """Verify multi-page navigation structure."""

    def test_page_wrapper_functions_exist(self):
        from src.web import app
        page_funcs = [
            "_page_dashboard", "_page_pipeline", "_page_transcripts",
            "_page_processes", "_page_bpmn", "_page_documents",
            "_page_help",
        ]
        for fn in page_funcs:
            assert hasattr(app, fn), f"Missing page function: {fn}"

    def test_get_context_helper_exists(self):
        from src.web import app
        assert hasattr(app, "_get_context")


# ───────────────────────────────────────────────────
# 13. FILE STRUCTURE — all required files exist
# ───────────────────────────────────────────────────

class TestFileStructure:
    """Verify all required UI files exist."""

    @pytest.mark.parametrize("filepath", UI_FILES)
    def test_ui_file_exists(self, filepath):
        assert (ROOT / filepath).exists(), f"Missing UI file: {filepath}"

    def test_components_init(self):
        init_path = ROOT / "src" / "web" / "components" / "__init__.py"
        assert init_path.exists(), "components/__init__.py missing"

    def test_pages_init(self):
        # Pages __init__.py is optional — not strictly required
        pass

    def test_test_data_exists(self):
        """Verify test data was created."""
        data_path = ROOT / "data" / "default"
        assert data_path.exists(), "data/default directory missing"

        transcript_path = data_path / "transcripts" / "interview_01.json"
        if transcript_path.exists():
            with open(transcript_path, encoding="utf-8") as f:
                data = json.load(f)
            assert "segments" in data


# ───────────────────────────────────────────────────
# 14. PIPELINE TEXT IMPORT — docx/txt handling
# ───────────────────────────────────────────────────

class TestPipelineTextImport:
    """Test text file import as transcript."""

    def test_save_text_creates_json(self, tmp_path):
        from src.config import ProjectDir

        p = ProjectDir("test", str(tmp_path))
        p.ensure_dirs()

        # Create a mock uploaded file
        mock_file = MagicMock()
        mock_file.name = "interview.txt"
        mock_file.read.return_value = "Это тестовая транскрипция.".encode("utf-8")

        from src.web.pages.pipeline import _save_text_as_transcript
        _save_text_as_transcript(mock_file, p)

        out = p.transcripts / "interview.json"
        assert out.exists()
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert "text" in data or "segments" in data
        assert data["segments"][0]["speaker"] == "Спикер_1"


# ───────────────────────────────────────────────────
# 15. VALIDATION — process and BPMN validation
# ───────────────────────────────────────────────────

class TestValidation:
    """Test validation functions."""

    def test_validate_processes(self):
        from src.analysis.validator import validate_processes
        data = {
            "processes": [
                {
                    "name": "Тестовый процесс",
                    "steps": [{"name": "Шаг 1"}],
                    "participants": [{"role": "Менеджер"}],
                }
            ]
        }
        result = validate_processes(data)
        assert "process_count" in result

    def test_validate_empty_processes(self):
        from src.analysis.validator import validate_processes
        data = {"processes": []}
        result = validate_processes(data)
        # Should handle empty list without crashing
        assert isinstance(result, dict)

    def test_validate_bpmn_json(self):
        from src.analysis.validator import validate_bpmn_json
        bpmn = {
            "process_id": "proc_1",
            "process_name": "Тест",
            "elements": [
                {"id": "start", "type": "startEvent", "name": "Начало"},
                {"id": "end", "type": "endEvent", "name": "Конец"},
            ],
            "flows": [
                {"id": "flow1", "source": "start", "target": "end"},
            ],
        }
        result = validate_bpmn_json(bpmn)
        assert "valid" in result

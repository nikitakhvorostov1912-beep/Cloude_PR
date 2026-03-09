"""Тесты: генерация документов Word и Excel."""
import pytest
from pathlib import Path

from app.docs.process_doc import ProcessDocGenerator
from app.docs.requirements_doc import RequirementsDocGenerator
from app.docs.gap_doc import GapReportGenerator


# -------------------------------------------------------------------
# ProcessDocGenerator
# -------------------------------------------------------------------


class TestProcessDocGenerator:
    """Tests for ProcessDocGenerator.generate."""

    def test_generate_creates_file(self, tmp_path, sample_processes):
        """generate creates a .docx file at the given path."""
        gen = ProcessDocGenerator(author="Тест", company="Тестовая компания")
        output = tmp_path / "processes.docx"
        processes = sample_processes["processes"]

        result = gen.generate(processes, output, project_name="Тестовый проект")

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_returns_path(self, tmp_path, sample_processes):
        """generate returns the output_path."""
        gen = ProcessDocGenerator()
        output = tmp_path / "result.docx"
        processes = sample_processes["processes"]

        result = gen.generate(processes, output, project_name="Проект")
        assert isinstance(result, Path)
        assert result == output

    def test_generate_empty_processes(self, tmp_path):
        """generate with empty processes list creates a document with placeholder text."""
        gen = ProcessDocGenerator()
        output = tmp_path / "empty.docx"

        result = gen.generate([], output, project_name="Пустой")
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_multiple_processes(self, tmp_path, sample_processes):
        """generate handles all processes from sample data."""
        gen = ProcessDocGenerator(author="Аналитик", company="ООО Тест")
        output = tmp_path / "all_processes.docx"
        processes = sample_processes["processes"]

        result = gen.generate(processes, output, project_name="Полный тест")
        assert result == output
        assert output.exists()

    def test_generate_single_process(self, tmp_path, sample_processes):
        """generate handles a single process correctly."""
        gen = ProcessDocGenerator()
        output = tmp_path / "single.docx"
        processes = [sample_processes["processes"][0]]

        result = gen.generate(processes, output, project_name="Один процесс")
        assert result == output
        assert output.exists()

    def test_generate_creates_parent_dirs(self, tmp_path, sample_processes):
        """generate creates parent directories if they don't exist."""
        gen = ProcessDocGenerator()
        output = tmp_path / "subdir" / "deep" / "processes.docx"
        processes = sample_processes["processes"][:1]

        result = gen.generate(processes, output, project_name="Тест")
        assert result == output
        assert output.exists()

    def test_generate_default_project_name(self, tmp_path, sample_processes):
        """generate uses default project_name when not specified."""
        gen = ProcessDocGenerator()
        output = tmp_path / "default_name.docx"
        processes = sample_processes["processes"][:1]

        # project_name has default value "Проект"
        result = gen.generate(processes, output)
        assert result == output
        assert output.exists()


# -------------------------------------------------------------------
# RequirementsDocGenerator — Word
# -------------------------------------------------------------------


class TestRequirementsDocGeneratorWord:
    """Tests for RequirementsDocGenerator.generate_word."""

    @pytest.fixture
    def requirements_data(self):
        """Sample requirements list for testing."""
        return [
            {
                "id": "FR-001",
                "type": "FR",
                "module": "Продажи",
                "description": "Регистрация заказа клиента",
                "priority": "Must",
                "source": "proc_001",
                "effort": "2 чел/дн",
            },
            {
                "id": "FR-002",
                "type": "FR",
                "module": "Склад",
                "description": "Автоматическая проверка остатков",
                "priority": "Should",
                "source": "proc_002",
                "effort": "3 чел/дн",
            },
            {
                "id": "NFR-001",
                "type": "NFR",
                "module": "Общее",
                "description": "Время отклика не более 3 секунд",
                "priority": "Could",
                "source": "Нефункциональные",
                "effort": "5 чел/дн",
            },
        ]

    def test_generate_word_creates_file(self, tmp_path, requirements_data):
        """generate_word creates a .docx file."""
        gen = RequirementsDocGenerator(author="Тест")
        output = tmp_path / "requirements.docx"

        result = gen.generate_word(requirements_data, "Тест", output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_word_empty_requirements(self, tmp_path):
        """generate_word with empty requirements creates a document."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "empty_reqs.docx"

        result = gen.generate_word([], "Пустой проект", output)
        assert result == output
        assert output.exists()

    def test_generate_word_returns_path(self, tmp_path, requirements_data):
        """generate_word returns the output path."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "result.docx"

        result = gen.generate_word(requirements_data, "Проект", output)
        assert isinstance(result, Path)
        assert result == output


# -------------------------------------------------------------------
# RequirementsDocGenerator — Excel
# -------------------------------------------------------------------


class TestRequirementsDocGeneratorExcel:
    """Tests for RequirementsDocGenerator.generate_excel."""

    @pytest.fixture
    def requirements_data(self):
        """Sample requirements list for testing."""
        return [
            {
                "id": "FR-001",
                "type": "FR",
                "module": "Продажи",
                "description": "Регистрация заказа",
                "priority": "Must",
                "source": "proc_001",
                "effort": "2 чел/дн",
            },
            {
                "id": "NFR-001",
                "type": "NFR",
                "module": "Общее",
                "description": "Производительность",
                "priority": "Should",
                "source": "Нефункциональные",
                "effort": "3 чел/дн",
            },
        ]

    def test_generate_excel_creates_file(self, tmp_path, requirements_data):
        """generate_excel creates an .xlsx file."""
        gen = RequirementsDocGenerator(author="Тест")
        output = tmp_path / "requirements.xlsx"

        result = gen.generate_excel(requirements_data, "Тест", output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_excel_empty_requirements(self, tmp_path):
        """generate_excel with empty requirements creates a file."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "empty_reqs.xlsx"

        result = gen.generate_excel([], "Пустой", output)
        assert result == output
        assert output.exists()

    def test_generate_excel_returns_path(self, tmp_path, requirements_data):
        """generate_excel returns the output path."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "result.xlsx"

        result = gen.generate_excel(requirements_data, "Проект", output)
        assert isinstance(result, Path)
        assert result == output

    def test_generate_dispatches_by_extension(self, tmp_path, requirements_data):
        """generate dispatches to generate_excel for .xlsx extension."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "auto.xlsx"

        result = gen.generate(requirements_data, output, project_name="Авто")
        assert result == output
        assert output.exists()

    def test_generate_dispatches_to_word(self, tmp_path, requirements_data):
        """generate dispatches to generate_word for .docx extension."""
        gen = RequirementsDocGenerator()
        output = tmp_path / "auto.docx"

        result = gen.generate(requirements_data, output, project_name="Авто")
        assert result == output
        assert output.exists()


# -------------------------------------------------------------------
# GapReportGenerator — Excel
# -------------------------------------------------------------------


class TestGapReportGeneratorExcel:
    """Tests for GapReportGenerator.generate_excel."""

    def test_generate_excel_creates_file(self, tmp_path, sample_gaps):
        """generate_excel creates an .xlsx file."""
        gen = GapReportGenerator(author="Тест")
        output = tmp_path / "gap_analysis.xlsx"
        gaps = sample_gaps["gaps"]
        erp_config = sample_gaps.get("erp_config", "1С:ERP 2.5")

        result = gen.generate_excel(gaps, "Тест", erp_config, output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_excel_empty_gaps(self, tmp_path):
        """generate_excel with empty gaps list creates a file."""
        gen = GapReportGenerator()
        output = tmp_path / "empty_gap.xlsx"

        result = gen.generate_excel([], "Пустой", "1С:ERP", output)
        assert result == output
        assert output.exists()

    def test_generate_excel_returns_path(self, tmp_path, sample_gaps):
        """generate_excel returns the output path."""
        gen = GapReportGenerator()
        output = tmp_path / "result.xlsx"
        gaps = sample_gaps["gaps"]
        erp_config = sample_gaps.get("erp_config", "1С:ERP 2.5")

        result = gen.generate_excel(gaps, "Проект", erp_config, output)
        assert isinstance(result, Path)
        assert result == output

    def test_generate_excel_creates_parent_dirs(self, tmp_path, sample_gaps):
        """generate_excel creates parent directories if needed."""
        gen = GapReportGenerator()
        output = tmp_path / "subdir" / "gap.xlsx"
        gaps = sample_gaps["gaps"][:2]

        result = gen.generate_excel(gaps, "Тест", "1С:ERP 2.5", output)
        assert result == output
        assert output.exists()


# -------------------------------------------------------------------
# GapReportGenerator — Word
# -------------------------------------------------------------------


class TestGapReportGeneratorWord:
    """Tests for GapReportGenerator.generate_word."""

    def test_generate_word_creates_file(self, tmp_path, sample_gaps):
        """generate_word creates a .docx file."""
        gen = GapReportGenerator(author="Тест", company="Компания")
        output = tmp_path / "gap_analysis.docx"
        gaps = sample_gaps["gaps"]
        erp_config = sample_gaps.get("erp_config", "1С:ERP 2.5")

        result = gen.generate_word(gaps, "Тест", erp_config, output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_generate_word_empty_gaps(self, tmp_path):
        """generate_word with empty gaps list creates a document."""
        gen = GapReportGenerator()
        output = tmp_path / "empty_gap.docx"

        result = gen.generate_word([], "Пустой", "1С:ERP", output)
        assert result == output
        assert output.exists()

    def test_generate_word_returns_path(self, tmp_path, sample_gaps):
        """generate_word returns the output path."""
        gen = GapReportGenerator()
        output = tmp_path / "result.docx"
        gaps = sample_gaps["gaps"]

        result = gen.generate_word(gaps, "Проект", "1С:ERP 2.5", output)
        assert isinstance(result, Path)
        assert result == output

    def test_generate_dispatches_by_extension_docx(self, tmp_path, sample_gaps):
        """generate dispatches to generate_word for .docx extension."""
        gen = GapReportGenerator()
        output = tmp_path / "auto.docx"
        gaps = sample_gaps["gaps"][:2]

        result = gen.generate(gaps, output, project_name="Авто", erp_config="1С:ERP")
        assert result == output
        assert output.exists()

    def test_generate_dispatches_by_extension_xlsx(self, tmp_path, sample_gaps):
        """generate dispatches to generate_excel for .xlsx extension."""
        gen = GapReportGenerator()
        output = tmp_path / "auto.xlsx"
        gaps = sample_gaps["gaps"][:2]

        result = gen.generate(gaps, output, project_name="Авто", erp_config="1С:ERP")
        assert result == output
        assert output.exists()


# -------------------------------------------------------------------
# DocGenerator base class init
# -------------------------------------------------------------------


class TestDocGeneratorInit:
    """Tests for DocGenerator constructor defaults."""

    def test_default_author(self):
        """ProcessDocGenerator with no args uses default author."""
        gen = ProcessDocGenerator()
        assert gen.author == "Survey Automation"
        assert gen.company == ""

    def test_custom_author_and_company(self):
        """DocGenerator subclasses accept author and company."""
        gen = RequirementsDocGenerator(author="Иван", company="ООО Рога")
        assert gen.author == "Иван"
        assert gen.company == "ООО Рога"

    def test_gap_generator_init(self):
        """GapReportGenerator accepts author and company."""
        gen = GapReportGenerator(author="Аналитик", company="ООО Тест")
        assert gen.author == "Аналитик"
        assert gen.company == "ООО Тест"

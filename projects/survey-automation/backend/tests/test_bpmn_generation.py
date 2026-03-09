"""Тесты: генерация BPMN XML и компоновка диаграмм."""
import pytest

from app.bpmn.json_to_bpmn import BpmnConverter
from app.bpmn.layout import BpmnLayout


def _process_to_bpmn_json(process: dict) -> dict:
    """Convert process dict from sample data to minimal BPMN JSON for testing."""
    elements = []
    flows = []

    # Start event
    elements.append({"id": "start_1", "type": "startEvent", "name": "Начало"})

    prev_id = "start_1"
    for i, step in enumerate(process.get("steps", [])):
        task_id = f"task_{i + 1}"
        elements.append({
            "id": task_id,
            "type": "task",
            "name": step.get("name", f"Шаг {i + 1}"),
        })
        flows.append({"id": f"flow_{i}", "source": prev_id, "target": task_id})
        prev_id = task_id

    # End event
    elements.append({"id": "end_1", "type": "endEvent", "name": "Конец"})
    flows.append({"id": "flow_end", "source": prev_id, "target": "end_1"})

    return {
        "process_id": process.get("id", "test_proc"),
        "process_name": process.get("name", "Тест"),
        "elements": elements,
        "flows": flows,
    }


# -------------------------------------------------------------------
# BpmnLayout
# -------------------------------------------------------------------


class TestBpmnLayout:
    """Tests for BpmnLayout.calculate_layout."""

    def test_layout_compute(self, sample_processes):
        """calculate_layout returns positions for all elements."""
        layout = BpmnLayout()
        process = sample_processes["processes"][0]
        bpmn_json = _process_to_bpmn_json(process)

        result = layout.calculate_layout(bpmn_json)
        assert result is not None
        assert "elements" in result
        assert "flows" in result
        assert len(result["elements"]) > 0

    def test_layout_all_elements_have_position(self, sample_processes):
        """Each element has x, y, width, height in the layout."""
        layout = BpmnLayout()
        process = sample_processes["processes"][0]
        bpmn_json = _process_to_bpmn_json(process)

        result = layout.calculate_layout(bpmn_json)
        for elem_id, pos in result["elements"].items():
            assert "x" in pos, f"Element {elem_id} missing 'x'"
            assert "y" in pos, f"Element {elem_id} missing 'y'"
            assert "width" in pos, f"Element {elem_id} missing 'width'"
            assert "height" in pos, f"Element {elem_id} missing 'height'"

    def test_layout_empty_elements(self):
        """calculate_layout with no elements returns empty layout."""
        layout = BpmnLayout()
        bpmn_json = {
            "process_id": "empty",
            "process_name": "Пустой",
            "elements": [],
            "flows": [],
        }
        result = layout.calculate_layout(bpmn_json)
        assert result["elements"] == {}
        assert result["flows"] == {}

    def test_layout_invalid_input(self):
        """calculate_layout with non-dict input raises ProcessingError."""
        from app.exceptions import ProcessingError

        layout = BpmnLayout()
        with pytest.raises(ProcessingError):
            layout.calculate_layout("not a dict")

    def test_layout_flows_have_waypoints(self, sample_processes):
        """Each flow in layout has waypoint data."""
        layout = BpmnLayout()
        process = sample_processes["processes"][0]
        bpmn_json = _process_to_bpmn_json(process)

        result = layout.calculate_layout(bpmn_json)
        for flow_id, waypoints in result["flows"].items():
            assert isinstance(waypoints, list)
            assert len(waypoints) >= 2
            for wp in waypoints:
                assert "x" in wp
                assert "y" in wp


# -------------------------------------------------------------------
# BpmnConverter
# -------------------------------------------------------------------


class TestBpmnConverter:
    """Tests for BpmnConverter.convert."""

    def test_bpmn_convert(self, sample_processes):
        """convert produces valid BPMN XML with expected tags."""
        converter = BpmnConverter()
        process = sample_processes["processes"][0]
        bpmn_json = _process_to_bpmn_json(process)

        xml = converter.convert(bpmn_json)
        assert xml is not None
        assert isinstance(xml, str)
        assert "definitions" in xml
        assert "process" in xml.lower()
        assert "startEvent" in xml
        assert "endEvent" in xml
        assert "sequenceFlow" in xml

    def test_bpmn_convert_multiple_processes(self, sample_processes):
        """convert works for each process in the sample data."""
        converter = BpmnConverter()
        for process in sample_processes["processes"]:
            bpmn_json = _process_to_bpmn_json(process)
            xml = converter.convert(bpmn_json)
            assert xml is not None
            assert "definitions" in xml

    def test_bpmn_convert_with_layout(self, sample_processes):
        """convert with pre-computed layout includes DI information."""
        converter = BpmnConverter()
        layout_engine = BpmnLayout()
        process = sample_processes["processes"][0]
        bpmn_json = _process_to_bpmn_json(process)

        layout = layout_engine.calculate_layout(bpmn_json)
        bpmn_json["layout"] = layout

        xml = converter.convert(bpmn_json)
        assert xml is not None
        assert "BPMNDiagram" in xml
        assert "BPMNShape" in xml
        assert "BPMNEdge" in xml

    def test_bpmn_convert_minimal(self):
        """convert with minimal valid input (just process_id) works."""
        converter = BpmnConverter()
        bpmn_json = {
            "process_id": "minimal_proc",
            "process_name": "Минимальный",
            "elements": [
                {"id": "s1", "type": "startEvent", "name": "Старт"},
                {"id": "e1", "type": "endEvent", "name": "Конец"},
            ],
            "flows": [
                {"id": "f1", "source": "s1", "target": "e1"},
            ],
        }
        xml = converter.convert(bpmn_json)
        assert "definitions" in xml
        assert "minimal_proc" in xml

    def test_bpmn_convert_missing_process_id(self):
        """convert without process_id raises ProcessingError."""
        from app.exceptions import ProcessingError

        converter = BpmnConverter()
        with pytest.raises(ProcessingError):
            converter.convert({"elements": [], "flows": []})

    def test_bpmn_convert_invalid_input_type(self):
        """convert with non-dict input raises ProcessingError."""
        from app.exceptions import ProcessingError

        converter = BpmnConverter()
        with pytest.raises(ProcessingError):
            converter.convert("not a dict")

    def test_bpmn_convert_with_gateways(self):
        """convert handles gateway elements correctly."""
        converter = BpmnConverter()
        bpmn_json = {
            "process_id": "gateway_proc",
            "process_name": "С шлюзами",
            "elements": [
                {"id": "s1", "type": "startEvent", "name": "Старт"},
                {"id": "gw1", "type": "exclusiveGateway", "name": "Условие"},
                {"id": "t1", "type": "task", "name": "Ветка Да"},
                {"id": "t2", "type": "task", "name": "Ветка Нет"},
                {"id": "gw2", "type": "exclusiveGateway", "name": "Слияние"},
                {"id": "e1", "type": "endEvent", "name": "Конец"},
            ],
            "flows": [
                {"id": "f1", "source": "s1", "target": "gw1"},
                {"id": "f2", "source": "gw1", "target": "t1", "name": "Да"},
                {"id": "f3", "source": "gw1", "target": "t2", "name": "Нет"},
                {"id": "f4", "source": "t1", "target": "gw2"},
                {"id": "f5", "source": "t2", "target": "gw2"},
                {"id": "f6", "source": "gw2", "target": "e1"},
            ],
        }
        xml = converter.convert(bpmn_json)
        assert "exclusiveGateway" in xml
        assert "gateway_proc" in xml


# -------------------------------------------------------------------
# _visual_text_width — расчёт визуальной ширины текста
# -------------------------------------------------------------------


class TestVisualTextWidth:
    """Тесты для _visual_text_width (учёт emoji и пробелов)."""

    def test_pure_cyrillic(self):
        """Кириллица: 1 символ = 1.0 visual unit."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width("Привет", char_coeff=1.0)
        assert w == 6.0

    def test_emoji_counted_double(self):
        """Emoji: 1 символ = 2.0 visual units."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width("\U0001F4E4", char_coeff=1.0)
        assert w == 2.0

    def test_space_half(self):
        """Пробел: 0.5 visual units."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width(" ", char_coeff=1.0)
        assert w == 0.5

    def test_mixed_emoji_and_cyrillic(self):
        """Смешанный текст: emoji(2) + space(0.5) + 4 буквы(4)."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width("\U0001F4E4 Тест", char_coeff=1.0)
        assert w == 6.5

    def test_gear_emoji(self):
        """⚙ (U+2699) считается как emoji (Symbol Other)."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width("\u2699", char_coeff=1.0)
        assert w == 2.0

    def test_badge_wider_than_naive(self):
        """_badge_w даёт ширину больше наивного len() * coeff."""
        from app.visio.direct_vsdx import DirectVsdxGenerator
        gen = DirectVsdxGenerator()
        text = "\U0001F4E4 Финансовое подтверждение"
        badge_w = gen._badge_w(text)
        naive_w = len(text) * 0.085
        assert badge_w > naive_w

    def test_coefficient_applied(self):
        """Коэффициент применяется к визуальным единицам."""
        from app.visio.direct_vsdx import _visual_text_width
        w = _visual_text_width("АБВ", char_coeff=0.1)
        assert abs(w - 0.3) < 0.001


# -------------------------------------------------------------------
# ProcessToBpmnConverter — нумерация задач и подпроцессы
# -------------------------------------------------------------------


class TestProcessToBpmnConverter:
    """Tests for ProcessToBpmnConverter: numbered tasks, subprocesses, gateways."""

    def test_task_names_numbered(self):
        """Task names include step number and performer."""
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter

        process = {
            "id": "p1", "name": "Test", "trigger": "Start", "result": "End",
            "steps": [
                {"order": 1, "name": "Accept order", "performer": "Manager"},
                {"order": 2, "name": "Check stock", "performer": "Worker"},
            ],
            "decisions": [],
            "participants": [{"role": "Manager"}, {"role": "Worker"}],
        }
        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)

        tasks = [e for e in bpmn["elements"] if "Task" in e.get("type", "") or e.get("type") == "task"]
        assert any("1. Accept order (Manager)" in t["name"] for t in tasks)
        assert any("2. Check stock (Worker)" in t["name"] for t in tasks)

    def test_subprocess_detected(self):
        """Steps with >= 2 sub_steps are marked is_subprocess=True."""
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter

        process = {
            "id": "p1", "name": "Test", "trigger": "Start", "result": "End",
            "steps": [
                {"order": 1, "name": "Simple", "performer": "A"},
                {"order": 2, "name": "Complex", "performer": "A",
                 "sub_steps": ["sub1", "sub2", "sub3"]},
            ],
            "decisions": [],
            "participants": [{"role": "A"}],
        }
        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)

        tasks = {e["name"]: e for e in bpmn["elements"]
                 if "Task" in e.get("type", "") or e.get("type") == "task"}
        simple = [v for k, v in tasks.items() if "Simple" in k]
        complex_ = [v for k, v in tasks.items() if "Complex" in k]
        assert simple and simple[0].get("is_subprocess") is False
        assert complex_ and complex_[0].get("is_subprocess") is True

    def test_gateway_has_condition_label(self):
        """Gateway element includes condition_label field."""
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter

        process = {
            "id": "p1", "name": "Test", "trigger": "Start", "result": "End",
            "steps": [{"order": 1, "name": "Step", "performer": "A"}],
            "decisions": [{
                "after_step": 1,
                "name": "Is ready?",
                "condition": "Full readiness check",
                "yes_branch": "Go", "no_branch": "Wait",
            }],
            "participants": [{"role": "A"}],
        }
        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)

        gateways = [e for e in bpmn["elements"] if "Gateway" in e.get("type", "")]
        split_gw = [g for g in gateways if g.get("name")]
        assert split_gw
        assert split_gw[0].get("condition_label") == "Full readiness check"

    def test_flow_labels_yes_no(self):
        """Flows from gateway have 'Да' and 'Нет' labels."""
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter

        process = {
            "id": "p1", "name": "Test", "trigger": "Start", "result": "End",
            "steps": [{"order": 1, "name": "Step", "performer": "A"}],
            "decisions": [{
                "after_step": 1, "name": "Q?", "condition": "cond",
                "yes_branch": "Y", "no_branch": "N",
            }],
            "participants": [{"role": "A"}],
        }
        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)

        flow_names = [f.get("name", "") for f in bpmn["flows"]]
        assert "Да" in flow_names
        assert "Нет" in flow_names


# -------------------------------------------------------------------
# DirectVsdxGenerator — Visio файл
# -------------------------------------------------------------------


class TestDirectVsdxGenerator:
    """Tests for DirectVsdxGenerator: valid .vsdx output."""

    def test_generate_valid_vsdx(self, tmp_path):
        """Generated .vsdx is a valid ZIP with required entries."""
        import zipfile
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter
        from app.bpmn.layout import BpmnLayout
        from app.visio.direct_vsdx import DirectVsdxGenerator

        process = {
            "id": "p1", "name": "Test Process", "trigger": "Start", "result": "End",
            "steps": [
                {"order": 1, "name": "Step One", "performer": "Manager"},
                {"order": 2, "name": "Step Two", "performer": "Worker",
                 "systems": ["1C:ERP"], "sub_steps": ["a", "b"]},
            ],
            "decisions": [{"after_step": 1, "name": "OK?", "condition": "Check",
                          "yes_branch": "Go", "no_branch": "Stop"}],
            "participants": [{"role": "Manager"}, {"role": "Worker"}],
        }

        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)
        layout = BpmnLayout().calculate_layout(bpmn)
        bpmn["layout"] = layout

        output = tmp_path / "test.vsdx"
        gen = DirectVsdxGenerator()
        gen.generate(bpmn, output, process_data=process)

        assert output.exists()
        assert output.stat().st_size > 1000

        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            assert any("page1.xml" in n for n in names)
            assert any("[Content_Types].xml" in n for n in names)

    def test_colored_lanes_in_vsdx(self, tmp_path):
        """Different lanes get different colors from LANE_PALETTE."""
        import zipfile
        from app.bpmn.process_to_bpmn import ProcessToBpmnConverter
        from app.bpmn.layout import BpmnLayout
        from app.visio.direct_vsdx import DirectVsdxGenerator, LANE_PALETTE

        process = {
            "id": "p1", "name": "Test", "trigger": "S", "result": "E",
            "steps": [
                {"order": 1, "name": "A", "performer": "Role1"},
                {"order": 2, "name": "B", "performer": "Role2"},
                {"order": 3, "name": "C", "performer": "Role3"},
            ],
            "decisions": [],
            "participants": [{"role": "Role1"}, {"role": "Role2"}, {"role": "Role3"}],
        }

        converter = ProcessToBpmnConverter()
        bpmn = converter.convert(process)
        layout = BpmnLayout().calculate_layout(bpmn)
        bpmn["layout"] = layout

        output = tmp_path / "lanes.vsdx"
        gen = DirectVsdxGenerator()
        gen.generate(bpmn, output, process_data=process)

        # Read the page XML and verify different lane colors are present
        with zipfile.ZipFile(output) as zf:
            page_xml = zf.read("visio/pages/page1.xml").decode("utf-8")

        # All 3 palette header colors should be in the XML
        for i in range(3):
            header_color = LANE_PALETTE[i][1]
            assert header_color in page_xml, f"Lane palette color {header_color} missing"

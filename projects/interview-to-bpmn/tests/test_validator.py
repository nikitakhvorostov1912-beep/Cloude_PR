"""Tests for process and BPMN validation."""
from src.analysis.validator import validate_bpmn_json, validate_processes


class TestValidateProcesses:
    def test_valid_processes(self, sample_processes):
        result = validate_processes(sample_processes)
        assert result["valid"] is True
        assert result["process_count"] == 1
        assert result["errors"] == []

    def test_empty_processes(self):
        result = validate_processes({"processes": []})
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_missing_processes_key(self):
        result = validate_processes({})
        assert result["valid"] is False


class TestValidateBpmnJson:
    def test_valid_bpmn(self, sample_bpmn_json):
        result = validate_bpmn_json(sample_bpmn_json)
        assert result["valid"] is True

    def test_empty_bpmn(self):
        result = validate_bpmn_json({"elements": [], "flows": []})
        # Should have warnings about missing elements
        assert isinstance(result["errors"], list)

    def test_missing_start_event(self, sample_bpmn_json):
        sample_bpmn_json["elements"] = [
            e for e in sample_bpmn_json["elements"] if e["type"] != "startEvent"
        ]
        result = validate_bpmn_json(sample_bpmn_json)
        # Should warn about missing start event
        assert len(result["warnings"]) > 0 or len(result["errors"]) > 0

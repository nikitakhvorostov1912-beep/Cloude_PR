"""Tests for BPMN JSON to XML conversion."""
from lxml import etree

from src.bpmn.json_to_bpmn import BPMN_NS, XSI_NS, bpmn_json_to_xml


class TestBpmnJsonToXml:
    def test_basic_conversion(self, sample_bpmn_json):
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        assert xml_string is not None
        assert len(xml_string) > 0

    def test_valid_xml(self, sample_bpmn_json):
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        assert root.tag == f"{{{BPMN_NS}}}definitions"

    def test_contains_process(self, sample_bpmn_json):
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        processes = root.findall(f"{{{BPMN_NS}}}process")
        assert len(processes) == 1
        assert processes[0].get("id") == "Process_1"

    def test_contains_elements(self, sample_bpmn_json):
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        process = root.find(f"{{{BPMN_NS}}}process")

        start_events = process.findall(f"{{{BPMN_NS}}}startEvent")
        assert len(start_events) == 1

        user_tasks = process.findall(f"{{{BPMN_NS}}}userTask")
        assert len(user_tasks) == 2

        gateways = process.findall(f"{{{BPMN_NS}}}exclusiveGateway")
        assert len(gateways) == 1

        end_events = process.findall(f"{{{BPMN_NS}}}endEvent")
        assert len(end_events) == 1

    def test_contains_flows(self, sample_bpmn_json):
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        process = root.find(f"{{{BPMN_NS}}}process")

        flows = process.findall(f"{{{BPMN_NS}}}sequenceFlow")
        assert len(flows) == 5

    def test_condition_expression_uses_xsi_type(self, sample_bpmn_json):
        """BUG-005 regression: conditionExpression must use xsi:type."""
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        process = root.find(f"{{{BPMN_NS}}}process")

        conditions = process.findall(f".//{{{BPMN_NS}}}conditionExpression")
        assert len(conditions) >= 1

        cond = conditions[0]
        xsi_type = cond.get(f"{{{XSI_NS}}}type")
        assert xsi_type == "bpmn:tFormalExpression"

    def test_contains_diagram(self, sample_bpmn_json):
        from src.bpmn.json_to_bpmn import BPMNDI_NS
        xml_string = bpmn_json_to_xml(sample_bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))

        diagrams = root.findall(f"{{{BPMNDI_NS}}}BPMNDiagram")
        assert len(diagrams) == 1

    def test_empty_elements(self):
        bpmn_json = {
            "process_id": "P1",
            "process_name": "Empty",
            "elements": [],
            "flows": [],
            "pools": [],
        }
        xml_string = bpmn_json_to_xml(bpmn_json)
        root = etree.fromstring(xml_string.encode("utf-8"))
        assert root is not None

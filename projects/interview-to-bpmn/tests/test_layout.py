"""Tests for BPMN auto layout."""
from src.bpmn.layout import auto_layout


class TestAutoLayout:
    def test_basic_layout(self, sample_bpmn_json):
        positions = auto_layout(sample_bpmn_json)
        assert len(positions) == 5
        for eid in ["start_1", "task_1", "gw_1", "task_2", "end_1"]:
            assert eid in positions
            pos = positions[eid]
            assert "x" in pos
            assert "y" in pos
            assert "width" in pos
            assert "height" in pos

    def test_left_to_right_order(self, sample_bpmn_json):
        positions = auto_layout(sample_bpmn_json)
        # Start should be leftmost, end rightmost
        assert positions["start_1"]["x"] < positions["task_1"]["x"]
        assert positions["task_1"]["x"] < positions["gw_1"]["x"]

    def test_empty_elements(self):
        result = auto_layout({"elements": [], "flows": [], "pools": []})
        assert result == {}

    def test_no_overlap_in_lanes(self):
        """BUG-007 regression: elements in same lane must not overlap."""
        bpmn_json = {
            "elements": [
                {"id": "t1", "type": "task", "name": "Task 1"},
                {"id": "t2", "type": "task", "name": "Task 2"},
                {"id": "t3", "type": "task", "name": "Task 3"},
            ],
            "flows": [],
            "pools": [
                {
                    "id": "pool_1",
                    "name": "Pool",
                    "lanes": [
                        {"id": "lane_1", "name": "Lane 1", "elements": ["t1", "t2", "t3"]},
                    ],
                }
            ],
        }
        positions = auto_layout(bpmn_json)

        # Check that no two elements in the same lane overlap vertically
        elems = [positions["t1"], positions["t2"], positions["t3"]]
        for i in range(len(elems)):
            for j in range(i + 1, len(elems)):
                a, b = elems[i], elems[j]
                if a["x"] == b["x"]:
                    # Same column: must not overlap vertically
                    a_bottom = a["y"] + a["height"]
                    b_bottom = b["y"] + b["height"]
                    assert a_bottom <= b["y"] or b_bottom <= a["y"], (
                        f"Elements overlap: {a} and {b}"
                    )

"""Tests for ML label generators: high/low multi-threshold + topbot."""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.label_generators import (
    generate_highlow_labels, generate_topbot_labels,
    generate_topbot_extrema, Extremum,
)


class TestHighLowLabels:

    def test_returns_all_keys(self):
        c = np.linspace(100, 110, 100)
        h = c + 1
        l = c - 1
        labels = generate_highlow_labels(c, h, l, horizon=10)
        assert "high_1_0" in labels
        assert "low_1_0" in labels
        assert "direction" in labels
        assert "magnitude" in labels

    def test_correct_length(self):
        c = np.linspace(100, 110, 50)
        labels = generate_highlow_labels(c, c + 1, c - 1, horizon=10)
        for v in labels.values():
            assert len(v) == 50

    def test_last_bars_false(self):
        """Last `horizon` bars should be False (no future data)."""
        c = np.linspace(100, 110, 50)
        labels = generate_highlow_labels(c, c + 1, c - 1, horizon=10)
        assert not labels["high_1_0"][-1]  # no future data
        assert not labels["high_1_0"][-5]

    def test_big_rise_detected(self):
        """Price jumps 5% → high_2_0 and high_3_0 should be True."""
        c = np.full(100, 100.0)
        c[50:] = 105.0  # 5% jump at bar 50
        h = c + 0.5
        l = c - 0.5
        labels = generate_highlow_labels(c, h, l, horizon=20,
                                         thresholds=[1.0, 2.0, 3.0, 5.0])
        # Bar 40: future max high = 105.5, close = 100 → 5.5% rise
        assert labels["high_2_0"][40]
        assert labels["high_3_0"][40]

    def test_big_drop_detected(self):
        """Price drops 5% → low thresholds True."""
        c = np.full(100, 100.0)
        c[50:] = 95.0
        h = c + 0.5
        l = c - 0.5
        labels = generate_highlow_labels(c, h, l, horizon=20,
                                         thresholds=[1.0, 2.0, 3.0])
        assert labels["low_2_0"][40]
        assert labels["low_3_0"][40]

    def test_flat_no_labels(self):
        """Flat price → no thresholds exceeded."""
        c = np.full(100, 100.0)
        h = c + 0.01
        l = c - 0.01
        labels = generate_highlow_labels(c, h, l, horizon=10,
                                         thresholds=[0.5, 1.0])
        assert not labels["high_0_5"][0]
        assert not labels["low_0_5"][0]

    def test_direction_label(self):
        """Direction = +1 when upside > downside."""
        c = np.full(100, 100.0)
        c[50:] = 105.0
        h = c + 0.5
        l = c - 0.5
        labels = generate_highlow_labels(c, h, l, horizon=20)
        assert labels["direction"][40] == 1

    def test_magnitude_positive(self):
        """Magnitude = max of up and down move."""
        c = np.full(100, 100.0)
        c[50:] = 103.0
        h = c + 0.5
        l = c - 0.5
        labels = generate_highlow_labels(c, h, l, horizon=20)
        assert labels["magnitude"][40] > 2.0

    def test_custom_thresholds(self):
        c = np.linspace(100, 120, 100)
        labels = generate_highlow_labels(c, c + 1, c - 1, horizon=10,
                                         thresholds=[0.1, 0.2])
        assert "high_0_1" in labels
        assert "high_0_2" in labels
        assert "high_1_0" not in labels

    def test_short_array(self):
        c = np.array([100.0, 101.0, 99.0])
        labels = generate_highlow_labels(c, c + 1, c - 1, horizon=2)
        assert len(labels["direction"]) == 3


class TestTopBotLabels:

    def test_detects_top(self):
        """Clear peak → top label True."""
        c = np.concatenate([
            np.linspace(100, 130, 50),  # +30% rise
            np.linspace(130, 100, 50),  # -23% fall
        ])
        tops, bots = generate_topbot_labels(c, level=0.10, tolerance=0.01)
        # Peak around index 49-50, tolerance zone should catch it
        assert tops.any(), f"No tops detected, max={c.max()}"

    def test_detects_bot(self):
        """Clear trough → bot label True."""
        c = np.concatenate([
            np.linspace(100, 70, 50),   # -30% fall
            np.linspace(70, 100, 50),   # +43% rise
        ])
        tops, bots = generate_topbot_labels(c, level=0.10, tolerance=0.01)
        assert bots.any(), f"No bots detected, min={c.min()}"

    def test_flat_no_extrema(self):
        """Flat price → no tops or bots."""
        c = np.full(50, 100.0)
        tops, bots = generate_topbot_labels(c, level=0.02)
        assert not tops.any()
        assert not bots.any()

    def test_correct_length(self):
        c = np.linspace(100, 120, 80)
        tops, bots = generate_topbot_labels(c, level=0.02)
        assert len(tops) == 80
        assert len(bots) == 80

    def test_tolerance_widens_zone(self):
        """Higher tolerance → more bars labeled."""
        c = np.concatenate([
            np.linspace(100, 115, 30),
            np.linspace(115, 95, 30),
            np.linspace(95, 110, 30),
        ])
        tops_tight, _ = generate_topbot_labels(c, level=0.05, tolerance=0.001)
        tops_wide, _ = generate_topbot_labels(c, level=0.05, tolerance=0.02)
        assert tops_wide.sum() >= tops_tight.sum()

    def test_extrema_list(self):
        c = np.concatenate([
            np.linspace(100, 130, 40),
            np.linspace(130, 85, 40),
            np.linspace(85, 115, 40),
        ])
        extrema = generate_topbot_extrema(c, level=0.10)
        assert len(extrema) >= 1
        types = [e.type for e in extrema]
        assert "top" in types or "bot" in types

    def test_extremum_dataclass(self):
        c = np.concatenate([
            np.linspace(100, 120, 30),
            np.linspace(120, 90, 30),
        ])
        extrema = generate_topbot_extrema(c, level=0.05)
        if extrema:
            e = extrema[0]
            assert isinstance(e, Extremum)
            assert e.price > 0
            assert e.type in ("top", "bot")

    def test_short_array(self):
        c = np.array([100.0, 101.0])
        tops, bots = generate_topbot_labels(c, level=0.01)
        assert len(tops) == 2

"""Tests for perception module: YoloInfer and VOC→YOLO conversion."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from perception.yolo_infer import Detection, YoloInfer
from scripts.convert_voc_to_yolo import CLASS_NAMES, convert_xml_to_yolo, _load_class_map


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------


class TestDetection:
    def _make_det(self, x1=10, y1=20, x2=110, y2=220):
        return Detection(
            class_id=0,
            class_name="test",
            confidence=0.9,
            x1=x1, y1=y1, x2=x2, y2=y2,
        )

    def test_bbox(self):
        d = self._make_det()
        assert d.bbox == (10, 20, 110, 220)

    def test_center(self):
        d = self._make_det()
        assert d.center == (60, 120)

    def test_area(self):
        d = self._make_det()
        assert d.area == 100 * 200


# ---------------------------------------------------------------------------
# YoloInfer tests (no weights — structural tests only)
# ---------------------------------------------------------------------------


class TestYoloInfer:
    def test_init(self):
        yolo = YoloInfer(device="cpu", use_fp16=False)
        assert yolo.model_names == []

    def test_predict_without_model_raises(self):
        yolo = YoloInfer(device="cpu", use_fp16=False)
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="not loaded"):
            yolo.predict("nonexistent", dummy)

    def test_class_names_constant(self):
        assert len(CLASS_NAMES) == 48


# ---------------------------------------------------------------------------
# VOC → YOLO conversion tests
# ---------------------------------------------------------------------------


class TestVocToYolo:
    def test_load_class_map(self):
        data_dir = Path(r"D:\Project\lol_yolo\data")
        if not data_dir.exists():
            pytest.skip("Data directory not available")
        mapping = _load_class_map(data_dir)
        assert len(mapping) == 48
        assert "小地图" in mapping
        assert mapping["小地图"] == 29

    def test_convert_xml_sample(self):
        data_dir = Path(r"D:\Project\lol_yolo\data")
        if not data_dir.exists():
            pytest.skip("Data directory not available")
        xml_files = list((data_dir / "label_xml").glob("*.xml"))
        if not xml_files:
            pytest.skip("No XML files found")

        mapping = _load_class_map(data_dir)
        lines = convert_xml_to_yolo(xml_files[0], 1920, 1080, mapping)
        assert len(lines) > 0
        for line in lines:
            parts = line.split()
            assert len(parts) == 5  # class_id cx cy w h
            cls_id = int(parts[0])
            assert 0 <= cls_id < 48
            for val in parts[1:]:
                v = float(val)
                assert 0.0 <= v <= 1.0

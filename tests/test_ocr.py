"""Tests for OCR engine (PaddleOCR 2.x)."""

import numpy as np
import pytest

from perception.ocr_engine import OcrEngine, OcrResult


class TestOcrResult:
    def _make_result(self, bbox=None):
        if bbox is None:
            bbox = [[10, 20], [100, 20], [100, 50], [10, 50]]
        return OcrResult(text="12:34", confidence=0.95, bbox=bbox)

    def test_center_x(self):
        r = self._make_result()
        assert r.center_x == 55

    def test_center_y(self):
        r = self._make_result()
        assert r.center_y == 35


class TestOcrEngine:
    @pytest.fixture(scope="class")
    def engine(self):
        return OcrEngine(lang="ch", use_gpu=True)

    def test_init(self, engine):
        assert engine is not None

    def test_recognize_empty_image(self, engine):
        black = np.zeros((100, 200, 3), dtype=np.uint8)
        results = engine.recognize(black)
        assert isinstance(results, list)

    def test_recognize_number_empty(self, engine):
        black = np.zeros((50, 100, 3), dtype=np.uint8)
        result = engine.recognize_number(black)
        assert result is None

    def test_recognize_time_empty(self, engine):
        black = np.zeros((50, 200, 3), dtype=np.uint8)
        result = engine.recognize_time(black)
        assert result is None

    def test_recognize_kda_empty(self, engine):
        black = np.zeros((50, 200, 3), dtype=np.uint8)
        result = engine.recognize_kda(black)
        assert result is None

    def test_recognize_with_real_image(self, engine):
        """Test OCR on a real game screenshot."""
        from pathlib import Path
        import cv2

        img_path = list(Path(r"D:\Project\lol_yolo\data\images").glob("*.jpg"))
        if not img_path:
            pytest.skip("No test images available")

        img = cv2.imread(str(img_path[0]))
        if img is None:
            pytest.skip("Cannot read test image")

        # Test full image OCR
        results = engine.recognize(img)
        assert isinstance(results, list)
        print(f"  Full image OCR: {len(results)} results")
        for r in results[:5]:
            print(f"    [{r.confidence:.2f}] {r.text}")

        # Test topbar (game time area)
        topbar = img[0:120, 300:1600]
        topbar_results = engine.recognize(topbar)
        print(f"  Topbar OCR: {[r.text for r in topbar_results]}")

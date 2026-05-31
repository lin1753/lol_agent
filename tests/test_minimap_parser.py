"""Tests for MinimapParser."""

import numpy as np
import pytest

from perception.minimap_parser import MinimapDetection, MinimapParser


class TestMinimapDetection:
    def test_create(self):
        d = MinimapDetection(x=100, y=200, team="enemy", radius=5, color_tag="red")
        assert d.x == 100
        assert d.team == "enemy"


class TestMinimapParser:
    @pytest.fixture
    def parser(self):
        return MinimapParser()

    def test_init(self, parser):
        assert parser is not None

    def test_empty_image(self, parser):
        black = np.zeros((300, 300, 3), dtype=np.uint8)
        result = parser.parse(black)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_none_image(self, parser):
        result = parser.parse(None)
        assert result == []

    def test_detect_red_dots(self, parser):
        """Red circles on black background should be detected as enemies."""
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        # Draw red circles (BGR: 0, 0, 255)
        cv2 = pytest.importorskip("cv2")
        cv2.circle(img, (150, 150), 5, (0, 0, 255), -1)
        cv2.circle(img, (50, 50), 4, (0, 0, 255), -1)

        result = parser.parse(img)
        assert len(result) >= 1  # At least one should be detected
        for d in result:
            assert d.team == "enemy"

    def test_detect_blue_dots(self, parser):
        """Green circles on black background should be detected as allies."""
        cv2 = pytest.importorskip("cv2")
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        cv2.circle(img, (100, 100), 5, (0, 200, 0), -1)   # bright green
        cv2.circle(img, (200, 200), 4, (0, 200, 0), -1)    # bright green

        result = parser.parse(img)
        assert len(result) >= 1
        for d in result:
            assert d.team == "ally"

    def test_annotate(self, parser):
        cv2 = pytest.importorskip("cv2")
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        dets = [MinimapDetection(x=150, y=150, team="enemy")]
        vis = parser.annotate(img, dets)
        assert vis.shape == img.shape
        # Should not be all black (annotations drawn)
        assert vis.sum() > 0

    def test_real_minimap(self, parser):
        """Test on a real game minimap crop."""
        cv2 = pytest.importorskip("cv2")
        from pathlib import Path

        img_paths = list(Path(r"D:\Project\lol_yolo\data\images").glob("*.jpg"))
        if not img_paths:
            pytest.skip("No test images")

        img = cv2.imread(str(img_paths[0]))
        if img is None:
            pytest.skip("Cannot read image")

        # Crop minimap area (bottom-left, ~300x300)
        minimap = img[780:1080, 0:300]
        result = parser.parse(minimap)
        assert isinstance(result, list)
        print(f"  Minimap detections: {len(result)} ({sum(1 for d in result if d.team == 'enemy')} enemies, {sum(1 for d in result if d.team == 'ally')} allies)")

"""OCR engine using subprocess isolation to avoid PyTorch/PaddlePaddle CUDA conflicts.

Runs PaddleOCR in a separate Python process. Communication via JSON over stdin/stdout.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass
class OcrResult:
    """A single OCR detection."""
    text: str
    confidence: float
    bbox: list[list[int]]

    @property
    def center_x(self) -> int:
        return sum(p[0] for p in self.bbox) // len(self.bbox)

    @property
    def center_y(self) -> int:
        return sum(p[1] for p in self.bbox) // len(self.bbox)


# Worker script that runs in a clean subprocess (no torch loaded)
_WORKER_SCRIPT = r'''
import json, sys, os, base64
os.environ["FLAGS_use_cuda_managed_memory"] = "false"

# Add nvidia DLL paths
nvidia_base = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
if os.path.isdir(nvidia_base):
    for root, dirs, files in os.walk(nvidia_base):
        if os.path.basename(root) == "bin":
            p = root
            if p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = p + ";" + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(p)
            except OSError:
                pass

import numpy as np
import cv2
from paddleocr import PaddleOCR

def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "ch"
    use_gpu = sys.argv[2] == "1" if len(sys.argv) > 2 else True

    ocr = PaddleOCR(use_angle_cls=False, lang=lang, use_gpu=use_gpu, show_log=False)

    # Signal ready
    print("READY", flush=True)

    # Read commands from stdin line by line
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "EXIT":
            break

        # "OCR_B64 <base64_data>" — preferred (no disk I/O)
        if line.startswith("OCR_B64 "):
            try:
                img_bytes = base64.b64decode(line[8:])
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            except Exception:
                img = None
        # "OCR <image_path>" — legacy fallback
        elif line.startswith("OCR "):
            img = cv2.imread(line[4:])
        else:
            continue

        if img is None:
            print(json.dumps([]), flush=True)
            continue
        results = ocr.ocr(img, cls=False)
        output = []
        if results and results[0]:
            for item in results[0]:
                bbox = [[int(p[0]), int(p[1])] for p in item[0]]
                output.append({
                    "text": item[1][0],
                    "confidence": float(item[1][1]),
                    "bbox": bbox,
                })
        print(json.dumps(output, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
'''


class OcrEngine:
    """OCR engine running in a subprocess to avoid torch/paddle conflicts.

    Args:
        lang: OCR language ('ch' or 'en').
        use_gpu: Use GPU for OCR inference.
    """

    def __init__(self, lang: str = "ch", use_gpu: bool = True) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._process: Optional[subprocess.Popen] = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        """Whether the OCR subprocess is ready for inference."""
        return self._ready

    def start(self) -> bool:
        """Start the OCR subprocess. Returns True if ready."""
        if self._process and self._process.poll() is None:
            return True

        # Write worker script to temp file
        script_path = Path(tempfile.gettempdir()) / "lol_ocr_worker.py"
        script_path.write_text(_WORKER_SCRIPT, encoding="utf-8")

        # Redirect stderr to devnull to prevent blocking
        stderr_log = Path(tempfile.gettempdir()) / "lol_ocr_stderr.log"
        stderr_fh = open(stderr_log, "w")

        self._process = subprocess.Popen(
            [sys.executable, str(script_path), self._lang, "1" if self._use_gpu else "0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            text=True,
            bufsize=1,
        )

        # Wait for READY signal with timeout
        try:
            import select
            import time
            deadline = time.time() + 30  # 30s timeout
            while time.time() < deadline:
                line = self._process.stdout.readline()
                if "READY" in line:
                    self._ready = True
                    return True
                if not line:
                    break
            return False
        except Exception as e:
            print(f"OCR subprocess error: {e}")
            return False

    def stop(self) -> None:
        """Stop the OCR subprocess."""
        if self._process and self._process.poll() is None:
            try:
                self._process.stdin.write("EXIT\n")
                self._process.stdin.flush()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()

    def recognize(self, image: NDArray[np.uint8]) -> List[OcrResult]:
        """Run OCR on an image region."""
        if not self._ready:
            if not self.start():
                return []
        if self._process.poll() is not None:
            self._ready = False
            self.start()

        if image is None or image.size == 0:
            return []
        if not image.flags["C_CONTIGUOUS"]:
            image = np.ascontiguousarray(image)

        # Encode to PNG in memory and send as base64 via stdin
        try:
            ok, buf = cv2.imencode(".png", image)
            if not ok:
                return []
            import base64
            b64 = base64.b64encode(buf.tobytes()).decode("ascii")
            self._process.stdin.write(f"OCR_B64 {b64}\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
            if not line:
                return []
            raw = json.loads(line.strip())
            return [OcrResult(text=r["text"], confidence=r["confidence"], bbox=r["bbox"]) for r in raw]
        except (json.JSONDecodeError, BrokenPipeError, Exception) as e:
            print(f"OCR error: {e}")
            return []

    def recognize_number(self, image: NDArray[np.uint8]) -> Optional[float]:
        for r in self.recognize(image):
            cleaned = r.text.replace(",", "").replace(" ", "")
            try:
                return float(cleaned)
            except ValueError:
                continue
        return None

    def recognize_time(self, image: NDArray[np.uint8]) -> Optional[str]:
        for r in self.recognize(image):
            match = re.search(r"\d{1,2}:\d{2}", r.text)
            if match:
                return match.group()
        return None

    def recognize_kda(self, image: NDArray[np.uint8]) -> Optional[tuple[int, int, int]]:
        for r in self.recognize(image):
            match = re.search(r"(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", r.text)
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return None

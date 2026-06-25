"""TTS Engine — async voice alerts using Edge TTS with deduplication."""

from __future__ import annotations

import asyncio
import os
import queue
import tempfile
import threading
import time
from typing import Optional

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class TtsEngine:
    """Text-to-speech engine with async queue and message deduplication.

    Uses Edge TTS (Microsoft neural network) for high-quality Chinese voice.
    Falls back to pyttsx3 if edge-tts is not available.

    Args:
        voice: Edge TTS voice name (default: zh-CN-YunxiNeural).
        rate: Speech rate adjustment (e.g. "+10%", "-10%").
        volume: Volume level 0.0-1.0 (only for pyttsx3 fallback).
        dedup_seconds: Seconds before the same message can be spoken again.
        min_level: Minimum warning level to speak (default: WARN).
    """

    def __init__(
        self,
        voice: str = "zh-CN-YunxiNeural",
        rate: str = "+10%",
        volume: float = 0.9,
        dedup_seconds: float = 10.0,
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._dedup_seconds = dedup_seconds

        self._queue: queue.Queue[str] = queue.Queue()
        self._dedup_map: dict[str, float] = {}  # message -> last_spoken_time
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Init audio playback
        if HAS_PYGAME and not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                pass

    def start(self) -> None:
        """Start the TTS worker thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the TTS worker thread and clear the queue."""
        self._running = False
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def speak(self, message: str) -> None:
        """Queue a message for speech (non-blocking).

        Args:
            message: Text to speak.
        """
        if not self._running:
            self.start()
        self._queue.put(message)

    def speak_if_new(self, message: str) -> bool:
        """Speak only if this message hasn't been spoken recently.

        Returns True if the message was queued, False if deduplicated.
        """
        now = time.time()
        last_time = self._dedup_map.get(message, 0)
        if now - last_time < self._dedup_seconds:
            return False
        self._dedup_map[message] = now
        self.speak(message)
        return True

    def clear_dedup(self) -> None:
        """Clear the deduplication cache."""
        self._dedup_map.clear()

    @property
    def is_running(self) -> bool:
        return self._running

    def _worker(self) -> None:
        """Background worker that processes the speech queue."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        while self._running:
            try:
                message = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._speak_blocking(message)
            time.sleep(0.2)
        self._loop.close()

    def _speak_blocking(self, message: str) -> None:
        """Speak a single message (blocking)."""
        if HAS_EDGE_TTS:
            self._speak_edge_tts(message)
        else:
            self._speak_pyttsx3(message)

    def _speak_edge_tts(self, message: str) -> None:
        """Speak using Edge TTS."""
        tmp_path = None
        try:
            # Generate audio to temp file
            tmp_path = os.path.join(tempfile.gettempdir(), "lol_tts_output.mp3")
            communicate = edge_tts.Communicate(message, self._voice, rate=self._rate)
            self._loop.run_until_complete(self._edge_tts_generate(communicate, tmp_path))

            # Play audio
            if HAS_PYGAME and os.path.exists(tmp_path):
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    async def _edge_tts_generate(communicate, output_path: str) -> None:
        """Generate Edge TTS audio file."""
        await communicate.save(output_path)

    def _speak_pyttsx3(self, message: str) -> None:
        """Fallback: speak using pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("volume", self._volume)
            engine.say(message)
            engine.runAndWait()
        except Exception as e:
            print(f"pyttsx3 error: {e}")

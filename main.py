"""LOL Agent Assistant — main entry point.

Real-time game understanding loop:
    Screen Capture → ROI → YOLO+OCR → StateParser → TemporalMemory → RuleEngine → Overlay + Voice

V2 pipeline (--v2 flag):
    Screen Capture → ROI → YOLO+OCR → FeatureEngine → FeatureBundle → (Goal/Decision in P2)

Usage:
    python main.py                      # Auto-detect LOL window
    python main.py --monitor 1          # Capture primary monitor
    python main.py --no-overlay         # Disable overlay
    python main.py --no-voice           # Disable TTS
    python main.py --model weights.pt   # YOLO weights path
    python main.py --v2 --model weights.pt  # V2 pipeline
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

import cv2

from capture.roi_manager import ROIManager
from capture.screen_capture import ScreenCapture
from memory.temporal_memory import TemporalMemory
from models.game_state import GameState
from overlay.overlay_ui import OverlayUI
from parser.state_parser import StateParser
from perception.detection_summary import DetectionSummary, summarize_detections, extract_ocr_regions
from perception.minimap_parser import MinimapParser
from perception.ocr_engine import OcrEngine
from perception.yolo_infer import YoloInfer
from reasoning.rule_engine import RuleEngine
from voice.tts_engine import TtsEngine


class LolAgent:
    """Main agent orchestrating all modules.

    Args:
        model_path: Path to YOLO weights (.pt file).
        video_path: Path to video file for testing (overrides screen capture).
        use_gpu: Use GPU for inference.
        enable_overlay: Enable PyQt5 overlay.
        enable_voice: Enable TTS voice alerts.
        monitor: Monitor index or 'auto' for LOL window detection.
        fps_target: Target FPS (frame skipping if faster).
    """

    def __init__(
        self,
        model_path: str | None = None,
        video_path: str | None = None,
        use_gpu: bool = True,
        enable_overlay: bool = True,
        enable_voice: bool = True,
        monitor: int | str = "auto",
        fps_target: float = 5.0,
        v2: bool = False,
        enable_llm: bool = False,
    ) -> None:
        self._use_gpu = use_gpu
        self._enable_overlay = enable_overlay
        self._enable_voice = enable_voice
        self._fps_target = fps_target
        self._running = False
        self._video_path = video_path
        self._v2 = v2

        # Initialize modules
        print("Initializing LOL Agent...")

        # Screen capture (live or video file)
        self._video_cap = None
        if video_path:
            self._video_cap = cv2.VideoCapture(video_path)
            if not self._video_cap.isOpened():
                print(f"  Error: cannot open video {video_path}")
            else:
                w = int(self._video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(self._video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = self._video_cap.get(cv2.CAP_PROP_FPS)
                total = int(self._video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
                print(f"  Video: {video_path} ({w}x{h}, {fps:.1f}fps, {total} frames)")
        else:
            self._capture = ScreenCapture()
            if monitor == "auto":
                if self._capture.set_lol_window():
                    print("  Screen: LOL window detected")
                else:
                    print("  Screen: LOL window not found, using primary monitor")
                    self._capture = ScreenCapture(monitor=1)
            else:
                self._capture = ScreenCapture(monitor=int(monitor))

        # ROI Manager
        self._roi = ROIManager(config_path=Path(__file__).parent / "configs" / "roi_config.json")
        print(f"  ROI: {self._roi.region_names}")

        # Minimap Parser (OpenCV-based, no model needed)
        self._minimap = MinimapParser()
        print("  Minimap: OpenCV color segmentation")

        # YOLO Inference (center viewport only)
        self._yolo = YoloInfer(
            device="0" if use_gpu else "cpu",
            use_fp16=use_gpu,
        )
        if model_path and Path(model_path).exists():
            self._yolo.load_model("main", model_path)
            print(f"  YOLO: loaded {model_path}")
        else:
            print("  YOLO: no weights loaded (run with --model path/to/best.pt)")

        # OCR Engine (subprocess-isolated PaddleOCR)
        self._ocr: OcrEngine | None = None
        try:
            self._ocr = OcrEngine(lang="ch", use_gpu=use_gpu)
            print("  OCR: starting subprocess...", flush=True)
            if self._ocr.start():
                print("  OCR: PaddleOCR subprocess ready", flush=True)
            else:
                print("  OCR: subprocess failed to start, disabled", flush=True)
                self._ocr = None
        except Exception as e:
            print(f"  OCR: exception {type(e).__name__}: {e}", flush=True)
            self._ocr = None

        # State Parser (V1)
        self._state_parser = StateParser()

        # Feature Engine (V2)
        self._feature_engine = None
        self._context_engine = None
        self._goal_engine = None
        self._decision_engine_v2 = None
        if v2:
            from reasoning.feature_engine import FeatureEngine
            from reasoning.context_engine import ContextEngine
            from reasoning.goal_engine import GoalEngine
            from reasoning.decision_engine_v2 import DecisionEngineV2
            self._feature_engine = FeatureEngine()
            self._context_engine = ContextEngine()
            self._goal_engine = GoalEngine()
            self._decision_engine_v2 = DecisionEngineV2()
            print("  V2: FeatureEngine + ContextEngine + GoalEngine + DecisionEngineV2")

        # LLM Engine (V2 + --llm)
        self._llm_engine = None
        if v2 and enable_llm:
            from reasoning.llm_engine import LlmEngine
            self._llm_engine = LlmEngine()
            if not self._llm_engine.start():
                self._llm_engine = None
                print("  LLM: disabled (failed to load)")

        # Temporal Memory
        self._memory = TemporalMemory(window_size=30)

        # Memory V2 (V2 mode)
        self._hero_memory_v2 = None
        self._objective_memory = None
        if v2:
            from memory.hero_memory import HeroMemoryV2
            from memory.objective_memory import ObjectiveMemory
            self._hero_memory_v2 = HeroMemoryV2()
            self._objective_memory = ObjectiveMemory()
            print("  V2: MemoryV2 (HeroMemory + ObjectiveMemory)")

        # Rule Engine
        self._rules = RuleEngine()

        # Overlay
        self._overlay: OverlayUI | None = None
        if enable_overlay:
            try:
                self._overlay = OverlayUI(v2=v2)
                self._overlay.start()
                print(f"  Overlay: started ({'V2' if v2 else 'V1'})")
            except Exception as e:
                print(f"  Overlay: failed ({e})")

        # TTS
        self._tts: TtsEngine | None = None
        if enable_voice:
            try:
                self._tts = TtsEngine()
                self._tts.start()
                print("  TTS: Edge TTS started")
            except Exception as e:
                print(f"  TTS: failed ({e})")

        print(f"LOL Agent ready (target {fps_target} FPS)")
        # Cached OCR results — persist across frames so time doesn't reset
        self._cached_ocr: dict[str, str] = {}

    def run(self) -> None:
        """Main loop — runs until Ctrl+C."""
        self._running = True

        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print("\nShutting down...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)

        frame_count = 0
        frame_index = 0  # Video frame counter for game time calculation
        fps_timer = time.time()
        fps_display = 0.0

        print("Press Ctrl+C to stop.\n")

        while self._running:
            loop_start = time.time()

            try:
                # 1. Capture frame (video or screen)
                if self._video_cap:
                    ret, frame = self._video_cap.read()
                    if not ret:
                        print("Video ended.")
                        break
                else:
                    frame = self._capture.get_frame()

                # 2. Crop ROIs
                rois = self._roi.crop_all(frame)
                minimap = rois.get("minimap")
                center = rois.get("center")
                topbar = rois.get("topbar")
                hud = rois.get("hud")

                # 3. YOLO detection (full frame, 29-class model)
                yolo_dets = []
                if "main" in self._yolo.model_names:
                    yolo_dets = self._yolo.predict("main", frame)

                # 3b. Summarize detections
                det_summary = summarize_detections(yolo_dets, frame)
                hero_dets = det_summary.visible_enemies + det_summary.visible_allies

                # 3c. Minimap detection (OpenCV)
                minimap_dets = []
                if minimap is not None:
                    minimap_dets = self._minimap.parse(minimap)

                # 4. Game time + OCR (optimized)
                ocr_values = dict(self._cached_ocr)

                # Game time: compute from video frame index (no OCR needed)
                if self._video_cap:
                    video_fps = self._video_cap.get(cv2.CAP_PROP_FPS)
                    if video_fps > 0:
                        game_seconds = frame_index / video_fps
                        ocr_values["time"] = f"{int(game_seconds // 60)}:{int(game_seconds % 60):02d}"
                        self._cached_ocr["time"] = ocr_values["time"]
                        frame_index += 1

                # OCR: only gold + kda, every 60 frames (~2s at 30fps)
                if self._ocr and self._ocr._ready and frame_count % 60 == 0:
                    ocr_crops = extract_ocr_regions(frame, det_summary, scale=4)
                    if "game_time" in ocr_crops and not self._video_cap:
                        # Real-time mode: OCR game_time (not video)
                        t = self._ocr.recognize_time(ocr_crops["game_time"])
                        if t:
                            ocr_values["time"] = t
                            self._cached_ocr["time"] = t
                    if "kda" in ocr_crops:
                        kda = self._ocr.recognize_kda(ocr_crops["kda"])
                        if kda:
                            kda_str = f"{kda[0]}/{kda[1]}/{kda[2]}"
                            ocr_values["kda"] = kda_str
                            self._cached_ocr["kda"] = kda_str
                    if "gold" in ocr_crops:
                        g = self._ocr.recognize_number(ocr_crops["gold"])
                        if g is not None and g > 0:
                            ocr_values["gold"] = str(int(g))
                            self._cached_ocr["gold"] = str(int(g))

                # 5. V2 pipeline: FeatureEngine → Context → Goal → Decision
                if self._v2 and self._feature_engine:
                    bundle = self._feature_engine.extract(
                        det_summary, ocr_values, minimap_dets,
                        minimap_shape=minimap.shape[:2] if minimap is not None else (240, 240),
                    )

                    # Parse game time for state
                    game_time = StateParser._parse_time(ocr_values.get("time", ""))

                    # Update Memory V2
                    if self._hero_memory_v2:
                        self._hero_memory_v2.update(minimap_dets, game_time)
                    if self._objective_memory:
                        for obj_name, alive in bundle.objective.model_dump().items():
                            obj_key = obj_name.replace("_alive", "")
                            if alive:
                                self._objective_memory.record_spawn(obj_key)

                    # Build GameStateV2 from features + context
                    from schemas.state import GameStateV2
                    v2_state = GameStateV2(game_time=game_time)
                    v2_state.context = self._context_engine.compute(bundle, v2_state, self._memory)
                    goal = self._goal_engine.determine(v2_state, bundle, self._memory)
                    decisions = self._decision_engine_v2.evaluate(v2_state, goal, bundle, self._memory)

                    # LLM advice (throttled)
                    advice = None
                    if self._llm_engine and self._llm_engine.should_advise(v2_state, goal):
                        advice = self._llm_engine.advise(v2_state, goal, decisions)

                    frame_count += 1
                    elapsed = time.time() - fps_timer
                    if elapsed >= 1.0:
                        fps_display = frame_count / elapsed
                        frame_count = 0
                        fps_timer = time.time()

                    if frame_count % 30 == 0:
                        self._display_v2_status(bundle, hero_dets, minimap_dets, fps_display)
                        if decisions:
                            top = decisions[0]
                            print(f"  Goal: {goal.goal_type} ({goal.confidence:.0%}) → {top.action} ({top.score:.0f}) {top.reason}")
                        if advice:
                            print(f"  LLM: {advice}")

                    if self._overlay:
                        self._overlay.update_state(self._make_v2_overlay_data(
                            bundle, v2_state, goal, decisions, ocr_values, advice, fps=fps_display
                        ))
                        self._overlay.update_decisions(decisions)

                # 5b. V1 pipeline: StateParser → GameState
                else:
                    # 5. Parse state
                    state = self._state_parser.parse_with_minimap(
                        hero_dets, minimap_dets, ocr_values,
                        frame_shape=frame.shape[:2],
                        det_summary=det_summary,
                    )

                    # 6. Update temporal memory
                    self._memory.update(state)

                    # 6b. Enrich state with understanding (phase/context/combat/threat)
                    state = self._state_parser.enrich_state(state, self._memory)

                    # 7. Evaluate rules
                    self._rules.clear_recent()
                    warnings = self._rules.evaluate(state, self._memory)

                    # 8. Output
                    frame_count += 1
                    elapsed = time.time() - fps_timer
                    if elapsed >= 1.0:
                        fps_display = frame_count / elapsed
                        frame_count = 0
                        fps_timer = time.time()

                    # Always show status every 30 frames
                    if frame_count % 30 == 0:
                        self._display_status(state, hero_dets, minimap_dets, fps_display)

                    if warnings:
                        self._display_warnings(warnings)
                        if self._overlay:
                            self._overlay.update_warnings(warnings)
                            self._overlay.update_state(self._make_state_info(state))
                        if self._tts:
                            self._tts.speak_warnings(warnings)
                    elif self._overlay:
                        # Update state even without warnings
                        self._overlay.update_state(self._make_state_info(state))

                # Frame rate limiting
                loop_time = time.time() - loop_start
                target_time = 1.0 / self._fps_target
                if loop_time < target_time:
                    time.sleep(target_time - loop_time)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.5)

        self._shutdown()

    def _display_status(
        self, state: GameState, hero_dets: list, minimap_dets: list, fps: float
    ) -> None:
        """Print periodic status to console."""
        mm_enemies = sum(1 for d in minimap_dets if d.team == "enemy")
        mm_allies = sum(1 for d in minimap_dets if d.team == "ally")
        print(
            f"[{state.current_time:.0f}s | {fps:.1f}FPS] "
            f"YOLO:{len(hero_dets)} mm:{mm_enemies}E/{mm_allies}A "
            f"vis:{state.enemy_count_visible}E/{state.ally_count_visible}A "
            f"phase:{state.game_phase} act:{state.activity} "
            f"combat:{state.combat_state} threat:{state.threat_level}",
            end="",
        )
        if state.danger_lane:
            print(f" danger:{state.danger_lane}", end="")
        print()

    @staticmethod
    def _make_state_info(state: GameState) -> dict:
        """Convert GameState to dict for overlay display."""
        return {
            "game_phase": state.game_phase,
            "activity": state.activity,
            "combat_state": state.combat_state,
            "threat_level": state.threat_level,
            "dragon_spawn_in": state.dragon_spawn_in,
            "baron_spawn_in": state.baron_spawn_in,
            "herald_spawn_in": state.herald_spawn_in,
            "kda": f"{state.kills}/{state.deaths}/{state.assists}",
            "gold": state.current_gold,
            "level": state.player_level,
            "game_time": f"{int(state.current_time // 60)}:{int(state.current_time % 60):02d}" if state.current_time > 0 else "",
        }
        print()

    def _display_v2_status(self, bundle, hero_dets: list, minimap_dets: list, fps: float) -> None:
        """Print V2 pipeline status to console."""
        mm_enemies = sum(1 for d in minimap_dets if d.team == "enemy")
        mm_allies = sum(1 for d in minimap_dets if d.team == "ally")
        h = bundle.hero
        e = bundle.economy
        print(
            f"[V2 | {fps:.1f}FPS] "
            f"YOLO:{len(hero_dets)} mm:{mm_enemies}E/{mm_allies}A "
            f"hero:{h.ally_count}A/{h.enemy_count}E "
            f"KDA:{e.kills}/{e.deaths}/{e.assists} "
            f"gold:{e.player_gold} lv:{e.player_level} "
            f"wave:{bundle.wave.lane_pressure} "
            f"obj:{'D' if bundle.objective.dragon_alive else '-'}"
            f"{'B' if bundle.objective.baron_alive else '-'} "
            f"map:{bundle.map.enemy_top}T/{bundle.map.enemy_mid}M/{bundle.map.enemy_bot}B",
        )

    def _make_v2_overlay_data(self, bundle, v2_state, goal, decisions, ocr_values, advice=None, fps=0.0) -> dict:
        """Build complete V2 overlay data dict."""
        # Compute objective timers from ObjectiveMemory
        dragon_in = -1.0
        baron_in = -1.0
        herald_in = -1.0
        if self._objective_memory:
            timers = self._objective_memory.get_spawn_timers(v2_state.game_time)
            dragon_in = timers.get("dragon_spawn_in", -1.0)
            baron_in = timers.get("baron_spawn_in", -1.0)
            herald_in = timers.get("herald_spawn_in", -1.0)

        game_time_str = ""
        if v2_state.game_time > 0:
            game_time_str = f"{int(v2_state.game_time // 60)}:{int(v2_state.game_time % 60):02d}"

        # OCR status
        ocr_ready = self._ocr is not None and self._ocr._ready if self._ocr else False
        has_kda = bool(ocr_values.get("kda"))
        has_gold = bool(ocr_values.get("gold"))

        return {
            "game_time": game_time_str,
            "fps": fps,
            "ocr_ready": ocr_ready,
            "has_kda": has_kda,
            "has_gold": has_gold,
            "phase": v2_state.phase,
            "activity": v2_state.activity,
            "context": v2_state.context,
            "combat": v2_state.combat,
            "threat": v2_state.threat,
            "kda": ocr_values.get("kda", ""),
            "gold": bundle.economy.player_gold if has_gold else 0,
            "level": bundle.economy.player_level,
            "dragon_spawn_in": dragon_in,
            "baron_spawn_in": baron_in,
            "herald_spawn_in": herald_in,
            "goal_type": goal.goal_type if goal else "",
            "goal_confidence": goal.confidence if goal else 0.0,
            "advice": advice or "",
            "ally_count": bundle.hero.ally_count,
            "enemy_count": bundle.hero.enemy_count,
            "hp_ratio": bundle.hero.hp_ratio,
            "ult_ready": bundle.skill.ult_ready,
            "flash_ready": bundle.skill.flash_ready,
        }

    def _display_warnings(self, warnings: list) -> None:
        """Print warnings to console."""
        level_icons = {"info": "●", "warn": "▲", "danger": "★"}
        for w in warnings:
            icon = level_icons.get(w.level.value, "?")
            print(f"  {icon} {w.message}")

    def _shutdown(self) -> None:
        """Clean shutdown of all modules."""
        print("\nShutting down modules...")
        if self._llm_engine:
            self._llm_engine.stop()
        if self._ocr:
            self._ocr.stop()
        if self._tts:
            self._tts.stop()
        if self._overlay:
            self._overlay.stop()
        if self._video_cap:
            self._video_cap.release()
        else:
            self._capture.close()
        print("LOL Agent stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="LOL Agent Assistant")
    parser.add_argument("--model", type=str, default=None, help="YOLO weights path")
    parser.add_argument("--video", type=str, default=None, help="Video file path for testing")
    parser.add_argument("--no-overlay", action="store_true", help="Disable overlay")
    parser.add_argument("--no-voice", action="store_true", help="Disable TTS")
    parser.add_argument("--monitor", default="auto", help="Monitor index or 'auto'")
    parser.add_argument("--fps", type=float, default=5.0, help="Target FPS")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode")
    parser.add_argument("--v2", action="store_true", help="Use V2 pipeline (FeatureEngine)")
    parser.add_argument("--llm", action="store_true", help="Enable Qwen3-8B LLM advice (requires --v2)")
    args = parser.parse_args()

    agent = LolAgent(
        model_path=args.model,
        video_path=args.video,
        use_gpu=not args.cpu,
        enable_overlay=not args.no_overlay,
        enable_voice=not args.no_voice,
        monitor=args.monitor,
        fps_target=args.fps,
        v2=args.v2,
        enable_llm=args.llm,
    )
    agent.run()


if __name__ == "__main__":
    main()

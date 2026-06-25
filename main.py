"""LOL Agent Assistant — main entry point.

V2 pipeline (goal-driven):
    Screen Capture → ROI → YOLO+OCR → FeatureEngine → ContextEngine → GoalEngine → DecisionEngineV2 → Overlay

Usage:
    python main.py                      # Auto-detect LOL window
    python main.py --monitor 1          # Capture primary monitor
    python main.py --no-overlay         # Disable overlay
    python main.py --no-voice           # Disable TTS
    python main.py --model weights.pt   # YOLO weights path
    python main.py --llm --llm-model /path/to/model  # Enable LLM advice
"""

from __future__ import annotations

import argparse
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

from capture.roi_manager import ROIManager
from capture.screen_capture import ScreenCapture
from config import AgentConfig, setup_logging
from memory.objective_memory import ObjectiveMemory
from memory.fight_memory import FightMemory
from overlay.overlay_ui import OverlayUI
from perception.detection_summary import summarize_detections, extract_ocr_regions
from perception.minimap_parser import MinimapParser
from perception.ocr_engine import OcrEngine
from perception.yolo_infer import YoloInfer
from reasoning.feature_engine import FeatureEngine
from reasoning.context_engine import ContextEngine
from reasoning.goal_engine import GoalEngine
from reasoning.decision_engine_v2 import DecisionEngineV2
from schemas.state import GameStateV2
from utils.parsing import parse_time, parse_kda
from voice.tts_engine import TtsEngine


class LolAgent:
    """Main agent orchestrating the V2 pipeline."""

    def __init__(self, config: AgentConfig, video_path: str | None = None,
                 enable_overlay: bool = True, enable_voice: bool = True,
                 monitor: int | str = "auto", window_title: str | None = None,
                 enable_llm: bool = False, debug: bool = False) -> None:
        self._cfg = config
        self._video_path = video_path
        self._enable_overlay = enable_overlay
        self._enable_voice = enable_voice
        self._monitor = monitor
        self._window_title = window_title
        self._enable_llm = enable_llm
        self._debug = debug
        self._running = False
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeline")
        self._prev_frame = None
        self._cached_yolo_dets = []
        self._logger = setup_logging()
        self._profile = {"yolo": 0.0, "ocr": 0.0, "minimap": 0.0, "engine": 0.0}

        print("Initializing LOL Agent...")

        # Screen capture
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
            if window_title:
                if self._capture.find_window(window_title):
                    print(f"  Screen: found window '{window_title}'")
                else:
                    print(f"  Screen: window '{window_title}' not found, using primary monitor")
                    self._capture = ScreenCapture(monitor=1)
            elif monitor == "auto":
                if self._capture.set_lol_window():
                    print("  Screen: LOL window detected")
                else:
                    print("  Screen: LOL window not found, using primary monitor")
                    self._capture = ScreenCapture(monitor=1)
            else:
                self._capture = ScreenCapture(monitor=int(monitor))

        # ROI
        roi_name = "roi_config.json" if video_path else "roi_config_live.json"
        self._roi = ROIManager(config_path=Path(__file__).parent / "configs" / roi_name)
        print(f"  ROI: {self._roi.region_names}")

        # Minimap
        self._minimap = MinimapParser()
        print("  Minimap: OpenCV color segmentation")

        # YOLO
        use_gpu = config.yolo_model is not None  # simplified; --cpu handled via config
        self._yolo = YoloInfer(device="0" if use_gpu else "cpu", use_fp16=use_gpu)
        if config.yolo_model and Path(config.yolo_model).exists():
            self._yolo.load_model("main", config.yolo_model)
            print(f"  YOLO: loaded {config.yolo_model}")
        else:
            print("  YOLO: no weights loaded (run with --model path/to/best.pt)")

        # OCR
        self._ocr: OcrEngine | None = None
        try:
            self._ocr = OcrEngine(lang=config.ocr_lang, use_gpu=False)
            print("  OCR: starting subprocess...", flush=True)
            if self._ocr.start():
                print("  OCR: PaddleOCR subprocess ready", flush=True)
            else:
                print("  OCR: subprocess failed to start, disabled", flush=True)
                self._ocr = None
        except Exception as e:
            print(f"  OCR: exception {type(e).__name__}: {e}", flush=True)
            self._ocr = None

        # V2 engines
        self._feature_engine = FeatureEngine()
        self._context_engine = ContextEngine()
        self._goal_engine = GoalEngine()
        self._decision_engine_v2 = DecisionEngineV2()
        print("  V2: FeatureEngine + ContextEngine + GoalEngine + DecisionEngineV2")

        # LLM
        self._llm_engine = None
        if enable_llm and config.llm_model:
            from reasoning.llm_engine import LlmEngine
            self._llm_engine = LlmEngine(model_path=config.llm_model)
            if not self._llm_engine.start():
                self._llm_engine = None
                print("  LLM: disabled (failed to load)")
        elif enable_llm:
            print("  LLM: no model path (use --llm-model or set LOL_LLM_MODEL_PATH)")

        # Memory
        self._objective_memory = ObjectiveMemory()
        self._fight_memory = FightMemory()
        self._prev_kda = (0, 0, 0)
        print("  V2: ObjectiveMemory + FightMemory")

        # Overlay
        self._overlay: OverlayUI | None = None
        if enable_overlay:
            try:
                self._overlay = OverlayUI(v2=True)
                self._overlay.start()
                print("  Overlay: started (V2)")
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

        print(f"LOL Agent ready (target {config.fps_target} FPS)")
        self._cached_ocr: dict[str, str] = {}

    def run(self) -> None:
        """Main loop — runs until Ctrl+C."""
        self._running = True

        def signal_handler(sig, frame):
            print("\nShutting down...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)

        frame_count = 0
        frame_index = 0
        fps_timer = time.time()
        fps_display = 0.0
        cfg = self._cfg

        print("Press Ctrl+C to stop.\n")

        while self._running:
            loop_start = time.time()

            try:
                # 1. Capture
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

                # 3. YOLO with frame-diff skip + error degradation
                t0 = time.perf_counter()
                yolo_dets = []
                frame_changed = True
                if self._prev_frame is not None and self._prev_frame.shape == frame.shape:
                    diff = abs(float(frame.astype(float).mean() - self._prev_frame.astype(float).mean()))
                    frame_changed = diff > 3.0
                self._prev_frame = frame.copy()

                try:
                    if "main" in self._yolo.model_names:
                        if frame_changed:
                            yolo_dets = self._yolo.predict("main", frame)
                            self._cached_yolo_dets = yolo_dets
                        else:
                            yolo_dets = self._cached_yolo_dets
                except Exception as e:
                    self._logger.warning("YOLO failed, using cached: %s", e)
                    yolo_dets = self._cached_yolo_dets
                self._profile["yolo"] = time.perf_counter() - t0

                det_summary = summarize_detections(yolo_dets, frame)
                hero_dets = det_summary.visible_enemies + det_summary.visible_allies

                # 4. Submit OCR to thread pool (runs in parallel with minimap + FeatureEngine)
                ocr_future = None
                if self._ocr and self._ocr.is_ready and frame_count % cfg.ocr_interval == 0:
                    ocr_future = self._pool.submit(self._run_ocr, frame, det_summary)

                # 3c. Minimap (parallel with OCR)
                t0 = time.perf_counter()
                minimap_dets = []
                if minimap is not None:
                    minimap_dets = self._minimap.parse(minimap)
                self._profile["minimap"] = time.perf_counter() - t0

                # 4b. Video time (no OCR needed)
                ocr_values = dict(self._cached_ocr)
                if self._video_cap:
                    video_fps = self._video_cap.get(cv2.CAP_PROP_FPS)
                    if video_fps > 0:
                        game_seconds = frame_index / video_fps
                        ocr_values["time"] = f"{int(game_seconds // 60)}:{int(game_seconds % 60):02d}"
                        self._cached_ocr["time"] = ocr_values["time"]
                        frame_index += 1

                # 5. FeatureEngine (runs in parallel with OCR)
                bundle = self._feature_engine.extract(
                    det_summary, ocr_values, minimap_dets,
                    minimap_shape=minimap.shape[:2] if minimap is not None else (240, 240),
                )

                # 4c. Wait for OCR result
                if ocr_future is not None:
                    try:
                        ocr_result = ocr_future.result(timeout=2.0)
                        ocr_values.update(ocr_result)
                        self._cached_ocr.update(ocr_result)
                    except Exception:
                        pass

                # Track KDA changes → death detection
                curr_kda = parse_kda(ocr_values.get("kda", ""))
                if curr_kda[2] > self._prev_kda[2]:  # deaths increased
                    self._fight_memory.record_death(game_time)
                    self._logger.info("Death detected at %.0fs", game_time)
                self._prev_kda = curr_kda

                if self._debug and frame_count % cfg.status_interval == 0:
                    self._print_debug(ocr_values, det_summary, hero_dets, minimap_dets, bundle)

                game_time = parse_time(ocr_values.get("time", ""))

                # Update ObjectiveMemory
                self._update_objectives(bundle, game_time)

                # Context → Goal → Decision + profiling
                t0 = time.perf_counter()
                try:
                    v2_state = GameStateV2(game_time=game_time)
                    v2_state.context = self._context_engine.compute(bundle, v2_state)
                    goal = self._goal_engine.determine(v2_state, bundle)
                    decisions = self._decision_engine_v2.evaluate(v2_state, goal, bundle)
                except Exception as e:
                    self._logger.warning("Engine failed: %s", e)
                    v2_state = GameStateV2(game_time=game_time)
                    goal = Goal()
                    decisions = []
                self._profile["engine"] = time.perf_counter() - t0

                # LLM
                advice = None
                if self._llm_engine and self._llm_engine.should_advise(v2_state, goal):
                    advice = self._llm_engine.advise(v2_state, goal, decisions)

                # FPS
                frame_count += 1
                elapsed = time.time() - fps_timer
                if elapsed >= 1.0:
                    fps_display = frame_count / elapsed
                    fps_timer = time.time()

                    if frame_count % cfg.status_interval == 0:
                        self._display_status(bundle, hero_dets, minimap_dets, fps_display)
                        if decisions:
                            top = decisions[0]
                            print(f"  Goal: {goal.goal_type} ({goal.confidence:.0%}) → {top.action} ({top.score:.0f}) {top.reason}")
                        if advice:
                            print(f"  LLM: {advice}")

                    frame_count = 0

                if self._overlay:
                    self._overlay.update_state(self._make_overlay_data(
                        bundle, v2_state, goal, decisions, ocr_values, advice, fps=fps_display
                    ))
                    self._overlay.update_decisions(decisions)

                # Frame rate
                loop_time = time.time() - loop_start
                target_time = 1.0 / cfg.fps_target
                if loop_time < target_time:
                    time.sleep(target_time - loop_time)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self._logger.error("Frame error: %s", e, exc_info=self._debug)
                time.sleep(0.5)

        self._shutdown()

    def _run_ocr(self, frame, det_summary) -> dict[str, str]:
        """Run OCR on all regions and return results dict. Runs in thread pool."""
        result = {}
        try:
            from perception.detection_summary import extract_ocr_regions
            ocr_crops = extract_ocr_regions(frame, det_summary, scale=4)
            if "game_time" in ocr_crops and not self._video_cap:
                t = self._ocr.recognize_time(ocr_crops["game_time"])
                if t:
                    result["time"] = t
            if "kda" in ocr_crops:
                kda = self._ocr.recognize_kda(ocr_crops["kda"])
                if kda:
                    result["kda"] = f"{kda[0]}/{kda[1]}/{kda[2]}"
            if "gold" in ocr_crops:
                g = self._ocr.recognize_number(ocr_crops["gold"])
                if g is not None and g > 0:
                    result["gold"] = str(int(g))
            if "player_level" in ocr_crops:
                lv = self._ocr.recognize_number(ocr_crops["player_level"])
                if lv is not None and 1 <= lv <= self._cfg.level_max:
                    result["level"] = str(int(lv))
        except Exception:
            pass
        return result

    def _update_objectives(self, bundle, game_time: float) -> None:
        """Track objective spawn/kill transitions."""
        for obj_name, alive in bundle.objective.model_dump().items():
            obj_key = obj_name.replace("_alive", "")
            if obj_key not in ("dragon", "baron", "herald", "grub", "elder"):
                continue
            rec = self._objective_memory.get_objective(obj_key)
            if rec is None:
                continue
            if alive and not rec.alive:
                self._objective_memory.record_spawn(obj_key)
            elif not alive and rec.alive:
                self._objective_memory.record_kill(obj_key, game_time)

    def _display_status(self, bundle, hero_dets: list, minimap_dets: list, fps: float) -> None:
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

    def _make_overlay_data(self, bundle, v2_state, goal, decisions, ocr_values, advice=None, fps=0.0) -> dict:
        timers = self._objective_memory.get_spawn_timers(v2_state.game_time)

        game_time_str = ""
        if v2_state.game_time > 0:
            game_time_str = f"{int(v2_state.game_time // 60)}:{int(v2_state.game_time % 60):02d}"

        ocr_ready = self._ocr is not None and self._ocr.is_ready if self._ocr else False
        has_gold = bool(ocr_values.get("gold"))

        return {
            "game_time": game_time_str,
            "fps": fps,
            "ocr_ready": ocr_ready,
            "has_kda": bool(ocr_values.get("kda")),
            "has_gold": has_gold,
            "phase": v2_state.phase,
            "activity": v2_state.activity,
            "context": v2_state.context,
            "combat": v2_state.combat,
            "threat": v2_state.threat,
            "kda": ocr_values.get("kda", ""),
            "gold": bundle.economy.player_gold if has_gold else 0,
            "level": bundle.economy.player_level,
            "dragon_spawn_in": timers.get("dragon_spawn_in", -1.0),
            "baron_spawn_in": timers.get("baron_spawn_in", -1.0),
            "herald_spawn_in": timers.get("herald_spawn_in", -1.0),
            "grub_spawn_in": timers.get("grub_spawn_in", -1.0),
            "elder_spawn_in": timers.get("elder_spawn_in", -1.0),
            "goal_type": goal.goal_type if goal else "",
            "goal_confidence": goal.confidence if goal else 0.0,
            "advice": advice or "",
            "ally_count": bundle.hero.ally_count,
            "enemy_count": bundle.hero.enemy_count,
            "hp_ratio": bundle.hero.hp_ratio,
            "ult_ready": bundle.skill.ult_ready,
            "flash_ready": bundle.skill.flash_ready,
        }

    def _print_debug(self, ocr_values, det_summary, hero_dets, minimap_dets, bundle):
        p = self._profile
        self._logger.debug(
            "YOLO:%.1fms minimap:%.1fms engine:%.1fms OCR:%.1fms",
            p["yolo"] * 1000, p["minimap"] * 1000, p["engine"] * 1000, p["ocr"] * 1000,
        )
        self._logger.debug("ocr_values=%s", ocr_values)
        self._logger.debug("YOLO dets=%d skills=%s hp_bars: ally=%d enemy=%d",
                           len(hero_dets), [f"{s.skill}({s.confidence:.2f})" for s in det_summary.skills],
                           len(det_summary.ally_hp_bars), len(det_summary.enemy_hp_bars))
        self._logger.debug("minimap_dets=%d enemy=%d",
                           len(minimap_dets), sum(1 for d in minimap_dets if d.team == "enemy"))

    def _shutdown(self) -> None:
        print("\nShutting down modules...")
        self._pool.shutdown(wait=False)
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
    parser = argparse.ArgumentParser(description="LOL Agent Assistant (V2)")
    parser.add_argument("--model", type=str, default=None, help="YOLO weights path")
    parser.add_argument("--video", type=str, default=None, help="Video file path for testing")
    parser.add_argument("--no-overlay", action="store_true", help="Disable overlay")
    parser.add_argument("--no-voice", action="store_true", help="Disable TTS")
    parser.add_argument("--monitor", default="auto", help="Monitor index or 'auto'")
    parser.add_argument("--window", type=str, default=None, help="Window title to capture")
    parser.add_argument("--fps", type=float, default=5.0, help="Target FPS")
    parser.add_argument("--llm", action="store_true", help="Enable LLM advice")
    parser.add_argument("--llm-model", type=str, default=None, help="LLM model path (or set LOL_LLM_MODEL_PATH env var)")
    parser.add_argument("--debug", action="store_true", help="Show debug info")
    args = parser.parse_args()

    config = AgentConfig.from_args(args)

    agent = LolAgent(
        config=config,
        video_path=args.video,
        enable_overlay=not args.no_overlay,
        enable_voice=not args.no_voice,
        monitor=args.monitor,
        window_title=args.window,
        enable_llm=args.llm,
        debug=args.debug,
    )
    agent.run()


if __name__ == "__main__":
    main()

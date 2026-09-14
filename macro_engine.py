"""
Unified MacroEngine Orchestrator.
Manages threads, rod engine delegation, state machine, and auto-cast.
"""

import time
import threading
import mss
from input_handler import mouse_up_left, robust_mouse_hold
from engine_default import DefaultRodEngine
from engine_tranquility import TranquilityEngine

class MacroEngine:
    def __init__(self, config, on_lane_hit_fn=None, on_default_bar_fn=None, on_log_fn=None, on_state_fn=None):
        self.config = config
        self.on_lane_hit = on_lane_hit_fn
        self.on_default_bar = on_default_bar_fn
        self.on_log = on_log_fn
        self.on_state = on_state_fn
        
        self.is_running = False
        self.worker_thread = None
        
        # Engines
        self.default_engine = DefaultRodEngine(
            config=self.config,
            log_fn=self.log,
            on_bar_update_fn=self.on_default_bar,
            on_state_fn=self.on_state
        )
        
        self.tranquility_engine = TranquilityEngine(
            config=self.config,
            log_fn=self.log,
            on_lane_hit_fn=self.on_lane_hit,
            on_state_fn=self.on_state
        )
        
        # Stats
        self.fps = 0.0
        self.total_catches = 0
        self.last_fps_time = time.perf_counter()
        self.frame_count = 0

    def log(self, tag, msg):
        formatted = f"[{tag}] {msg}"
        print(formatted)
        if self.on_log:
            self.on_log(formatted)

    def _update_fps(self):
        self.frame_count += 1
        now = time.perf_counter()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (now - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = now

    def is_active(self):
        return self.is_running

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()
        
        if self.config.get('beep_sound'):
            try:
                import winsound
                winsound.Beep(1000, 120)
            except Exception:
                pass
                
        mode_name = "Default Rod (Thanh Bar Trượt)" if self.config.get('rod_mode') == 'default' else "Tranquility Rod (4 Làn Nhạc)"
        self.log("START", f"Macro ĐÃ BẬT ({mode_name}). Đang chờ bạn quăng cần câu để bắt đầu chuỗi tự động!")
        if self.on_state:
            self.on_state("STANDBY")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        # Guarantee mouse is released
        mouse_up_left()
        
        if self.config.get('beep_sound'):
            try:
                import winsound
                winsound.Beep(600, 150)
            except Exception:
                pass
                
        self.log("STOP", "Macro ĐÃ TẮT.")
        if self.on_state:
            self.on_state("STOPPED")

    def toggle(self):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def do_auto_cast(self):
        """Unified auto-cast handler across all rod modes."""
        if not self.is_running:
            return
            
        self.total_catches += 1
        if self.config.get('auto_cast', True):
            cast_delay = float(self.config.get('cast_delay_sec', 1.2))
            cast_duration = float(self.config.get('cast_duration_sec', 0.5))
            
            if self.on_state:
                self.on_state("CASTING")
            self.log("CAST", f"⏳ Chờ {cast_delay:.1f}s hoạt ảnh hoàn tất...")
            
            delay_waited = 0.0
            while delay_waited < cast_delay and self.is_running:
                time.sleep(0.08)
                delay_waited += 0.08
            
            if not self.is_running:
                return
            
            self.log("CAST", f"🎣 Đang quăng cần (giữ chuột {cast_duration:.1f}s)...")
            robust_mouse_hold(cast_duration)
            self.log("CAST", "🎣 Đã quăng cần xong! Chờ cá cắn câu...")
            
            # Post-cast grace period so bobber hits water before scanning
            time.sleep(0.5)
        
        if self.on_state:
            self.on_state("STANDBY")

    def _run_loop(self):
        """Dispatches to the chosen rod engine."""
        try:
            with mss.MSS() as sct:
                mode = self.config.get('rod_mode', 'default')
                if mode == 'default':
                    self.default_engine.run(
                        sct=sct,
                        is_running_fn=self.is_active,
                        do_auto_cast_fn=self.do_auto_cast,
                        update_fps_fn=self._update_fps
                    )
                else:
                    self.tranquility_engine.run(
                        sct=sct,
                        is_running_fn=self.is_active,
                        do_auto_cast_fn=self.do_auto_cast,
                        update_fps_fn=self._update_fps
                    )
        finally:
            mouse_up_left()

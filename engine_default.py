"""
Default Rod Engine for Fisch Macro.
Features:
- Dynamic white bar width detection
- Real-time fish tracking (dark notch & color distance)
- Velocity estimation & Predictive Inertia Compensation (Anti-Overshoot)
- Spam Click / PWM Hover Controller to lock fish directly in center
- Automatic minigame identification from standby
- Catch flash detection & transition to auto-cast
"""

import time
import numpy as np
from input_handler import mouse_down_left, mouse_up_left
from vision_utils import get_roblox_client_rect

class DefaultRodEngine:
    def __init__(self, config, log_fn=None, on_bar_update_fn=None, on_state_fn=None):
        self.config = config
        self.log = log_fn or print
        self.on_bar_update = on_bar_update_fn
        self.on_state = on_state_fn
        
        # Hover & mouse state
        self.is_mouse_down = False
        self.last_spam_toggle = time.perf_counter()
        
    def run(self, sct, is_running_fn, do_auto_cast_fn, update_fps_fn):
        """Runs the Default Rod vision and control loop with predictive anti-overshoot."""
        missing_bar_streak = 0
        minigame_active = False
        
        # Velocity and prediction trackers
        prev_bar_c = None
        prev_fish_x = None
        prev_time = None
        v_bar = 0.0
        v_fish = 0.0
        
        while is_running_fn() and self.config.get('rod_mode') == 'default':
            now = time.perf_counter()
            update_fps_fn()
            
            deadband = float(self.config.get('bar_deadband_px', 10))
            k_inertia = float(self.config.get('inertia_lead_sec', 0.12))
            k_lead = float(self.config.get('fish_lead_sec', 0.08))
            spam_pulse_sec = float(self.config.get('spam_pulse_ms', 30)) / 1000.0
            spam_enabled = bool(self.config.get('spam_enabled', True))
            
            # Resolve Roblox client rect or primary monitor
            roblox_info = get_roblox_client_rect()
            if roblox_info:
                _, rx, ry, rw, rh, title = roblox_info
            else:
                mon = [m for m in sct.monitors if m.get('is_primary')][0]
                rx, ry, rw, rh = mon['left'], mon['top'], mon['width'], mon['height']
                
            track_left = rx + int(rw * (570.0 / 1920.0))
            track_width = int(rw * ((1350.0 - 570.0) / 1920.0))
            track_top = ry + int(rh * (908.0 / 1080.0))
            track_height = max(18, int(rh * (30.0 / 1080.0)))
            
            roi = {'left': track_left, 'top': track_top, 'width': track_width, 'height': track_height}
            
            # ================= STATE 1: STANDBY =================
            if not minigame_active:
                prev_bar_c = None
                prev_fish_x = None
                prev_time = None
                v_bar = 0.0
                v_fish = 0.0
                
                try:
                    raw = sct.grab(roi)
                    frame = np.array(raw)[:, :, :3]
                except Exception:
                    time.sleep(0.1)
                    continue
                    
                col_bright = np.mean(frame, axis=(0, 2))
                edge = max(6, int(track_width * 0.015))
                valid_white = np.where(col_bright[edge:-edge] > 180)[0] + edge
                
                # Active minigame check: at least 60 white columns and NOT full flash (> 88% width)
                if len(valid_white) >= 60:
                    bar_l = valid_white[0]
                    bar_r = valid_white[-1]
                    bar_w = bar_r - bar_l
                    if 80 <= bar_w <= int(track_width * 0.88):
                        minigame_active = True
                        missing_bar_streak = 0
                        self.log("GAME", f"🎮 PHÁT HIỆN MINIGAME! Độ dài bar tự nhận diện: {bar_w}px. Bắt đầu tự động giữ tâm...")
                        if self.on_state:
                            self.on_state("PLAYING")
                
                if not minigame_active:
                    time.sleep(0.08)
                    continue

            # ================= STATE 2: PLAYING =================
            try:
                raw = sct.grab(roi)
                frame = np.array(raw)[:, :, :3]
            except Exception:
                time.sleep(0.05)
                continue
                
            col_bgr = np.mean(frame, axis=0)
            col_bright = np.mean(col_bgr, axis=1)
            edge = max(6, int(track_width * 0.015))
            valid_white = np.where(col_bright[edge:-edge] > 180)[0] + edge
            
            has_bar = len(valid_white) >= 40
            is_flash = False
            if has_bar:
                bar_l = valid_white[0]
                bar_r = valid_white[-1]
                bar_w = bar_r - bar_l
                bar_c = (bar_l + bar_r) / 2.0
                if bar_w > int(track_width * 0.88):
                    is_flash = True
            
            # Check if minigame ended (bar disappeared or catch flash)
            if not has_bar or is_flash:
                missing_bar_streak += 1
                if missing_bar_streak >= 3:
                    minigame_active = False
                    if self.is_mouse_down:
                        mouse_up_left()
                        self.is_mouse_down = False
                    self.log("GAME", "✅ Minigame kết thúc! Đã bắt cá thành công.")
                    do_auto_cast_fn()
                    missing_bar_streak = 0
                continue
            else:
                missing_bar_streak = 0
                
            # Track fish position: darkest column inside bar or color difference
            bar_inner = col_bright[bar_l:bar_r+1]
            darkest_idx = np.argmin(bar_inner)
            darkest_val = bar_inner[darkest_idx]
            
            target_fish = np.array([92, 73, 67], dtype=np.float32)
            color_diff = np.sum(np.abs(col_bgr - target_fish), axis=1)
            best_color_idx = np.argmin(color_diff)
            best_color_diff = color_diff[best_color_idx]
            
            if darkest_val < 160:
                fish_x = bar_l + darkest_idx
            elif best_color_diff < 40:
                fish_x = best_color_idx
            else:
                fish_x = best_color_idx
                
            raw_err = fish_x - bar_c
            
            # ================= VELOCITY & INERTIA PREDICTION =================
            if prev_bar_c is not None and prev_time is not None:
                dt = max(0.005, now - prev_time)
                inst_v_bar = (bar_c - prev_bar_c) / dt
                inst_v_fish = (fish_x - prev_fish_x) / dt
                # Exponential filter to prevent noise
                v_bar = 0.6 * inst_v_bar + 0.4 * v_bar
                v_fish = 0.6 * inst_v_fish + 0.4 * v_fish
            else:
                v_bar = 0.0
                v_fish = 0.0
                
            prev_bar_c = bar_c
            prev_fish_x = fish_x
            prev_time = now
            
            # Predictive error:
            # - (k_inertia * v_bar): early braking compensation for bar inertia!
            # + (k_lead * v_fish): lead prediction for fast moving fish!
            pred_err = raw_err - (k_inertia * v_bar) + (k_lead * v_fish)
            
            # ================= CONTROL DECISION WITH ANTI-OVERSHOOT =================
            if pred_err > deadband:
                # Need to accelerate right
                if not self.is_mouse_down:
                    mouse_down_left()
                    self.is_mouse_down = True
                action = "HOLD"
            elif pred_err < -deadband:
                # Need to slide left
                if self.is_mouse_down:
                    mouse_up_left()
                    self.is_mouse_down = False
                action = "RELEASE"
            else:
                # Within predictive zone: bar will naturally coast and land in center!
                # Activate Spam Hover / Counter-Braking to arrest momentum
                if spam_enabled:
                    if now - self.last_spam_toggle >= spam_pulse_sec:
                        self.is_mouse_down = not self.is_mouse_down
                        if self.is_mouse_down:
                            mouse_down_left()
                        else:
                            mouse_up_left()
                        self.last_spam_toggle = now
                    action = "SPAM_HOVER"
                else:
                    if self.is_mouse_down:
                        mouse_up_left()
                        self.is_mouse_down = False
                    action = "CENTERED"
                    
            if self.on_bar_update:
                self.on_bar_update(bar_l, bar_r, bar_w, bar_c, fish_x, raw_err, pred_err, v_bar, action, track_width)
                
        # Loop terminated: guarantee mouse is released
        if self.is_mouse_down:
            mouse_up_left()
            self.is_mouse_down = False

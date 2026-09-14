"""
Tranquility Rod Engine for Fisch Macro.
Features:
- Bottom-edge lock calibration on 4 target rings (immune to falling notes)
- Native lane note detection (Cyan, Purple, Yellow, Pink)
- Red note detection in any lane
- DirectInput key presses (D, F, J, K)
"""

import time
import threading
import cv2
import numpy as np
from input_handler import robust_send_key, mouse_click_at
from vision_utils import LANE_CONFIG, RED_NOTE_HSV, get_roblox_client_rect
from shake_detector import ShakeDetector

class TranquilityEngine:
    def __init__(self, config, log_fn=None, on_lane_hit_fn=None, on_state_fn=None):
        self.config = config
        self.log = log_fn or print
        self.on_lane_hit = on_lane_hit_fn
        self.on_state = on_state_fn
        
        # Shake detector
        self.shake_detector = ShakeDetector()
        self.last_shake_click = 0.0
        self.shake_count_session = 0
        
        self.is_calibrated = False
        self.target_coords = {}
        self.target_radius = 28
        self.capture_roi = None
        self.last_hit_times = {k: 0.0 for k in ['D', 'F', 'J', 'K']}
        self.total_hits = 0

    def calibrate(self, sct, frame_or_none=None, silent=False):
        """Finds the 4 target rings by locking onto their bottom edges."""
        try:
            if frame_or_none is not None:
                img = frame_or_none
                roi_offset_x = 0
                roi_offset_y = 0
            else:
                roblox_info = get_roblox_client_rect()
                if roblox_info:
                    _, rx, ry, rw, rh, title = roblox_info
                    roi = {'left': rx, 'top': ry, 'width': rw, 'height': rh}
                    roi_offset_x = rx
                    roi_offset_y = ry
                else:
                    mon = [m for m in sct.monitors if m.get('is_primary')][0]
                    roi = mon
                    roi_offset_x = mon['left']
                    roi_offset_y = mon['top']
                
                raw = sct.grab(roi)
                img = np.array(raw)[:, :, :3]
        
            H, W, _ = img.shape
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            roi_y_start = int(H * 0.45)
            hsv_lower = hsv[roi_y_start:, :]
            
            rings = {}
            for lane, cfg in LANE_CONFIG.items():
                mask = cv2.inRange(hsv_lower, np.array(cfg['ring_hsv_min']), np.array(cfg['ring_hsv_max']))
                ys, xs = np.where(mask)
                if len(ys) > 100:
                    ys += roi_y_start
                    bottom_y = int(ys.max())
                    ring_xs = xs[ys > bottom_y - 60]
                    if len(ring_xs) > 40:
                        cx = float((ring_xs.min() + ring_xs.max()) / 2)
                        radius = (ring_xs.max() - ring_xs.min()) / 2.0
                        cy = bottom_y - radius
                        rings[lane] = {
                            'screen_x': int(roi_offset_x + cx),
                            'screen_y': int(roi_offset_y + cy),
                            'local_x': int(cx),
                            'local_y': int(cy),
                            'radius': int(radius)
                        }
            
            if len(rings) == 4:
                xs = [r['screen_x'] for r in rings.values()]
                ys = [r['screen_y'] for r in rings.values()]
                self.target_radius = int(np.mean([r['radius'] for r in rings.values()]))
                pad = int(self.target_radius * 2.2)
                
                min_x = min(xs) - pad
                max_x = max(xs) + pad
                min_y = min(ys) - int(pad * 1.5)
                max_y = max(ys) + pad
                
                self.capture_roi = {
                    'left': min_x,
                    'top': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y
                }
                
                for lane, r in rings.items():
                    r['roi_x'] = r['screen_x'] - min_x
                    r['roi_y'] = r['screen_y'] - min_y
                
                self.target_coords = rings
                self.is_calibrated = True
                if not silent:
                    self.log("CALIB", f"Tranquility Rod: Đã khóa 4 làn tại Y={int(np.mean(ys))}px (Bán kính: {self.target_radius}px)")
                return True
            return False
        except Exception as e:
            if not silent:
                self.log("ERROR", f"Lỗi hiệu chỉnh Tranquility: {e}")
            return False

    def trigger_key_async(self, lane, is_red=False):
        """Asynchronously presses the key so screen capture remains uninterrupted."""
        key = LANE_CONFIG[lane]['key']
        duration = self.config['key_duration_ms'] / 1000.0
        threading.Thread(target=robust_send_key, args=(key, duration), daemon=True).start()
        self.total_hits += 1
        if self.on_lane_hit:
            self.on_lane_hit(lane, is_red)

    def run(self, sct, is_running_fn, do_auto_cast_fn, update_fps_fn):
        """Runs the Tranquility Rod 4-lane rhythm detection loop."""
        cooldown_sec = self.config['cooldown_ms'] / 1000.0
        timing_offset = self.config.get('timing_offset_px', 0)
        
        red_min1 = np.array(RED_NOTE_HSV[0][0])
        red_max1 = np.array(RED_NOTE_HSV[0][1])
        red_min2 = np.array(RED_NOTE_HSV[1][0])
        red_max2 = np.array(RED_NOTE_HSV[1][1])
        
        frame_count = 0
        missing_rings_streak = 0
        session_hits_start = self.total_hits
        
        while is_running_fn() and self.config.get('rod_mode') == 'tranquility':
            now = time.perf_counter()
            update_fps_fn()
            
            # STANDBY: Search for rings or Shake
            if not self.is_calibrated or self.capture_roi is None:
                found = self.calibrate(sct, silent=True)
                if not found:
                    if self.config.get('auto_shake', True) and (now - self.last_shake_click > 0.18):
                        roblox_info = get_roblox_client_rect()
                        if roblox_info:
                            _, rx, ry, rw, rh, title = roblox_info
                        else:
                            mon = [m for m in sct.monitors if m.get('is_primary')][0]
                            rx, ry, rw, rh = mon['left'], mon['top'], mon['width'], mon['height']
                        
                        shake_roi = {'left': rx, 'top': ry, 'width': rw, 'height': rh}
                        try:
                            shake_raw = sct.grab(shake_roi)
                            shake_frame = np.array(shake_raw)[:, :, :3]
                            found_shake, sx, sy, score = self.shake_detector.detect(
                                shake_frame, client_rect=(rx, ry, rw, rh), threshold=0.62
                            )
                            if found_shake:
                                self.shake_count_session += 1
                                self.log("SHAKE", f"🎯 Đã phát hiện nút SHAKE ({self.shake_count_session}) tại ({sx}, {sy}) -> Bấm!")
                                if self.on_state:
                                    self.on_state("SHAKING")
                                mouse_click_at(sx, sy, click_delay=0.03)
                                self.last_shake_click = time.perf_counter()
                                time.sleep(0.12)
                                continue
                        except Exception:
                            pass

                    time.sleep(0.06)
                    continue
                
                missing_rings_streak = 0
                self.shake_count_session = 0
                session_hits_start = self.total_hits
                if self.on_state:
                    self.on_state("PLAYING")
                self.log("GAME", "🎮 PHÁT HIỆN MINIGAME TRANQUILITY! Đang tự động chơi 4 làn...")
            
            try:
                raw = sct.grab(self.capture_roi)
                frame = np.array(raw)[:, :, :3]
            except Exception:
                self.is_calibrated = False
                time.sleep(0.15)
                continue
                
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            box_r = max(8, int(self.target_radius * 0.32))
            ring_offset_y = int(self.target_radius * 0.85)
            box_pixels = (box_r * 2 + 1) ** 2
            active_threshold = max(12, int(box_pixels * 0.02))
            
            # Periodically validate rings presence
            frame_count += 1
            if frame_count % 12 == 0:
                valid_rings = 0
                for lane, cfg in LANE_CONFIG.items():
                    t = self.target_coords[lane]
                    rx, ry = t['roi_x'], t['roi_y']
                    top_y = ry - ring_offset_y
                    if top_y >= 0 and top_y + 4 <= frame.shape[0]:
                        patch = hsv[max(0, top_y-3):top_y+4, rx-5:rx+6]
                        mask = cv2.inRange(patch, np.array(cfg['ring_hsv_min']), np.array(cfg['ring_hsv_max']))
                        if np.sum(mask > 0) >= 3:
                            valid_rings += 1
                
                if valid_rings < 2:
                    missing_rings_streak += 1
                    if missing_rings_streak >= 2:
                        self.is_calibrated = False
                        hits_this_game = self.total_hits - session_hits_start
                        self.log("GAME", f"✅ Minigame kết thúc! Đã đánh trúng {hits_this_game} nốt.")
                        do_auto_cast_fn()
                        missing_rings_streak = 0
                        continue
                else:
                    missing_rings_streak = 0
            
            # Check notes in each lane
            for lane in ['D', 'F', 'J', 'K']:
                if now - self.last_hit_times[lane] < cooldown_sec:
                    continue
                
                t_info = self.target_coords[lane]
                rx = t_info['roi_x']
                ry = t_info['roi_y'] + timing_offset
                
                fh, fw, _ = frame.shape
                if ry - box_r < 0 or ry + box_r + 1 > fh or rx - box_r < 0 or rx + box_r + 1 > fw:
                    continue
                
                box = hsv[ry - box_r : ry + box_r + 1, rx - box_r : rx + box_r + 1]
                cfg = LANE_CONFIG[lane]
                
                mask_native = cv2.inRange(box, np.array(cfg['note_hsv_min']), np.array(cfg['note_hsv_max']))
                matches_native = np.sum(mask_native > 0)
                
                mask_r1 = cv2.inRange(box, red_min1, red_max1)
                mask_r2 = cv2.inRange(box, red_min2, red_max2)
                matches_red = np.sum((mask_r1 | mask_r2) > 0)
                
                if matches_native >= active_threshold:
                    self.last_hit_times[lane] = now
                    self.trigger_key_async(lane, is_red=False)
                elif matches_red >= active_threshold:
                    self.last_hit_times[lane] = now
                    self.trigger_key_async(lane, is_red=True)

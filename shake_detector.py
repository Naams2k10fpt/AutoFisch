"""
Shake Minigame Detector for AutoFisch.
Detects circular SHAKE button on screen across all rods and UI scales using
a multi-scale dual-template matching bank on downscaled ROI (< 15ms per check).
"""

import base64
import cv2
import numpy as np

from shake_templates import B64_LARGE, B64_SMALL

def _decode_template(b64_str):
    raw = base64.b64decode(b64_str)
    arr = np.frombuffer(raw, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

class ShakeDetector:
    def __init__(self):
        t_large = _decode_template(B64_LARGE)
        t_small = _decode_template(B64_SMALL)
        
        # Pre-generate bank of downscaled templates (downscaled by 0.5 for fast matching)
        self.bank = [
            ("large_1.0", cv2.resize(t_large, (0, 0), fx=0.5, fy=0.5)),
            ("large_0.8", cv2.resize(t_large, (0, 0), fx=0.4, fy=0.4)),
            ("small_1.0", cv2.resize(t_small, (0, 0), fx=0.5, fy=0.5)),
            ("small_1.2", cv2.resize(t_small, (0, 0), fx=0.6, fy=0.6)),
        ]

    def detect(self, frame_bgr_or_gray, client_rect=None, threshold=0.62):
        """
        Searches for the SHAKE button in the frame.
        client_rect: (rx, ry, rw, rh) of Roblox window, or None.
        Returns: (found: bool, screen_x: int, screen_y: int, confidence: float)
        """
        if frame_bgr_or_gray is None:
            return False, 0, 0, 0.0
            
        if len(frame_bgr_or_gray.shape) == 3:
            gray = cv2.cvtColor(frame_bgr_or_gray, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame_bgr_or_gray

        h, w = gray.shape[:2]

        # Search area: 15% to 85% of client area
        x_min = int(w * 0.15)
        x_max = int(w * 0.85)
        y_min = int(h * 0.15)
        y_max = int(h * 0.85)

        roi = gray[y_min:y_max, x_min:x_max]
        if roi.shape[0] < 50 or roi.shape[1] < 50:
            return False, 0, 0, 0.0

        # Downscale 0.5x for blazing speed (~15ms)
        roi_half = cv2.resize(roi, (0, 0), fx=0.5, fy=0.5)

        best_score = -1.0
        best_loc = None
        best_tmpl_shape = None

        for _, tmpl in self.bank:
            res = cv2.matchTemplate(roi_half, tmpl, cv2.TM_CCOEFF_NORMED)
            min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
            if max_v > best_score:
                best_score = max_v
                best_loc = max_l
                best_tmpl_shape = tmpl.shape

        if best_score >= threshold and best_loc is not None:
            # Map back to full frame coordinates
            th, tw = best_tmpl_shape
            center_x_roi = int((best_loc[0] + tw // 2) * 2)
            center_y_roi = int((best_loc[1] + th // 2) * 2)

            frame_x = x_min + center_x_roi
            frame_y = y_min + center_y_roi

            if client_rect:
                rx, ry, _, _ = client_rect
                screen_x = rx + frame_x
                screen_y = ry + frame_y
            else:
                screen_x = frame_x
                screen_y = frame_y

            return True, screen_x, screen_y, float(best_score)

        return False, 0, 0, float(best_score)

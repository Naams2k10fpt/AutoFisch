"""
Vision utilities, window rectangle detection, and color configurations.
"""

import ctypes
from ctypes import wintypes
import cv2
import numpy as np

user32 = ctypes.windll.user32

# HSV Configurations for Tranquility Rod 4-Lane Minigame
RED_NOTE_HSV = [
    ((0, 70, 60), (10, 255, 255)),
    ((170, 70, 60), (180, 255, 255))
]

LANE_CONFIG = {
    'D': {
        'color_name': 'Cyan',
        'key': 'd',
        'hex': '#00E5FF',
        'ring_hsv_min': (85, 120, 140),
        'ring_hsv_max': (98, 255, 255),
        'note_hsv_min': (85, 80, 70),
        'note_hsv_max': (98, 255, 255),
    },
    'F': {
        'color_name': 'Purple',
        'key': 'f',
        'hex': '#A855F7',
        'ring_hsv_min': (120, 100, 140),
        'ring_hsv_max': (135, 255, 255),
        'note_hsv_min': (115, 60, 60),
        'note_hsv_max': (140, 255, 255),
    },
    'J': {
        'color_name': 'Yellow',
        'key': 'j',
        'hex': '#FACC15',
        'ring_hsv_min': (20, 70, 140),
        'ring_hsv_max': (35, 255, 255),
        'note_hsv_min': (18, 45, 70),
        'note_hsv_max': (38, 255, 255),
    },
    'K': {
        'color_name': 'Pink',
        'key': 'k',
        'hex': '#EC4899',
        'ring_hsv_min': (150, 100, 140),
        'ring_hsv_max': (175, 255, 255),
        'note_hsv_min': (145, 60, 70),
        'note_hsv_max': (178, 255, 255),
    },
}

def get_roblox_client_rect():
    """Finds the Roblox game window client rect in screen coordinates."""
    found = []
    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value.lower()
            if 'roblox' in title:
                rect = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rect))
                pt = wintypes.POINT(0, 0)
                user32.ClientToScreen(hwnd, ctypes.byref(pt))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 300 and h > 300:
                    found.append((hwnd, pt.x, pt.y, w, h, buf.value))
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    if found:
        found.sort(key=lambda item: item[3] * item[4], reverse=True)
        return found[0]
    return None

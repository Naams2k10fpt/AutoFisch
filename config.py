"""
Configuration manager for Fisch Macro.
Handles loading, saving, and default parameters.
"""

import os
import sys
import json

if getattr(sys, 'frozen', False):
    MACRO_DIR = os.path.dirname(sys.executable)
else:
    MACRO_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(MACRO_DIR, "config.json")

DEFAULT_CONFIG = {
    "hotkey_toggle": "f6",
    "hotkey_calibrate": "f7",
    "hotkey_exit": "f8",
    "rod_mode": "default",           # "default" (Bar) or "tranquility" (4-Lanes)
    "bar_deadband_px": 10,           # Deadband for centering fish in Default Rod
    "inertia_lead_sec": 0.12,        # Braking anticipation to prevent overshooting (seconds)
    "fish_lead_sec": 0.08,           # Predictive lead for fast swimming fish (seconds)
    "spam_pulse_ms": 50,             # Duration for rapid spam clicks to hover in center (ms)
    "spam_enabled": True,            # Enable spam clicking when fish is in center
    "cooldown_ms": 160,              # Cooldown between lane hits in Tranquility
    "key_duration_ms": 35,           # Key press duration for rhythm lanes
    "timing_offset_px": 0,           # Rhythm timing offset (-px = early, +px = late)
    "trigger_threshold": 12,
    "auto_cast": True,
    "auto_shake": True,              # Automatically click Shake buttons before minigame
    "cast_duration_sec": 0.5,
    "cast_delay_sec": 1.2,
    "beep_sound": True
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")

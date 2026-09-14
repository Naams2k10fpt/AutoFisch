"""
Low-level DirectInput sender for Keyboard & Mouse.
Guarantees hardware-level input registration in DirectX & Roblox.
"""

import time
import ctypes
from ctypes import wintypes
import pydirectinput

# Disable pydirectinput failsafe to prevent corner halts
pydirectinput.FAILSAFE = False
pydirectinput.PAUSE = 0.0

# Set Windows DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Ensure desktop access
try:
    u32 = ctypes.windll.user32
    hDesk = u32.OpenInputDesktop(0, False, 0x01FF)
    if hDesk:
        u32.SetThreadDesktop(hDesk)
except Exception:
    pass

ULONG_PTR = ctypes.c_uint64

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD)
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [
            ('mi', MOUSEINPUT),
            ('ki', KEYBDINPUT),
            ('hi', HARDWAREINPUT)
        ]
    _anonymous_ = ('_input',)
    _fields_ = [
        ('type', wintypes.DWORD),
        ('_input', _INPUT)
    ]

user32 = ctypes.windll.user32
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

SCANCODES = {'d': 0x20, 'f': 0x21, 'j': 0x24, 'k': 0x25}
VK_CODES = {'d': 0x44, 'f': 0x46, 'j': 0x4A, 'k': 0x4B}

def robust_send_key(key: str, hold_duration: float = 0.035) -> bool:
    """Multi-layer key sender guaranteeing DirectX / Roblox input registration."""
    k = key.lower()
    sc = SCANCODES.get(k)
    vk = VK_CODES.get(k)
    if not sc:
        return False
    
    success = False
    try:
        pydirectinput.keyDown(k)
        time.sleep(hold_duration)
        pydirectinput.keyUp(k)
        success = True
    except Exception:
        pass
        
    if not success:
        try:
            inp_down = INPUT(type=1)
            inp_down.ki = KEYBDINPUT(wVk=0, wScan=sc, dwFlags=KEYEVENTF_SCANCODE, time=0, dwExtraInfo=0)
            ret_down = user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            
            time.sleep(hold_duration)
            
            inp_up = INPUT(type=1)
            inp_up.ki = KEYBDINPUT(wVk=0, wScan=sc, dwFlags=KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            ret_up = user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
            
            if ret_down > 0 and ret_up > 0:
                success = True
        except Exception:
            pass

    if not success:
        try:
            user32.keybd_event(vk, sc, 0, 0)
            time.sleep(hold_duration)
            user32.keybd_event(vk, sc, 2, 0)
            success = True
        except Exception:
            pass
            
    return success

def mouse_down_left():
    """Presses and holds left mouse button."""
    try:
        pydirectinput.mouseDown(button='left')
    except Exception:
        pass
    try:
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    except Exception:
        pass

def mouse_up_left():
    """Releases left mouse button."""
    try:
        pydirectinput.mouseUp(button='left')
    except Exception:
        pass
    try:
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    except Exception:
        pass

def robust_mouse_hold(duration: float = 0.5):
    """Holds left mouse button for casting the fishing rod."""
    mouse_down_left()
    time.sleep(duration)
    mouse_up_left()

def mouse_click_at(x: int, y: int, click_delay: float = 0.03):
    """Moves mouse to (x, y) and performs a clean left click."""
    try:
        user32.SetCursorPos(int(x), int(y))
    except Exception:
        pass
    try:
        pydirectinput.moveTo(int(x), int(y))
    except Exception:
        pass
    user32.SetCursorPos(int(x), int(y))
    mouse_down_left()
    time.sleep(click_delay)
    mouse_up_left()


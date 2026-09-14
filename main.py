"""
Main entry point for Fisch Multi-Rod Auto Fishing Bot.
"""

import os
import sys
import ctypes
import tkinter as tk
from gui import MacroGUI

def init_dpi():
    """Ensure process is DPI aware so screen coordinates and MSS capture are pixel-perfect."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def get_asset_path(filename):
    """Find asset path in PyInstaller temp dir, exe dir, or script dir."""
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    if getattr(sys, 'frozen', False):
        p = os.path.join(os.path.dirname(sys.executable), filename)
        if os.path.exists(p):
            return p
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(p):
        return p
    return filename

def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Naams.AutoFisch.Bot.1.0")
    except Exception:
        pass

    init_dpi()
    root = tk.Tk()
    
    ico_path = get_asset_path("app.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass

    app = MacroGUI(root)
    root.protocol("WM_DELETE_WINDOW", app._exit_app)
    root.mainloop()

if __name__ == "__main__":
    main()

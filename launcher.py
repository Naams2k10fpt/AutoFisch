"""
AutoFisch Auto-Updating Launcher
Checks for latest releases on GitHub, downloads updates, and launches AutoFisch.exe.
"""

import os
import sys
import json
import time
import ctypes
import threading
import subprocess
import requests
import tkinter as tk
from tkinter import ttk, messagebox

# Repository Information
REPO_OWNER = "Naams2k10fpt"
REPO_NAME = "AutoFisch"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
TARGET_EXE = "AutoFischCore.exe"
VERSION_FILE = "version.json"


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    return os.path.join(get_base_dir(), filename)


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Fisch")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        self.root.configure(bg="#12131C")

        # Center window on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 400) // 2
        y = (sh - 200) // 2
        self.root.geometry(f"400x200+{x}+{y}")

        # Window Icon
        ico = get_asset_path("app.ico")
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

        self._build_ui()
        self.worker_thread = threading.Thread(target=self._update_and_launch, daemon=True)
        self.worker_thread.start()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#1A1C29", height=50)
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            header, text="🎣 AUTO FISCH",
            font=("Segoe UI", 12, "bold"), fg="#38BDF8", bg="#1A1C29"
        ).pack(side=tk.LEFT, padx=15, pady=10)

        self.ver_badge = tk.Label(
            header, text="v1.0.0",
            font=("Segoe UI", 9), fg="#94A3B8", bg="#1A1C29"
        )
        self.ver_badge.pack(side=tk.RIGHT, padx=15, pady=10)

        # Body
        body = tk.Frame(self.root, bg="#12131C", padx=20, pady=15)
        body.pack(fill=tk.BOTH, expand=True)

        self.status_lbl = tk.Label(
            body, text="Đang kiểm tra cập nhật từ GitHub...",
            font=("Segoe UI", 9, "bold"), fg="#F8FAFC", bg="#12131C", anchor=tk.W
        )
        self.status_lbl.pack(fill=tk.X, pady=(0, 6))

        # Progress bar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Cyan.Horizontal.TProgressbar",
            troughcolor="#1E2235",
            background="#38BDF8",
            bordercolor="#1E2235",
            lightcolor="#38BDF8",
            darkcolor="#0284C7"
        )

        self.prog = ttk.Progressbar(
            body, style="Cyan.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL, mode='determinate', length=360
        )
        self.prog.pack(fill=tk.X, pady=(0, 6))
        self.prog['value'] = 0

        self.detail_lbl = tk.Label(
            body, text="Kết nối máy chủ...",
            font=("Segoe UI", 8), fg="#94A3B8", bg="#12131C", anchor=tk.W
        )
        self.detail_lbl.pack(fill=tk.X)

    def _set_status(self, text, detail=None, pct=None):
        def update():
            self.status_lbl.config(text=text)
            if detail is not None:
                self.detail_lbl.config(text=detail)
            if pct is not None:
                self.prog['value'] = pct
        self.root.after(0, update)

    def _update_and_launch(self):
        base_dir = get_base_dir()
        target_path = os.path.join(base_dir, TARGET_EXE)
        ver_path = os.path.join(base_dir, VERSION_FILE)

        local_version = "1.0.0"
        if os.path.exists(ver_path):
            try:
                with open(ver_path, "r", encoding="utf-8") as f:
                    local_version = json.load(f).get("version", "1.0.0")
            except Exception:
                pass

        self._set_status("Đang kiểm tra phiên bản...", f"Bản hiện tại: v{local_version}", pct=10)

        # Check GitHub Release
        download_url = None
        latest_tag = local_version
        try:
            headers = {"User-Agent": "AutoFisch-Launcher"}
            resp = requests.get(GITHUB_API_URL, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                raw_tag = data.get("tag_name", "").lstrip("v").strip()
                if raw_tag:
                    latest_tag = raw_tag
                # Find core .exe asset
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if "core" in name and name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break
                if not download_url:
                    for asset in data.get("assets", []):
                        name = asset.get("name", "").lower()
                        if name.endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
        except Exception as e:
            # Network issue or rate-limit
            pass

        # Determine if we should download
        should_download = False
        if not os.path.exists(target_path) and download_url:
            should_download = True
        elif download_url and latest_tag > local_version:
            should_download = True

        if should_download and download_url:
            self._set_status(f"Phát hiện bản mới: v{latest_tag}!", "Đang tải gói cập nhật...", pct=20)
            tmp_path = target_path + ".tmp"
            try:
                with requests.get(download_url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))
                    done = 0
                    with open(tmp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                done += len(chunk)
                                if total > 0:
                                    pct = 20 + int((done / total) * 75)
                                    mb_done = done / (1024 * 1024)
                                    mb_tot = total / (1024 * 1024)
                                    self._set_status(
                                        f"Đang tải cập nhật: {int(done/total*100)}%",
                                        f"{mb_done:.1f} MB / {mb_tot:.1f} MB",
                                        pct=pct
                                    )

                # Swap files
                if os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except Exception:
                        os.rename(target_path, target_path + f".old_{int(time.time())}")

                os.rename(tmp_path, target_path)

                # Save local version
                with open(ver_path, "w", encoding="utf-8") as f:
                    json.dump({"version": latest_tag, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)

                self._set_status("Cập nhật thành công!", f"Đã nâng cấp lên v{latest_tag}", pct=100)
            except Exception as e:
                self._set_status("Tải bản cập nhật thất bại", f"Lỗi: {e}", pct=50)
                time.sleep(1.5)
        else:
            self._set_status("Phiên bản mới nhất!", f"v{local_version} đã sẵn sàng", pct=100)

        time.sleep(0.6)

        # Launch Bot
        if os.path.exists(target_path):
            self._set_status("Đang khởi động AutoFisch...", "Vui lòng đợi...", pct=100)
            try:
                subprocess.Popen([target_path], cwd=base_dir)
            except Exception as e:
                messagebox.showerror("Lỗi Khởi Chạy", f"Không thể mở AutoFisch.exe: {e}")
            self.root.after(400, self.root.destroy)
        else:
            messagebox.showwarning(
                "Thông Báo",
                "Chưa tìm thấy AutoFisch.exe và chưa có bản tải trên GitHub!\n"
                "Hãy đảm bảo AutoFisch.exe nằm cùng thư mục với Launcher."
            )
            self.root.after(0, self.root.destroy)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

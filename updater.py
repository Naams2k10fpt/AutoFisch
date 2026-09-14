"""
Auto-updater module for AutoFisch.
Checks GitHub Releases for updates, downloads the new standalone executable,
and performs an in-place self-replacement and restart.
"""

import os
import sys
import subprocess
import threading
import requests

CURRENT_VERSION = "1.0.0"
REPO_OWNER = "Naams2k10fpt"
REPO_NAME = "AutoFisch"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


def parse_version(ver_str):
    """Parses a version string like 'v1.0.1' or '1.0.0' into a tuple of integers."""
    try:
        clean = ver_str.strip().lstrip('v').lstrip('V')
        parts = [int(p) for p in clean.split('.') if p.isdigit()]
        return tuple(parts)
    except Exception:
        return (0, 0, 0)


def get_base_dir():
    """Returns the directory of the executable or script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def check_for_update_sync():
    """
    Synchronously queries GitHub Releases API.
    Returns: (has_update: bool, latest_tag: str, download_url: str, body: str)
    """
    try:
        headers = {"User-Agent": "AutoFisch-Updater"}
        resp = requests.get(GITHUB_API_URL, headers=headers, timeout=6)
        if resp.status_code != 200:
            return False, CURRENT_VERSION, None, ""

        data = resp.json()
        latest_tag = data.get("tag_name", "1.0.0")
        body = data.get("body", "")

        curr_parsed = parse_version(CURRENT_VERSION)
        latest_parsed = parse_version(latest_tag)

        if latest_parsed > curr_parsed:
            download_url = None
            for asset in data.get("assets", []):
                asset_name = asset.get("name", "").lower()
                if asset_name == "autofisch.exe" or asset_name.endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break

            if download_url:
                return True, latest_tag, download_url, body

        return False, latest_tag, None, body
    except Exception as e:
        print(f"[Updater] Check error: {e}")
        return False, CURRENT_VERSION, None, ""


def check_for_update_async(callback):
    """
    Runs update check in a background daemon thread.
    callback(has_update, latest_tag, download_url, body) will be called on completion.
    """
    def _worker():
        result = check_for_update_sync()
        if callback:
            callback(*result)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def download_update_sync(download_url, progress_callback=None):
    """
    Downloads the new executable from download_url into 'AutoFisch_new.exe'.
    Calls progress_callback(percent: float, downloaded_bytes: int, total_bytes: int).
    Returns the path to the downloaded file on success, or None on failure.
    """
    try:
        base_dir = get_base_dir()
        temp_file = os.path.join(base_dir, "AutoFisch_new.exe")

        headers = {"User-Agent": "AutoFisch-Updater"}
        with requests.get(download_url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_len = int(r.headers.get('content-length', 0))
            downloaded = 0

            with open(temp_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            percent = (downloaded / total_len * 100) if total_len > 0 else 0
                            progress_callback(percent, downloaded, total_len)

        return temp_file
    except Exception as e:
        print(f"[Updater] Download error: {e}")
        return None


def apply_update_and_restart(new_file_path):
    """
    Self-replaces the running executable with new_file_path using a detached batch script,
    then terminates the current process.
    """
    if not getattr(sys, 'frozen', False):
        print(f"[Updater] Running in source mode. Downloaded update to: {new_file_path}")
        return

    current_exe = sys.executable
    base_dir = os.path.dirname(current_exe)
    bat_path = os.path.join(base_dir, "_update_replace.bat")

    batch_script = f"""@echo off
chcp 65001 >nul
timeout /t 2 /nobreak >nul
move /y "{new_file_path}" "{current_exe}" >nul
start "" "{current_exe}"
del /f /q "%~f0" >nul
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(batch_script)

    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True
    )
    os._exit(0)

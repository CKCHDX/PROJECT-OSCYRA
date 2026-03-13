"""Sverkan client launcher (admin/student)."""

import os
import time
import webbrowser
import subprocess


def find_chrome():
    possible = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in possible:
        if os.path.exists(path):
            return path
    return None


def main():
    port = int(os.getenv("APP_PORT", 5000))
    url = f"http://localhost:{port}"

    print("=" * 50)
    print("Sverkan Client")
    print("=" * 50)
    print(f"Opening {url}")

    time.sleep(1)

    browser_path = find_chrome()
    if browser_path:
        subprocess.Popen([browser_path, f"--app={url}", "--start-fullscreen"])
    else:
        webbrowser.open(url)

    print("Client is running. Close the browser window to exit.")


if __name__ == "__main__":
    main()

"""Desktop entry point for Transcription Studio.

This module launches the FastAPI server in a background thread and opens
a native OS window using pywebview. When the window is closed, the app exits cleanly.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import webview


def _get_base_dir() -> Path:
    """Get the base directory for resources (frozen or dev mode)."""
    if hasattr(sys, '_MEIPASS'):
        # Running as a PyInstaller bundle
        return Path(sys._MEIPASS)
    # Running in development mode
    return Path(__file__).parent


def _find_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    """Poll the server until it's ready or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(('127.0.0.1', port))
                return True
        except (socket.error, OSError):
            time.sleep(0.1)
    return False


def _start_server(port: int) -> None:
    """Start the Uvicorn server in the current thread."""
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )


def main() -> None:
    """Launch the desktop application."""
    base_dir = _get_base_dir()

    # Set up environment variables for app.py to find resources
    os.environ['TRANSCRIPTION_BASE_DIR'] = str(base_dir)

    # Set ffmpeg path if bundled
    ffmpeg_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    ffmpeg_path = base_dir / ffmpeg_name
    if ffmpeg_path.exists():
        os.environ['FFMPEG_PATH'] = str(ffmpeg_path)

    # Find an available port
    port = _find_free_port()

    # Start the server in a daemon background thread
    server_thread = threading.Thread(
        target=_start_server,
        args=(port,),
        daemon=True,
    )
    server_thread.start()

    # Wait for the server to be ready
    if not _wait_for_server(port):
        print("Error: Server failed to start within the timeout period.", file=sys.stderr)
        sys.exit(1)

    # Open the pywebview window
    url = f"http://127.0.0.1:{port}"
    webview.create_window(
        title="Transcription Studio",
        url=url,
        width=1100,
        height=800,
        resizable=True,
    )
    webview.start()

    # When the window closes, the process exits (server thread is daemon)


if __name__ == '__main__':
    main()

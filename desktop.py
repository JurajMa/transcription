"""Desktop entry point for Transcription Studio.

This module launches the FastAPI server in a background thread and opens
an OS window using pywebview. In hotkey mode (Windows only), F4 works as
a global press-to-toggle recording hotkey while minimized to tray.
"""

from __future__ import annotations

import ctypes
import multiprocessing as mp
import os
import socket
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from queue import Empty
from typing import Any

import webview


def _get_base_dir() -> Path:
    """Get the base directory for resources (frozen or dev mode)."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def _find_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        sock.listen(1)
        return sock.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    """Poll the server until it's ready or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                sock.connect(('127.0.0.1', port))
                return True
        except (socket.error, OSError):
            time.sleep(0.1)
    return False


def _start_server(port: int) -> None:
    """Start the Uvicorn server in the current thread."""
    import uvicorn
    from app import app as fastapi_app

    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )


def _set_windows_clipboard_text(text: str) -> bool:
    """Write unicode text directly to the Windows clipboard."""
    if sys.platform != 'win32':
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    GMEM_MOVEABLE = 0x0002
    CF_UNICODETEXT = 13

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    data = (text or "") + "\0"
    size = len(data.encode("utf-16-le"))

    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
    if not handle:
        return False

    locked = kernel32.GlobalLock(handle)
    if not locked:
        kernel32.GlobalFree(handle)
        return False

    try:
        buf = ctypes.create_unicode_buffer(data)
        ctypes.memmove(locked, ctypes.addressof(buf), size)
    finally:
        kernel32.GlobalUnlock(handle)

    opened = False
    for _ in range(10):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.05)

    if not opened:
        kernel32.GlobalFree(handle)
        return False

    try:
        if not user32.EmptyClipboard():
            kernel32.GlobalFree(handle)
            return False
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        # Ownership of handle transfers to OS on success.
        return True
    finally:
        user32.CloseClipboard()


def _indicator_process_main(command_queue: "mp.Queue[tuple[str, Any]]") -> None:
    """Run the hotkey status indicator window in a dedicated process."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.95)

    frame = tk.Frame(root, bg="#121212", bd=0, highlightthickness=0)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, width=56, height=56, bg="#121212", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    state = {
        "flashing": False,
        "visible": False,
        "flash_on": True,
    }

    def place_window() -> None:
        root.update_idletasks()
        width = 56
        height = 56
        x = root.winfo_screenwidth() - width - 28
        y = root.winfo_screenheight() - height - 86
        root.geometry(f"{width}x{height}+{x}+{y}")

    def show_window() -> None:
        if not state["visible"]:
            place_window()
            root.deiconify()
            state["visible"] = True

    def hide_window() -> None:
        if state["visible"]:
            root.withdraw()
            state["visible"] = False

    def draw_recording_dot(on: bool) -> None:
        canvas.delete("all")
        fill = "#ef4444" if on else "#7f1d1d"
        canvas.create_oval(10, 10, 46, 46, fill=fill, outline="")

    def draw_symbol(symbol: str, color: str) -> None:
        canvas.delete("all")
        canvas.create_text(28, 28, text=symbol, fill=color, font=("Segoe UI", 20, "bold"))

    def flash_tick() -> None:
        if not state["flashing"]:
            return
        state["flash_on"] = not state["flash_on"]
        draw_recording_dot(state["flash_on"])
        root.after(420, flash_tick)

    def show_timed_symbol(symbol: str, color: str) -> None:
        state["flashing"] = False
        draw_symbol(symbol, color)
        show_window()
        root.after(1000, hide_window)

    def process_queue() -> None:
        try:
            while True:
                command, _payload = command_queue.get_nowait()
                if command == "recording":
                    state["flashing"] = True
                    state["flash_on"] = True
                    draw_recording_dot(True)
                    show_window()
                    root.after(420, flash_tick)
                elif command == "hide":
                    state["flashing"] = False
                    hide_window()
                elif command == "success":
                    show_timed_symbol("OK", "#22c55e")
                elif command == "error":
                    show_timed_symbol("X", "#facc15")
                elif command == "stop":
                    root.destroy()
                    return
        except Empty:
            pass

        root.after(80, process_queue)

    process_queue()
    root.mainloop()


class ScreenIndicator:
    """Small always-on-top visual indicator for hotkey mode state."""

    def __init__(self) -> None:
        self._queue: mp.Queue[tuple[str, Any]] = mp.Queue()
        self._process = mp.Process(target=_indicator_process_main, args=(self._queue,), daemon=False)
        self._process.start()

    def show_recording(self) -> None:
        self._queue.put(("recording", None))

    def hide(self) -> None:
        self._queue.put(("hide", None))

    def show_success(self) -> None:
        self._queue.put(("success", None))

    def show_error(self) -> None:
        self._queue.put(("error", None))

    def stop(self) -> None:
        if not self._process.is_alive():
            return
        self._queue.put(("stop", None))
        self._process.join(timeout=3.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)

class NullIndicator:
    """No-op indicator used on platforms without hotkey overlay support."""

    def show_recording(self) -> None:
        return

    def hide(self) -> None:
        return

    def show_success(self) -> None:
        return

    def show_error(self) -> None:
        return

    def stop(self) -> None:
        return


class DesktopController:
    """Coordinates tray, global hotkey, and JS bridge behavior."""

    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    WM_APP = 0x8000
    WM_ENABLE_HOTKEY = WM_APP + 1
    WM_DISABLE_HOTKEY = WM_APP + 2
    VK_F4 = 0x73
    HOTKEY_ID = 1099

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._window: webview.Window | None = None
        self._is_windows = sys.platform == 'win32'
        self._enabled = False
        self._hotkey_state = "idle"
        self._running = True
        self._lock = threading.Lock()
        self._allow_close_once = False

        self._indicator = ScreenIndicator() if self._is_windows else NullIndicator()
        self._tray_icon = None
        self._hotkey_thread_id: int | None = None
        self._hotkey_registered = False
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._hotkey_thread.start()

    def attach_window(self, window: webview.Window) -> None:
        self._window = window

    def shutdown(self) -> None:
        self._running = False
        if self._is_windows:
            self._post_hotkey_thread_message(self.WM_DISABLE_HOTKEY)
            self._post_hotkey_thread_message(self.WM_QUIT)
        self._hide_tray()
        self._indicator.stop()

    def set_hotkey_mode(self, enabled: bool) -> bool:
        if enabled and not self._is_windows:
            with self._lock:
                self._enabled = False
                self._hotkey_state = "idle"
                self._evaluate_js("window.desktopSetHotkeyLock && window.desktopSetHotkeyLock(false);")
            return False

        with self._lock:
            self._enabled = enabled
            if enabled:
                self._post_hotkey_thread_message(self.WM_ENABLE_HOTKEY)
            else:
                self._hotkey_state = "idle"
                self._indicator.hide()
                self._hide_tray()
                self._evaluate_js("window.desktopSetHotkeyLock && window.desktopSetHotkeyLock(false);")
                self._post_hotkey_thread_message(self.WM_DISABLE_HOTKEY)
        return self._enabled

    def _post_hotkey_thread_message(self, message: int) -> None:
        if not self._is_windows:
            return
        if self._hotkey_thread_id is None:
            return
        try:
            ctypes.windll.user32.PostThreadMessageW(self._hotkey_thread_id, message, 0, 0)
        except Exception:
            pass

    def on_window_minimized(self) -> None:
        with self._lock:
            enabled = self._enabled
        if not enabled:
            return

        if self._show_tray() and self._window is not None:
            self._window.hide()

    def on_window_closing(self, *args: Any) -> bool:
        """Hide to tray instead of closing when hotkey mode is enabled."""
        with self._lock:
            if self._allow_close_once:
                self._allow_close_once = False
                return True
            enabled = self._enabled

        if not enabled:
            return True

        if self._show_tray() and self._window is not None:
            self._window.hide()
            for arg in args:
                if hasattr(arg, 'cancel'):
                    setattr(arg, 'cancel', True)
            return False

        return True

    def on_hotkey_recording_failed(self, _message: str) -> None:
        with self._lock:
            self._hotkey_state = "idle"
            self._evaluate_js("window.desktopSetHotkeyLock && window.desktopSetHotkeyLock(false);")
        self._indicator.hide()
        self._indicator.show_error()

    def on_hotkey_transcription_success(self) -> None:
        with self._lock:
            self._hotkey_state = "idle"
            self._evaluate_js("window.desktopSetHotkeyLock && window.desktopSetHotkeyLock(false);")
        self._indicator.show_success()

    def on_hotkey_transcription_error(self, _message: str) -> None:
        with self._lock:
            self._hotkey_state = "idle"
            self._evaluate_js("window.desktopSetHotkeyLock && window.desktopSetHotkeyLock(false);")
        self._indicator.show_error()

    def on_hotkey_recording_started(self) -> None:
        with self._lock:
            if self._hotkey_state == "starting":
                self._hotkey_state = "recording"

    def _on_hotkey_pressed(self) -> None:
        with self._lock:
            if not self._enabled:
                return

            if self._hotkey_state == "idle":
                self._hotkey_state = "starting"
                self._evaluate_js("window.desktopHotkeyStartRecording && window.desktopHotkeyStartRecording();")
                self._indicator.show_recording()
                return

            if self._hotkey_state == "starting":
                self._hotkey_state = "idle"
                self._indicator.hide()
                self._evaluate_js("window.desktopHotkeyCancelStartRecording && window.desktopHotkeyCancelStartRecording();")
                return

            if self._hotkey_state == "recording":
                self._hotkey_state = "processing"
                self._indicator.hide()
                self._evaluate_js("window.desktopHotkeyStopAndTranscribe && window.desktopHotkeyStopAndTranscribe();")
                return

    def _evaluate_js(self, script: str) -> None:
        try:
            if self._window is not None:
                self._window.evaluate_js(script)
        except Exception:
            pass

    def _set_hotkey_registration(self, user32: Any, should_register: bool) -> None:
        if should_register:
            if self._hotkey_registered:
                return
            if user32.RegisterHotKey(None, self.HOTKEY_ID, 0, self.VK_F4):
                self._hotkey_registered = True
            return

        if not self._hotkey_registered:
            return
        user32.UnregisterHotKey(None, self.HOTKEY_ID)
        self._hotkey_registered = False

    def _hotkey_loop(self) -> None:
        if not self._is_windows:
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._hotkey_thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()

        # Ensure the thread message queue exists before PostThreadMessageW is used.
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        with self._lock:
            enabled_at_start = self._enabled
        self._set_hotkey_registration(user32, enabled_at_start)

        try:
            while self._running:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break

                if msg.message == self.WM_ENABLE_HOTKEY:
                    self._set_hotkey_registration(user32, True)
                    continue

                if msg.message == self.WM_DISABLE_HOTKEY:
                    self._set_hotkey_registration(user32, False)
                    continue

                if msg.message == self.WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                    self._on_hotkey_pressed()

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._set_hotkey_registration(user32, False)

    def _show_tray(self) -> bool:
        if self._tray_icon is not None:
            return True
        if sys.platform != 'win32':
            return False

        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return False

        def open_window(_icon: Any, _item: Any) -> None:
            self._hide_tray()
            if self._window is not None:
                try:
                    self._window.show()
                    self._window.restore()
                except Exception:
                    pass

        def exit_app(_icon: Any, _item: Any) -> None:
            self._allow_close_once = True
            self.shutdown()
            if self._window is not None:
                try:
                    self._window.destroy()
                except Exception:
                    os._exit(0)

        icon_path = self._base_dir / "icon.ico"
        if icon_path.exists():
            image = Image.open(icon_path)
        else:
            image = Image.new("RGBA", (64, 64), (20, 20, 20, 255))
            draw = ImageDraw.Draw(image)
            draw.ellipse((12, 12, 52, 52), fill=(239, 68, 68, 255))

        menu = pystray.Menu(
            pystray.MenuItem("Open", open_window, default=True),
            pystray.MenuItem("Exit", exit_app),
        )

        self._tray_icon = pystray.Icon("transcription_studio", image, "Transcription Studio", menu)
        self._tray_icon.run_detached()
        return True

    def _hide_tray(self) -> None:
        if self._tray_icon is None:
            return
        try:
            self._tray_icon.stop()
        finally:
            self._tray_icon = None


class JsApi:
    """Methods callable from the web UI via pywebview.api."""

    def __init__(self, controller: DesktopController) -> None:
        self._controller = controller

    def set_hotkey_mode(self, enabled: bool) -> bool:
        return self._controller.set_hotkey_mode(bool(enabled))

    def hotkey_recording_failed(self, message: str) -> bool:
        self._controller.on_hotkey_recording_failed(message)
        return True

    def hotkey_recording_started(self) -> bool:
        self._controller.on_hotkey_recording_started()
        return True

    def hotkey_transcription_success(self) -> bool:
        self._controller.on_hotkey_transcription_success()
        return True

    def hotkey_transcription_error(self, message: str) -> bool:
        self._controller.on_hotkey_transcription_error(message)
        return True

    def copy_to_clipboard(self, text: str) -> bool:
        return _set_windows_clipboard_text(text)

def main() -> None:
    """Launch the desktop application."""
    base_dir = _get_base_dir()

    os.environ['TRANSCRIPTION_BASE_DIR'] = str(base_dir)

    ffmpeg_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    ffmpeg_path = base_dir / ffmpeg_name
    if ffmpeg_path.exists():
        os.environ['FFMPEG_PATH'] = str(ffmpeg_path)
        os.environ['PATH'] = str(ffmpeg_path.parent) + os.pathsep + os.environ.get('PATH', '')

    port = _find_free_port()
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    if not _wait_for_server(port):
        print("Error: Server failed to start within the timeout period.", file=sys.stderr)
        sys.exit(1)

    controller = DesktopController(base_dir=base_dir)
    api = JsApi(controller)

    url = f"http://127.0.0.1:{port}"
    window = webview.create_window(
        title="Transcription Studio",
        url=url,
        width=1100,
        height=800,
        resizable=True,
        js_api=api,
    )
    controller.attach_window(window)

    try:
        window.events.minimized += controller.on_window_minimized
    except Exception:
        pass

    try:
        window.events.closing += controller.on_window_closing
    except Exception:
        pass

    try:
        webview.start()
    finally:
        controller.shutdown()


if __name__ == '__main__':
    mp.freeze_support()
    main()



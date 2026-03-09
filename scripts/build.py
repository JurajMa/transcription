#!/usr/bin/env python3
"""Cross-platform build helper for Transcription Studio.

This script detects the current OS and runs the appropriate PyInstaller spec file.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Build the desktop application for the current platform."""
    # Determine the current platform
    system = platform.system()

    if system == "Windows":
        spec_file = "build_windows.spec"
        ffmpeg_name = "ffmpeg.exe"
    elif system == "Darwin":
        spec_file = "build_mac.spec"
        ffmpeg_name = "ffmpeg"
    else:
        print(f"Error: Unsupported platform '{system}'", file=sys.stderr)
        print("This script only supports Windows and macOS.", file=sys.stderr)
        sys.exit(1)

    # Check that we're in the project root
    project_root = Path(__file__).parent.parent
    spec_path = project_root / spec_file
    if not spec_path.exists():
        print(f"Error: Spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    # Check that ffmpeg binary exists
    ffmpeg_path = project_root / ffmpeg_name
    if not ffmpeg_path.exists():
        print(f"Warning: {ffmpeg_name} not found in project root.", file=sys.stderr)
        print(f"Please download a static ffmpeg build from https://ffmpeg.org/download.html", file=sys.stderr)
        print(f"and place the {ffmpeg_name} binary in: {project_root}", file=sys.stderr)
        print(f"\nYou can still build without ffmpeg, but audio conversion won't work.", file=sys.stderr)
        print(f"Make sure to uncomment the ffmpeg line in {spec_file} before building with it.", file=sys.stderr)
        response = input("\nContinue without ffmpeg? [y/N] ")
        if response.lower() != 'y':
            sys.exit(1)

    # Check that PyInstaller is installed
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: PyInstaller is not installed.", file=sys.stderr)
        print("Install build deps with: python -m pip install -r requirements-build.txt", file=sys.stderr)
        sys.exit(1)

    # Run PyInstaller
    print(f"Building for {system}...")
    print(f"Using spec file: {spec_file}")
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", spec_file],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"\nError: Build failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)

    # Print success message
    output_dir = project_root / "dist" / "TranscriptionStudio"
    print("\n" + "=" * 60)
    print("Build completed successfully!")
    print("=" * 60)
    print(f"\nOutput directory: {output_dir}")

    if system == "Darwin":
        app_path = project_root / "dist" / "TranscriptionStudio.app"
        print(f"macOS app bundle: {app_path}")
        print("\nTo run the app:")
        print(f"  open {app_path}")
        print("\nNote: macOS Gatekeeper will show a warning unless you code-sign the app")
        print("with an Apple Developer certificate.")
    else:
        exe_path = output_dir / "TranscriptionStudio.exe"
        print(f"Windows executable: {exe_path}")
        print("\nTo run the app:")
        print(f"  {exe_path}")

    print("\nYou can distribute the entire folder to users.")
    print("They can run the app without installing Python or any dependencies.")


if __name__ == '__main__':
    main()


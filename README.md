# Transcription Studio

**Record or upload audio and get a text transcript — powered by your own OpenAI API key.**

Transcription Studio is a lightweight, self-hosted alternative to Wispr Flow. Paste your OpenAI API key, press record or drop in your audio file, and receive an accurate transcript in seconds. The app **does not store your audio or your API key** — audio is sent directly to the OpenAI API for processing and all temporary files are deleted immediately afterwards.

![Transcription Studio UI](static/screenshot.png)

## Why use this?

| | Transcription Studio | Wispr Flow |
|---|---|---|
| **Cost** | Pay-per-use via your own OpenAI API key | Monthly subscription |
| **Setup** | `pip install` + API key, self-hosted | Download desktop app, create account |
| **Privacy** | Audio sent to OpenAI API only; nothing stored locally | Audio processed by Wispr's servers |
| **Flexibility** | Open-source, customisable, CLI + web UI | Closed-source desktop app |

## How it works

1. Audio is split into overlapping chunks (~4.5 min each) to stay within API limits.
2. Each chunk is sent to the OpenAI transcription API (`gpt-4o-transcribe` by default).
3. Overlapping text between chunks is automatically deduplicated.
4. The final stitched transcript is displayed and can be copied or downloaded.

## Features

- 🎙️ **Record directly** in the browser or drag & drop / upload audio files
- 🎵 **Multi-format support** — WAV, M4A, MP3, MP4, AAC, FLAC, OGG, WEBM (auto-converted to WAV)
- 🔐 **Your API key stays private** — entered per-session, never stored or logged
- 🗑️ **No audio storage** — temporary files are cleaned up immediately after transcription
- ⚡ **Intelligent chunking** with overlap and deduplication for seamless long-form transcripts
- 💾 **Copy or save** the transcript as a `.txt` file
- 🖥️ **CLI included** for scripting and batch workflows

## Quick start

### 1. Install dependencies

```bash
# Create a virtual environment (conda or venv)
conda create -n transcription python=3.11 && conda activate transcription
# Or: python -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

**FFmpeg** is required for non-WAV audio conversion:
- **Windows:** `conda install -c conda-forge ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### 2. Launch the web app

```bash
uvicorn app:app --reload
```

Open [http://localhost:8000](http://localhost:8000), paste your OpenAI API key, and start transcribing.

### 3. Or use the CLI

```bash
export OPENAI_API_KEY="your_key_here"       # Linux / macOS
# set OPENAI_API_KEY=your_key_here          # Windows

python transcribe_audio.py path/to/audio.wav
```

CLI options:

| Flag | Description |
|---|---|
| `--output PATH` | Custom output file path |
| `--no-save` | Print transcript to stdout without saving |
| `--keep-chunks` | Keep intermediate chunk files for inspection |

> **Note:** The CLI currently accepts WAV files only. For other formats, use the web UI or pre-convert with FFmpeg.

## Privacy & security

- **API key** — entered in the browser, sent over HTTPS to the OpenAI API, and discarded after the request. It is never written to disk or logged.
- **Audio data** — uploaded audio is held in a temporary file only for the duration of processing. It is sent to the OpenAI API for transcription and then immediately deleted. The app does not retain, log, or transmit your audio anywhere else.
- **Transcripts** — displayed in your browser. Nothing is saved server-side unless you explicitly use the CLI `--output` flag.

## Project structure

```
├── app.py                  # FastAPI web server
├── transcribe_audio.py     # CLI entry point
├── transcription/
│   ├── __init__.py
│   └── service.py          # Core chunking & transcription logic
├── static/
│   ├── index.html          # Web UI
│   ├── styles.css
│   └── app.js
└── requirements.txt
```

## License

© Juraj Mavračić 2025

---

## Desktop Packaging

Transcription Studio can be packaged as a standalone desktop application for **Windows** and **macOS**. The desktop app opens in a native OS window (not a browser) and includes all dependencies—users don't need Python, pip, or a terminal.

### Prerequisites

#### 1. Install build dependencies

```bash
pip install -r requirements-build.txt
```

#### 2. Download ffmpeg

You need a **static ffmpeg build** to bundle with the app:

- **Windows**: Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (get the "essentials" build)
  - Extract `ffmpeg.exe` and place it in the project root directory
- **macOS**: Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (get the static build)
  - Extract the `ffmpeg` binary and place it in the project root directory

#### 3. Uncomment the ffmpeg line in the spec file

Before building, edit the appropriate `.spec` file (`build_windows.spec` or `build_mac.spec`) and **uncomment** the ffmpeg binary line:

```python
# In build_windows.spec:
binaries=[
    ('ffmpeg.exe', '.'),  # <-- Uncomment this line
],

# In build_mac.spec:
binaries=[
    ('ffmpeg', '.'),  # <-- Uncomment this line
],
```

### Building

#### Option 1: Use the build script (recommended)

```bash
python scripts/build.py
```

The script will:
- Detect your OS (Windows or macOS)
- Check that ffmpeg and PyInstaller are available
- Run the appropriate PyInstaller spec file
- Print the output location

#### Option 2: Run PyInstaller directly

**Windows:**
```bash
pyinstaller build_windows.spec
```

**macOS:**
```bash
pyinstaller build_mac.spec
```

### Output

After building, you'll find the packaged app in:

```
dist/TranscriptionStudio/
```

- **Windows**: `dist/TranscriptionStudio/TranscriptionStudio.exe` — double-click to run
- **macOS**: `dist/TranscriptionStudio.app` — double-click to run

You can distribute the entire `dist/TranscriptionStudio/` folder to users. They can run the app without installing Python or any other dependencies.

### Important Notes

- **Cross-compilation is not supported**: You must build ON Windows for Windows, and ON macOS for macOS
- **macOS Gatekeeper warning**: Users will see a security warning unless you code-sign the app with an Apple Developer certificate
  - To bypass for testing: Right-click the app → "Open" → click "Open" in the dialog
  - For distribution, you should sign the app: `codesign -s "Developer ID Application: Your Name" TranscriptionStudio.app`
- **Windows antivirus**: Some antivirus software may flag the `.exe` as suspicious (false positive)
  - This is common with PyInstaller apps—consider code-signing the executable
- **App size**: The bundled app will be ~100-200 MB due to Python runtime, dependencies, and ffmpeg

### Troubleshooting

- **"ffmpeg not found" error**: Make sure you downloaded the ffmpeg binary, placed it in the project root, and uncommented the line in the `.spec` file
- **Import errors**: Make sure all dependencies are installed (`pip install -r requirements.txt`)
- **Build fails on macOS**: You may need to install Xcode Command Line Tools (`xcode-select --install`)

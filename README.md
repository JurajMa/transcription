# Transcription Studio



**Record or upload audio and get a text transcript — powered by your own OpenAI API key.** 


## ⬇️ Download

### [Download Transcription Studio for Windows — v1.1.0](https://github.com/JurajMa/transcription/releases/download/v1.1.0/TranscriptionStudio_Setup_1.1.0.exe)

One-click installer · Windows 10+ · No Python required. · You only pay OpenAI per use, this app is free





![Transcription Studio UI](static/screenshot.png)

> **🔑 Bring Your Own Key (BYOK)** — You need your own OpenAI API key to use this app. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). This means you:
> - Always use the **latest state-of-the-art transcription models**
> - **Control your own usage and costs** directly through OpenAI. **This app is free**, you only pay OpenAI for transcription
> - Pay **far less** than with subscription-based transcription services
>
> ⚠️ **Always [set usage limits](https://platform.openai.com/settings/organization/limits) on your API key. Your API key is sent directly to OpenAI and not stored anywhere. Paste at your own risk — never share this app with untrusted users.**

## Why use this?

Transcription Studio is a lightweight, self-hosted alternative to Wispr Flow. Paste your OpenAI API key, press record or drop in your audio file, and receive an accurate transcript in seconds. The app **does not store your audio or your API key** — audio is sent directly to the OpenAI API for processing and all temporary files are deleted immediately afterwards.

| | Transcription Studio | Wispr Flow |
|---|---|---|
| **Cost** | This app is free, Pay-per-use for the model directly via your own OpenAI API key (🥜) | Monthly subscription |
| **Setup** | One-click install + API key | Download desktop app, create account |
| **Privacy** | Audio sent to OpenAI API only; nothing stored locally | Audio processed by Wispr's servers |
| **Flexibility** | Open-source, customisable, CLI + web UI | Closed-source desktop app |

## Installation

The easiest way to get started is to download the Windows installer from the [Releases](../../releases) page on GitHub. Run the installer, launch the app, paste your OpenAI API key, and start transcribing — no Python or terminal required.

> ⚠️ **Windows SmartScreen warning:** The installer is not code-signed, so Windows may show a warning saying the app is from an "unknown publisher". This is normal for independent software.
>
> **To install:** Click **"More info"** → then click **"Run anyway"**

## How it works

1. Audio is split into overlapping chunks (~4.5 min each) to stay within API limits.
2. Each chunk is sent to the OpenAI transcription API (`gpt-4o-transcribe` by default).
3. Overlapping text between chunks is automatically deduplicated.
4. The final stitched transcript is displayed and can be copied or downloaded.

## Features

- 🎙️ **Record directly** in the app or drag & drop / upload audio files
- 🎵 **Multi-format support** — WAV, M4A, MP3, MP4, AAC, FLAC, OGG, WEBM (auto-converted to WAV)
- 🔐 **Your API key stays private** — entered per-session, never stored or logged
- 🗑️ **No audio storage** — temporary files are cleaned up immediately after transcription
- ⚡ **Intelligent chunking** with overlap and deduplication for seamless long-form transcripts
- 💾 **Copy or save** the transcript as a `.txt` file

## Changelog

### v1.1.0
- Added Windows hotkey mode (`F4`) for start/stop recording while minimized to tray.
- Added tray workflow and on-screen status indicator (recording, success, error).
- Hotkey transcriptions now auto-copy to clipboard when processing completes.

## Privacy & security

- **API key** — entered in the app, sent over HTTPS to the OpenAI API, and discarded after the request. It is never written to disk or logged.
- **Audio data** — uploaded audio is held in a temporary file only for the duration of processing. It is sent to the OpenAI API for transcription and then immediately deleted. The app does not retain, log, or transmit your audio anywhere else.
- **Transcripts** — displayed in the app. Nothing is saved unless you explicitly save or copy the text.

## Disclaimer

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

**IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY**, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. THIS INCLUDES, WITHOUT LIMITATION, ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF DATA, LOSS OF PROFITS, BUSINESS INTERRUPTION, OR ANY FINANCIAL LOSSES.

By using this software, you acknowledge and agree that:

- **You are solely responsible for your OpenAI API key.** The author is not responsible for any unauthorised access to, misuse of, or charges incurred on your API key, whether resulting from your own actions, third-party access, security breaches, or any other cause.
- **You are solely responsible for all costs** incurred through the OpenAI API. The author has no control over and accepts no liability for API pricing, usage charges, or billing disputes.
- **You are solely responsible for the security of your system and network.** The author makes no guarantees regarding the security of data in transit or at rest and is not liable for any data breaches, interceptions, or leaks.
- **You are solely responsible for compliance** with all applicable laws, regulations, and third-party terms of service (including OpenAI's usage policies) in your jurisdiction.
- **Audio data and transcripts** are processed at your own risk. The author is not responsible for the accuracy, completeness, or suitability of any transcription output.
- **The author does not provide any technical support, security guarantees, or uptime commitments** for this software.

Use of this software is entirely at your own risk.

## License

© Juraj Mavračić 2025. All rights reserved.

This software is proprietary. No part of this software may be reproduced, distributed, or transmitted in any form or by any means without the prior written permission of the author, except for personal, non-commercial use as made available through official releases.

---

# For Developers

Everything below is for developers who want to run from source, use the CLI, or build the desktop app themselves.

## Running from source

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

## Desktop packaging

Transcription Studio can be packaged as a standalone desktop application for **Windows** and **macOS**. The desktop app opens in a native OS window (not a browser) and includes all dependencies, so users do not need Python, pip, or a terminal.

### Quick build (Windows PowerShell)

Run these commands from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe .\scripts\build.py
```

Build output:

- `dist/TranscriptionStudio/TranscriptionStudio.exe`

### Prerequisites

1. Install runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Install build dependencies:

```bash
python -m pip install -r requirements-build.txt
```

3. Place ffmpeg in the project root:

- **Windows**: `ffmpeg.exe`
- **macOS**: `ffmpeg`

### Build commands

Recommended:

```bash
python scripts/build.py
```

Direct PyInstaller (alternative):

- **Windows**: `python -m PyInstaller build_windows.spec`
- **macOS**: `python -m PyInstaller build_mac.spec`

### Notes

- The build helper now runs PyInstaller via the current Python interpreter (`python -m PyInstaller`), so activation is optional.
- `build_windows.spec` already includes `ffmpeg.exe` and tray/hotkey dependencies.
- `build_mac.spec` keeps ffmpeg optional by default; uncomment `('ffmpeg', '.')` if you want ffmpeg bundled in macOS builds.
- Cross-compilation is not supported (build Windows on Windows, macOS on macOS).

### Troubleshooting

- **`PyInstaller is not installed`**: `python -m pip install -r requirements-build.txt`
- **Missing imports at runtime**: reinstall deps with `python -m pip install -r requirements.txt`
- **`ffmpeg not found`**: place the correct ffmpeg binary in the project root before building
- **Build fails on macOS**: install Xcode Command Line Tools (`xcode-select --install`)

const fileInput = document.getElementById("fileInput");
const uploadButton = document.getElementById("uploadButton");
const dropZone = document.getElementById("dropZone");
const fileName = document.getElementById("fileName");
const apiKeyInput = document.getElementById("apiKeyInput");
const toggleKey = document.getElementById("toggleKey");
const transcribeButton = document.getElementById("transcribeButton");
const saveButton = document.getElementById("saveButton");
const statusLog = document.getElementById("statusLog");
const transcriptSection = document.getElementById("transcriptSection");
const transcriptOutput = document.getElementById("transcriptOutput");
const recordButton = document.getElementById("recordButton");
const recordTimer = document.getElementById("recordTimer");
const recordingIndicator = document.getElementById("recordingIndicator");
const copyButton = document.getElementById("copyButton");
const hotkeyPanel = document.getElementById("hotkeyPanel");
const hotkeyToggle = document.getElementById("hotkeyToggle");

let selectedFile = null;
let transcriptText = "";
let mediaRecorder = null;
let audioChunks = [];
let timerInterval = null;
let recordingSeconds = 0;
let recordingOrigin = "manual";

let isRecording = false;
let isLoading = false;
let hotkeyModeEnabled = false;
let hotkeyLockActive = false;
let hotkeyStopRequested = false;
let hotkeyState = "idle";
let hotkeyStartCancelled = false;

let desktopApi = null;
let desktopBridgeReady = false;

const setStatus = (messages, { append = false } = {}) => {
  if (!append) {
    statusLog.innerHTML = "";
  }
  const ensureArray = Array.isArray(messages) ? messages : [messages];
  ensureArray.forEach((message) => {
    const entry = document.createElement("p");
    entry.className = "status-entry";
    entry.textContent = message;
    statusLog.appendChild(entry);
  });
  statusLog.scrollTop = statusLog.scrollHeight;
};

const resetTranscript = () => {
  transcriptText = "";
  transcriptOutput.textContent = "";
  transcriptSection.hidden = true;
  saveButton.disabled = true;
  copyButton.hidden = true;
};

const updateButtons = () => {
  const hasFile = Boolean(selectedFile);
  const hasKey = Boolean(apiKeyInput.value.trim());

  const lockUi = isLoading || hotkeyLockActive;

  transcribeButton.disabled = lockUi || isRecording || !(hasFile && hasKey);
  saveButton.disabled = lockUi || transcriptText.length === 0;
  copyButton.hidden = transcriptText.length === 0;
  recordButton.disabled = isRecording ? lockUi : (!hasKey || lockUi);
  uploadButton.disabled = !hasKey || lockUi || isRecording;
  hotkeyToggle.disabled = !hasKey || lockUi || isRecording;
  apiKeyInput.disabled = lockUi;
  toggleKey.disabled = lockUi;
  hotkeyPanel.classList.toggle("disabled", hotkeyToggle.disabled);

  apiKeyInput.classList.toggle("key-empty", !hasKey);
  dropZone.classList.toggle("enabled", hasKey);
  dropZone.classList.toggle("dragging", isLoading);
};

const setLoading = (loading) => {
  isLoading = loading;
  if (loading) {
    setStatus(["Uploading audio...", "Contacting OpenAI..."], { append: false });
  }
  updateButtons();
};

const setHotkeyLock = (locked) => {
  hotkeyLockActive = locked;
  if (!locked) {
    hotkeyStopRequested = false;
  }
  updateButtons();
};

const selectFile = (file) => {
  if (!file) return;
  if (!apiKeyInput.value.trim()) {
    setStatus("Paste your OpenAI API key first.", { append: false });
    return;
  }

  const supportedFormats = [".wav", ".m4a", ".mp3", ".mp4", ".aac", ".flac", ".ogg", ".webm"];
  const fileExt = file.name.toLowerCase().match(/\.[^.]+$/)?.[0];

  if (!fileExt || !supportedFormats.includes(fileExt)) {
    setStatus(`Please upload a supported audio file: ${supportedFormats.join(", ")}`, { append: false });
    return;
  }

  selectedFile = file;
  fileName.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
  const conversionNote = fileExt === ".wav" ? "" : " (will be converted to WAV)";
  setStatus(`Ready to transcribe ${file.name}${conversionNote}.`, { append: false });
  resetTranscript();
  updateButtons();
};

const copyTranscriptToClipboard = async () => {
  if (!transcriptText) return false;

  try {
    await navigator.clipboard.writeText(transcriptText);
    return true;
  } catch {
    const range = document.createRange();
    range.selectNodeContents(transcriptOutput);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    const copied = document.execCommand("copy");
    selection.removeAllRanges();
    return copied;
  }
};

const runTranscription = async ({ fromHotkey = false } = {}) => {
  if (!selectedFile) {
    setStatus("Choose an audio file before transcribing.");
    return;
  }
  if (!apiKeyInput.value.trim()) {
    setStatus("Paste your OpenAI API key to continue.");
    if (fromHotkey && desktopApi?.hotkey_transcription_error) {
      await desktopApi.hotkey_transcription_error("Missing API key.");
    }
    return;
  }

  setLoading(true);
  resetTranscript();

  const formData = new FormData();
  formData.append("audio", selectedFile);
  formData.append("api_key", apiKeyInput.value.trim());

  try {
    const response = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let payload;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      const detail = (() => {
        if (payload == null) return response.statusText || "Request failed";
        if (typeof payload === "string") return payload;
        if (typeof payload.detail === "string") return payload.detail;
        if (Array.isArray(payload.detail)) return payload.detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
        if (payload.message && typeof payload.message === "string") return payload.message;
        return JSON.stringify(payload);
      })();

      throw new Error(detail || response.statusText || "Transcription failed");
    }

    const data = await response.json();
    transcriptText = data.transcript ?? "";
    transcriptOutput.textContent = transcriptText || "<empty transcript>";
    transcriptSection.hidden = transcriptText.length === 0;

    statusLog.innerHTML = "";
    (data.logs || []).forEach((line) => setStatus(line, { append: true }));
    if (!data.logs?.length) {
      setStatus("Transcription completed.", { append: true });
    }

    if (fromHotkey) {
      let copied = false;
      if (desktopApi?.copy_to_clipboard) {
        copied = await desktopApi.copy_to_clipboard(transcriptText);
      }
      if (!copied) {
        copied = await copyTranscriptToClipboard();
      }
      if (!copied) {
        throw new Error("Transcription succeeded but copying to clipboard failed.");
      }
      if (desktopApi?.hotkey_transcription_success) {
        await desktopApi.hotkey_transcription_success();
      }
    }
  } catch (error) {
    console.error(error);
    const message = (() => {
      if (!error) return "Unknown error";
      if (typeof error === "string") return error;
      if (error.message) return error.message;
      try {
        return JSON.stringify(error);
      } catch {
        return String(error);
      }
    })();

    setStatus(`Error: ${message}`, { append: false });
    resetTranscript();

    if (fromHotkey && desktopApi?.hotkey_transcription_error) {
      await desktopApi.hotkey_transcription_error(message);
    }
  } finally {
    setLoading(false);
    if (fromHotkey) {
      setHotkeyLock(false);
    }
    updateButtons();
  }
};

const formatTime = (seconds) => {
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
};

const micIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>';
const stopIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';

const setRecording = (recording) => {
  isRecording = recording;

  recordTimer.hidden = !recording;
  recordingIndicator.hidden = !recording;
  dropZone.classList.toggle("recording", recording);

  if (recording) {
    recordButton.innerHTML = `${stopIconSVG}<span id="recordBtnLabel">Stop</span>`;
    recordButton.classList.add("recording-active");
  } else {
    recordButton.innerHTML = `${micIconSVG}<span id="recordBtnLabel">Record</span>`;
    recordButton.classList.remove("recording-active");
  }

  updateButtons();
};

const startRecording = async ({ fromHotkey = false } = {}) => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    if (fromHotkey && hotkeyStartCancelled) {
      stream.getTracks().forEach((track) => track.stop());
      hotkeyState = "idle";
      setHotkeyLock(false);
      return false;
    }

    audioChunks = [];
    recordingSeconds = 0;
    recordingOrigin = fromHotkey ? "hotkey" : "manual";
    hotkeyStopRequested = false;
    recordTimer.textContent = formatTime(0);

    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", () => {
      stream.getTracks().forEach((track) => track.stop());
      clearInterval(timerInterval);
      setRecording(false);

      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      const mimeUsed = mediaRecorder.mimeType || "audio/webm";
      const extMap = { "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".mp4", "audio/wav": ".wav" };
      const ext = Object.entries(extMap).find(([key]) => mimeUsed.startsWith(key))?.[1] ?? ".webm";
      const file = new File([blob], `recording${ext}`, { type: blob.type });

      selectFile(file);

      if (apiKeyInput.value.trim()) {
        if (recordingOrigin === "hotkey" || hotkeyStopRequested) {
          void runTranscription({ fromHotkey: true });
        } else {
          void runTranscription({ fromHotkey: false });
        }
      }
    });

    mediaRecorder.start(1000);
    setRecording(true);
    setStatus("Recording... click Stop when done.", { append: false });

    if (fromHotkey) {
      hotkeyState = "recording";
      hotkeyStartCancelled = false;
      if (desktopApi?.hotkey_recording_started) {
        try {
          await desktopApi.hotkey_recording_started();
        } catch {
          // Keep local recorder flow alive even if desktop callback briefly fails.
        }
      }
    }

    timerInterval = setInterval(() => {
      recordingSeconds += 1;
      recordTimer.textContent = formatTime(recordingSeconds);
    }, 1000);

    return true;
  } catch (error) {
    const message = error?.message || "Microphone access failed.";
    setStatus(`Microphone error: ${message}`, { append: false });
    if (fromHotkey) {
      hotkeyState = "idle";
    }
    if (fromHotkey && desktopApi?.hotkey_recording_failed) {
      await desktopApi.hotkey_recording_failed(message);
    }
    return false;
  }
};

const ensureMicrophonePermission = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
    return true;
  } catch (error) {
    const message = error?.message || "Microphone access is required for hotkey mode.";
    setStatus(`Microphone permission required: ${message}`, { append: false });
    return false;
  }
};
const setupDesktopBridge = async () => {
  if (desktopBridgeReady) return;
  if (!(window.pywebview && window.pywebview.api)) return;

  desktopApi = window.pywebview.api;
  desktopBridgeReady = true;

  hotkeyPanel.hidden = false;

  hotkeyToggle.addEventListener("change", async () => {
    if (!desktopApi?.set_hotkey_mode) return;

    const enabled = hotkeyToggle.checked;
    try {
      if (enabled) {
        const micOk = await ensureMicrophonePermission();
        if (!micOk) {
          hotkeyToggle.checked = false;
          hotkeyModeEnabled = false;
          await desktopApi.set_hotkey_mode(false);
          updateButtons();
          return;
        }
      }

      const result = await desktopApi.set_hotkey_mode(enabled);
      hotkeyModeEnabled = Boolean(result);
      hotkeyToggle.checked = hotkeyModeEnabled;

      if (!hotkeyModeEnabled) {
        hotkeyState = "idle";
        hotkeyStartCancelled = false;
        setHotkeyLock(false);
      }

      setStatus(
        hotkeyModeEnabled
          ? "Hotkey mode enabled. Minimize window to tray, then use F4 to record."
          : "Hotkey mode disabled.",
        { append: false },
      );
    } catch (error) {
      hotkeyToggle.checked = false;
      hotkeyModeEnabled = false;
      hotkeyState = "idle";
      hotkeyStartCancelled = false;
      setHotkeyLock(false);
      const message = error?.message || "Unable to toggle hotkey mode.";
      setStatus(`Hotkey error: ${message}`, { append: false });
    }
  });
};

window.desktopSetHotkeyLock = (locked) => {
  setHotkeyLock(Boolean(locked));
  return true;
};

window.desktopHotkeyStartRecording = async () => {
  if (!hotkeyModeEnabled) {
    return false;
  }
  if (isLoading) {
    return false;
  }

  // Self-heal stale state so subsequent F4 presses still start recording.
  if (hotkeyState !== "idle") {
    const recorderInactive = !mediaRecorder || mediaRecorder.state === "inactive";
    if (recorderInactive) {
      hotkeyState = "idle";
      hotkeyStopRequested = false;
      hotkeyStartCancelled = false;
      setHotkeyLock(false);
    } else {
      return false;
    }
  }

  if (!apiKeyInput.value.trim()) {
    const message = "Paste your OpenAI API key before using hotkey mode.";
    setStatus(message, { append: false });
    if (desktopApi?.hotkey_recording_failed) {
      await desktopApi.hotkey_recording_failed(message);
    }
    return false;
  }

  hotkeyState = "starting";
  hotkeyStartCancelled = false;
  setHotkeyLock(true);

  const started = await startRecording({ fromHotkey: true });
  if (!started && hotkeyState === "starting") {
    hotkeyState = "idle";
    setHotkeyLock(false);
  }
  return started;
};

window.desktopHotkeyCancelStartRecording = async () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    hotkeyState = "processing";
    hotkeyStopRequested = true;
    try {
      mediaRecorder.stop();
      return true;
    } catch {
      hotkeyState = "idle";
      setHotkeyLock(false);
      if (desktopApi?.hotkey_recording_failed) {
        await desktopApi.hotkey_recording_failed("Failed to stop in-progress recording.");
      }
      return false;
    }
  }

  if (hotkeyState !== "starting") {
    return false;
  }

  hotkeyStartCancelled = true;
  hotkeyState = "idle";
  setHotkeyLock(false);
  setStatus("Hotkey recording start canceled.", { append: false });
  return true;
};

window.desktopHotkeyStopAndTranscribe = async () => {
  if (!hotkeyModeEnabled || hotkeyState !== "recording" || !mediaRecorder || mediaRecorder.state === "inactive") {
    hotkeyStopRequested = false;
    hotkeyState = "idle";
    setHotkeyLock(false);
    if (desktopApi?.hotkey_recording_failed) {
      await desktopApi.hotkey_recording_failed("Recorder was not active when trying to stop.");
    }
    return false;
  }

  hotkeyState = "processing";
  hotkeyStopRequested = true;
  try {
    mediaRecorder.stop();
    return true;
  } catch (error) {
    hotkeyStopRequested = false;
    hotkeyState = "idle";
    setHotkeyLock(false);
    const message = error?.message || "Failed to stop recording.";
    setStatus(`Recording error: ${message}`, { append: false });
    if (desktopApi?.hotkey_recording_failed) {
      await desktopApi.hotkey_recording_failed(message);
    }
    return false;
  }
};

uploadButton.addEventListener("click", () => {
  if (!apiKeyInput.value.trim()) return;
  fileInput.click();
});

fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  selectFile(file);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  if (!isLoading && !isRecording && !hotkeyLockActive) {
    dropZone.classList.add("dragging");
  }
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");

  if (!apiKeyInput.value.trim()) {
    setStatus("Paste your OpenAI API key first.", { append: false });
    return;
  }

  if (isLoading || isRecording || hotkeyLockActive) {
    return;
  }

  const [file] = event.dataTransfer.files;
  selectFile(file);
});

apiKeyInput.addEventListener("input", () => {
  updateButtons();
});

toggleKey.addEventListener("click", () => {
  const isHidden = apiKeyInput.type === "password";
  apiKeyInput.type = isHidden ? "text" : "password";

  const eyeOpen = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeClosed = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
  toggleKey.innerHTML = (isHidden ? eyeClosed : eyeOpen) + (isHidden ? " Hide" : " Show");
});

transcribeButton.addEventListener("click", async () => {
  await runTranscription({ fromHotkey: false });
});

saveButton.addEventListener("click", () => {
  if (!transcriptText) return;
  const blob = new Blob([transcriptText], { type: "text/plain;charset=utf-8" });
  const anchor = document.createElement("a");
  const fileBase = selectedFile ? selectedFile.name.replace(/\.[^.]+$/, "") : "transcript";
  anchor.href = URL.createObjectURL(blob);
  anchor.download = `${fileBase || "transcript"}.txt`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(anchor.href);
});

copyButton.addEventListener("click", async () => {
  if (!transcriptText) return;

  const copyIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  const originalHTML = `${copyIconSVG} Copy transcript`;

  const copied = await copyTranscriptToClipboard();
  copyButton.innerHTML = copied ? "Copied!" : "Copy failed";
  setTimeout(() => {
    copyButton.innerHTML = originalHTML;
  }, 1200);
});

recordButton.addEventListener("click", async () => {
  if (isRecording) {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    return;
  }

  await startRecording({ fromHotkey: false });
});

window.addEventListener("pywebviewready", () => {
  void setupDesktopBridge();
});

void setupDesktopBridge();
updateButtons();

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

let selectedFile = null;
let transcriptText = "";
let mediaRecorder = null;
let audioChunks = [];
let timerInterval = null;
let recordingSeconds = 0;

const updateButtons = () => {
  const hasFile = Boolean(selectedFile);
  const hasKey = Boolean(apiKeyInput.value.trim());
  transcribeButton.disabled = !(hasFile && hasKey);
  saveButton.disabled = transcriptText.length === 0;
  copyButton.hidden = transcriptText.length === 0;
};

const resetTranscript = () => {
  transcriptText = "";
  transcriptOutput.textContent = "";
  transcriptSection.hidden = true;
  saveButton.disabled = true;
  copyButton.hidden = true;
};

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

const setLoading = (isLoading) => {
  transcribeButton.disabled = isLoading || !(selectedFile && apiKeyInput.value.trim());
  uploadButton.disabled = isLoading;
  apiKeyInput.disabled = isLoading;
  toggleKey.disabled = isLoading;
  recordButton.disabled = isLoading;
  dropZone.classList.toggle("dragging", isLoading);
  if (isLoading) {
    setStatus(["Uploading audio…", "Contacting OpenAI…"], { append: false });
  }
};

const selectFile = (file) => {
  if (!file) return;
  const supportedFormats = ['.wav', '.m4a', '.mp3', '.mp4', '.aac', '.flac', '.ogg', '.webm'];
  const fileExt = file.name.toLowerCase().match(/\.[^.]+$/)?.[0];
  if (!fileExt || !supportedFormats.includes(fileExt)) {
    setStatus(`Please upload a supported audio file: ${supportedFormats.join(', ')}`, { append: false });
    return;
  }
  selectedFile = file;
  fileName.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
  const conversionNote = fileExt === '.wav' ? '' : ' (will be converted to WAV)';
  setStatus(`Ready to transcribe ${file.name}${conversionNote}.`, { append: false });
  resetTranscript();
  updateButtons();
};

uploadButton.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  selectFile(file);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
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
  if (!selectedFile) {
    setStatus("Choose an audio file before transcribing.");
    return;
  }
  if (!apiKeyInput.value.trim()) {
    setStatus("Paste your OpenAI API key to continue.");
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
      } catch (parseError) {
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

    saveButton.disabled = transcriptText.length === 0;
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
  } finally {
    setLoading(false);
    updateButtons();
  }
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

copyButton.addEventListener("click", () => {
  if (!transcriptText) return;
  const copyIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  const originalHTML = copyIconSVG + " Copy transcript";
  navigator.clipboard.writeText(transcriptText).then(() => {
    copyButton.innerHTML = "✅ Copied!";
    setTimeout(() => { copyButton.innerHTML = originalHTML; }, 1500);
  }).catch(() => {
    const range = document.createRange();
    range.selectNodeContents(transcriptOutput);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    document.execCommand("copy");
    sel.removeAllRanges();
    copyButton.innerHTML = "✅ Copied!";
    setTimeout(() => { copyButton.innerHTML = originalHTML; }, 1500);
  });
});

const formatTime = (seconds) => {
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
};

const micIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>';
const stopIconSVG = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';

let isRecording = false;

const setRecording = (recording) => {
  isRecording = recording;
  uploadButton.disabled = recording;
  transcribeButton.disabled = recording || !(selectedFile && apiKeyInput.value.trim());
  recordTimer.hidden = !recording;
  recordingIndicator.hidden = !recording;
  dropZone.classList.toggle("recording", recording);

  if (recording) {
    recordButton.innerHTML = stopIconSVG + '<span id="recordBtnLabel">Stop</span>';
    recordButton.classList.add("recording-active");
  } else {
    recordButton.innerHTML = micIconSVG + '<span id="recordBtnLabel">Record</span>';
    recordButton.classList.remove("recording-active");
  }
};

recordButton.addEventListener("click", async () => {
  if (isRecording) {
    // Stop recording
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    return;
  }

  // Start recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    recordingSeconds = 0;
    recordTimer.textContent = formatTime(0);

    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener("stop", () => {
      stream.getTracks().forEach((track) => track.stop());
      clearInterval(timerInterval);
      setRecording(false);

      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      const mimeUsed = mediaRecorder.mimeType || "audio/webm";
      const extMap = { "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".mp4", "audio/wav": ".wav" };
      const ext = Object.entries(extMap).find(([k]) => mimeUsed.startsWith(k))?.[1] ?? ".webm";
      const file = new File([blob], `recording${ext}`, { type: blob.type });
      selectFile(file);

      if (apiKeyInput.value.trim()) {
        transcribeButton.click();
      }
    });

    mediaRecorder.start(1000);
    setRecording(true);
    setStatus("Recording… click Stop when done.", { append: false });

    timerInterval = setInterval(() => {
      recordingSeconds += 1;
      recordTimer.textContent = formatTime(recordingSeconds);
    }, 1000);
  } catch (err) {
    setStatus(`Microphone error: ${err.message}`, { append: false });
  }
});

updateButtons();

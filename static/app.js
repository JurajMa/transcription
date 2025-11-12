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

let selectedFile = null;
let transcriptText = "";

const updateButtons = () => {
  const hasFile = Boolean(selectedFile);
  const hasKey = Boolean(apiKeyInput.value.trim());
  transcribeButton.disabled = !(hasFile && hasKey);
  saveButton.disabled = transcriptText.length === 0;
};

const resetTranscript = () => {
  transcriptText = "";
  transcriptOutput.textContent = "";
  transcriptSection.hidden = true;
  saveButton.disabled = true;
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
  dropZone.classList.toggle("dragging", isLoading);
  if (isLoading) {
    setStatus(["Uploading audio…", "Contacting OpenAI…"], { append: false });
  }
};

const selectFile = (file) => {
  if (!file) return;
  const supportedFormats = ['.wav', '.m4a', '.mp3', '.mp4', '.aac', '.flac', '.ogg'];
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
  toggleKey.textContent = isHidden ? "Hide" : "Show";
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

updateButtons();

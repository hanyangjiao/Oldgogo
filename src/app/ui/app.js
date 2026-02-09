const rootPath = new URL("../../../", window.location.href);

const elements = {
  systemStatus: document.getElementById("systemStatus"),
  videoSelect: document.getElementById("videoSelect"),
  hrSelect: document.getElementById("hrSelect"),
  addPairButton: document.getElementById("addPairButton"),
  startButton: document.getElementById("startButton"),
  clearPairsButton: document.getElementById("clearPairsButton"),
  pairQueue: document.getElementById("pairQueue"),
  pairCount: document.getElementById("pairCount"),
  controlStatus: document.getElementById("controlStatus"),
  downloadButton: document.getElementById("downloadButton"),
  caseBadge: document.getElementById("caseBadge"),
  caseClock: document.getElementById("caseClock"),
  caseVideo: document.getElementById("caseVideo"),
  bpmValue: document.getElementById("bpmValue"),
  bpmStatus: document.getElementById("bpmStatus"),
  signalQuality: document.getElementById("signalQuality"),
  syncWindow: document.getElementById("syncWindow"),
  reportStage: document.getElementById("reportStage"),
  reportProgress: document.getElementById("reportProgress"),
  inputText: document.getElementById("inputText"),
  windowText: document.getElementById("windowText"),
  tasksText: document.getElementById("tasksText"),
  anomalyText: document.getElementById("anomalyText"),
  notificationText: document.getElementById("notificationText"),
  humanText: document.getElementById("humanText"),
  reportJson: document.getElementById("reportJson"),
  streamLog: document.getElementById("streamLog"),
  emailPreview: document.getElementById("emailPreview"),
  emailStatus: document.getElementById("emailStatus")
};

const pipelineSteps = new Map();
Array.from(document.querySelectorAll(".pipeline-step")).forEach((el) => {
  pipelineSteps.set(el.dataset.step, el);
});

const canvas = document.getElementById("hrCanvas");
const ctx = canvas.getContext("2d");

let samples = [];
let hrSeries = [];
let hrIndex = 0;
let hrState = {
  targetBpm: 72,
  currentBpm: 72,
  variance: 6
};
let caseStart = null;
let inferenceToken = 0;
let progressTimer = null;
let progressValue = 0;
let options = {
  videos: [],
  hrTypes: []
};
let selection = {
  video: null,
  hrType: null
};
let pairQueue = [];
let queueResults = [];
let audioContext = null;

function initAudioContext() {
  if (audioContext) return;
  const AudioCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtor) return;
  audioContext = new AudioCtor();
}

async function playAlertTone() {
  if (!audioContext) return;
  if (audioContext.state === "suspended") {
    try {
      await audioContext.resume();
    } catch (error) {
      return;
    }
  }

  const now = audioContext.currentTime;
  const tones = [0, 0.22, 0.44];
  tones.forEach((offset) => {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0, now + offset);
    gain.gain.linearRampToValueAtTime(0.2, now + offset + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.18);
    osc.connect(gain);
    gain.connect(audioContext.destination);
    osc.start(now + offset);
    osc.stop(now + offset + 0.2);
  });
}

function hasAnomalyMatch(report) {
  if (!report || !Array.isArray(report.anomalies)) return false;
  return report.anomalies.some((anom) => anom && anom.match);
}

function speakAlert(text) {
  if (!("speechSynthesis" in window)) return false;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
  return true;
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * ratio;
  canvas.height = canvas.clientHeight * ratio;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(ratio, ratio);
}

function resetSamples() {
  const count = Math.floor(canvas.clientWidth / 3);
  samples = Array.from({ length: count }, () => 0);
}

function pushStreamLine(text) {
  const line = document.createElement("div");
  line.className = "stream-line";
  line.textContent = text;
  elements.streamLog.appendChild(line);
  elements.streamLog.scrollTop = elements.streamLog.scrollHeight;
}

function setPipeline(step, state) {
  const el = pipelineSteps.get(step);
  if (!el) return;
  el.classList.remove("active", "done");
  if (state === "active") {
    el.classList.add("active");
  }
  if (state === "done") {
    el.classList.add("done");
  }
}

function resetPipeline() {
  pipelineSteps.forEach((el) => {
    el.classList.remove("active", "done");
  });
}

function setSystemStatus(text) {
  const label = elements.systemStatus.querySelector("span:last-child");
  if (label) label.textContent = text;
}

function setControlStatus(text) {
  elements.controlStatus.textContent = text;
}

function setControlsDisabled(disabled) {
  elements.videoSelect.disabled = disabled;
  elements.hrSelect.disabled = disabled;
  elements.addPairButton.disabled = disabled;
  elements.startButton.disabled = disabled;
  elements.clearPairsButton.disabled = disabled;
}

function setReportLoading() {
  [
    elements.inputText,
    elements.windowText,
    elements.tasksText,
    elements.anomalyText,
    elements.notificationText,
    elements.humanText
  ].forEach((el) => {
    el.textContent = "";
    el.classList.add("loading");
  });
  elements.reportJson.textContent = "";
  elements.reportProgress.style.width = "0%";
  elements.reportStage.textContent = "Waiting";
  elements.streamLog.innerHTML = "";
  elements.downloadButton.disabled = true;
}

function clearReportLoading() {
  [
    elements.inputText,
    elements.windowText,
    elements.tasksText,
    elements.anomalyText,
    elements.notificationText,
    elements.humanText
  ].forEach((el) => {
    el.classList.remove("loading");
  });
}

function updateReportProgress(value, label) {
  elements.reportProgress.style.width = `${value}%`;
  elements.reportStage.textContent = label;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function typeText(el, text, token, speed) {
  el.classList.remove("loading");
  el.textContent = "";
  for (let i = 0; i < text.length; i += 1) {
    if (token !== inferenceToken) return;
    el.textContent = text.slice(0, i + 1);
    await delay(speed);
  }
}

function formatSeconds(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function applyHeartRateSeries(series, label) {
  hrSeries = Array.isArray(series) ? series : [];
  hrIndex = 0;
  if (hrSeries.length > 0) {
    hrState.currentBpm = Math.round(hrSeries[0].bpm);
    hrState.targetBpm = hrState.currentBpm;
    elements.signalQuality.textContent = label || "Generated";
    elements.syncWindow.textContent = `00:00 / ${formatSeconds(hrSeries.length)}`;
  } else {
    elements.signalQuality.textContent = "Awaiting generation";
    elements.syncWindow.textContent = "00:00 / 00:00";
  }
  updateBpm(true);
}

function applyHeartRateTypeSelection(option) {
  if (!option) return;
  hrState.targetBpm = option.base_bpm;
  hrState.currentBpm = option.base_bpm;
  hrState.variance = option.jitter;
  applyHeartRateSeries([], "Awaiting generation");
}

function updateBpm(force = false) {
  let bpm = hrState.currentBpm;

  if (hrSeries.length > 0) {
    const total = hrSeries.length;
    const currentIndex = hrIndex;
    const point = hrSeries[hrIndex];
    hrIndex = (hrIndex + 1) % total;
    bpm = Math.round(point.bpm);
    hrState.currentBpm = bpm;
    hrState.targetBpm = bpm;
    elements.syncWindow.textContent = `${formatSeconds(
      currentIndex
    )} / ${formatSeconds(total)}`;
  } else if (!force) {
    const variance = Math.random() * hrState.variance * 2 - hrState.variance;
    bpm = Math.round(hrState.targetBpm + variance);
    hrState.currentBpm = bpm;
  }

  elements.bpmValue.textContent = `${bpm} BPM`;

  let status = "Normal";
  let statusClass = "status-normal";
  if (bpm < 60) {
    status = "Bradycardia";
    statusClass = "status-brady";
  } else if (bpm > 110) {
    status = "Tachycardia";
    statusClass = "status-tachy";
  } else if (bpm > 90) {
    status = "Elevated";
    statusClass = "status-elevated";
  }

  elements.bpmStatus.className = `badge badge-outline ${statusClass}`;
  elements.bpmStatus.textContent = status;
}

function generatePulse(time, bpm) {
  const beat = ((time * bpm) / 60) % 1;
  let value = 0;
  if (beat < 0.08) {
    value = Math.sin((beat / 0.08) * Math.PI) * 1.4;
  } else if (beat < 0.16) {
    value = -0.4 + (beat - 0.08) * 5;
  } else {
    value = 0.05 * Math.sin(beat * Math.PI * 6);
  }
  value += (Math.random() - 0.5) * 0.08;
  return value;
}

function drawWave(time) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(110, 231, 194, 0.25)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();

  const sample = generatePulse(time, hrState.currentBpm);
  samples.push(sample);
  samples.shift();

  ctx.strokeStyle = "#6ee7c2";
  ctx.lineWidth = 2;
  ctx.beginPath();
  samples.forEach((value, index) => {
    const x = (index / (samples.length - 1)) * width;
    const y = height / 2 - value * 40;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "rgba(110, 231, 194, 0.12)";
  ctx.lineTo(width, height / 2);
  ctx.lineTo(0, height / 2);
  ctx.closePath();
  ctx.fill();
}

function animate(now) {
  drawWave(now / 1000);
  requestAnimationFrame(animate);
}

function updateClock() {
  if (!caseStart) {
    elements.caseClock.textContent = "00:00";
    return;
  }
  const elapsed = Math.floor((Date.now() - caseStart) / 1000);
  const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const seconds = String(elapsed % 60).padStart(2, "0");
  elements.caseClock.textContent = `${minutes}:${seconds}`;
}

function populateSelect(select, items) {
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label;
    select.appendChild(option);
  });
}

function applyVideoSelection(option) {
  if (!option) return;
  elements.caseBadge.textContent = option.label;
  elements.caseVideo.src = new URL(option.path, rootPath).toString();
  elements.caseVideo.play().catch(() => {
    elements.reportStage.textContent = "Click video to play";
  });
}

function renderPairQueue() {
  elements.pairQueue.innerHTML = "";
  elements.pairCount.textContent = `${pairQueue.length} pairs queued`;
  if (pairQueue.length === 0) {
    return;
  }

  pairQueue.forEach((pair, index) => {
    const item = document.createElement("div");
    item.className = "pair-item";

    const label = document.createElement("span");
    label.className = "pair-label";
    label.textContent = `${pair.video.label} · ${pair.hrType.label}`;

    const remove = document.createElement("button");
    remove.className = "pair-remove";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      pairQueue = pairQueue.filter((_, idx) => idx !== index);
      renderPairQueue();
    });

    item.appendChild(label);
    item.appendChild(remove);
    elements.pairQueue.appendChild(item);
  });
}

function addPairToQueue() {
  if (!selection.video || !selection.hrType) {
    pushStreamLine("Select a video and heart rate type before adding.");
    return;
  }
  pairQueue = [
    ...pairQueue,
    {
      video: selection.video,
      hrType: selection.hrType
    }
  ];
  renderPairQueue();
}

function clearPairQueue() {
  pairQueue = [];
  renderPairQueue();
}

async function loadOptions() {
  try {
    const response = await fetch("/api/options");
    if (!response.ok) {
      throw new Error("Failed to load options");
    }
    const data = await response.json();
    options = {
      videos: data.videos || [],
      hrTypes: data.hr_types || []
    };

    if (options.hrTypes.length === 0) {
      if (data.heart_rates) {
        setSystemStatus("Server mismatch");
        pushStreamLine(
          "Server is running an older API. Restart ./scripts/run_ui.sh to enable heart rate types."
        );
      } else {
        setSystemStatus("No heart rate types");
        pushStreamLine("No heart rate types were returned by the server.");
      }
    }

    populateSelect(elements.videoSelect, options.videos);
    populateSelect(elements.hrSelect, options.hrTypes);

    selection.video = options.videos[0] || null;
    selection.hrType = options.hrTypes[0] || null;

    if (selection.video) {
      elements.videoSelect.value = selection.video.id;
      applyVideoSelection(selection.video);
    }
    if (selection.hrType) {
      elements.hrSelect.value = selection.hrType.id;
      applyHeartRateTypeSelection(selection.hrType);
    }
  } catch (error) {
    setSystemStatus("Options unavailable");
    pushStreamLine("Failed to load options from server.");
  }
}

async function loadLatestEmail() {
  if (!elements.emailPreview) return;
  try {
    const response = await fetch("/api/latest-email");
    if (!response.ok) {
      throw new Error("Failed to load email preview");
    }
    const data = await response.json();
    let body = data.body || "No email generated yet.";
    if (body.startsWith("To:")) {
      body = body.split("\n").slice(1).join("\n").trimStart();
    }
    elements.emailPreview.textContent = body;
    if (elements.emailStatus) {
      elements.emailStatus.textContent = data.ok ? "Available" : "No email";
    }
  } catch (error) {
    elements.emailPreview.textContent = "No email generated yet.";
    if (elements.emailStatus) {
      elements.emailStatus.textContent = "Unavailable";
    }
    pushStreamLine("Failed to load latest email preview.");
  }
}

function formatInputSummary(input) {
  if (!input) return "";
  const hrLabel = input.hr_type_label
    ? `${input.hr_type_label} (base ${input.hr_base_bpm}, jitter ${input.hr_jitter})`
    : "Unknown";
  return [
    `Video: ${input.video_label || input.video_file}`,
    `Heart rate type: ${hrLabel}`,
    `Frames: ${input.frame_count}`,
    `HR points: ${input.heart_rate_points}`
  ].join("\n");
}

function formatWindow(report, input) {
  if (report && report.window) {
    return `${report.window.start_time} → ${report.window.end_time}`;
  }
  if (input) {
    return `${input.window_start} → ${input.window_end}`;
  }
  return "";
}

function formatTasks(report) {
  if (!report || !Array.isArray(report.tasks)) return "No task data.";
  if (report.tasks.length === 0) return "No tasks detected.";
  return report.tasks
    .map((task) => {
      const status = task.match ? "match" : "no match";
      return `- ${task.type}: ${status}. ${task.reason}`;
    })
    .join("\n");
}

function formatAnomalies(report) {
  if (!report || !Array.isArray(report.anomalies)) return "No anomaly data.";
  const matches = report.anomalies.filter((anom) => anom.match);
  if (matches.length === 0) return "No anomalies detected.";
  return matches.map((anom) => `- ${anom.type}: ${anom.reason}`).join("\n");
}

function formatNotifications(report) {
  const note = report ? report.notifications : null;
  if (!note) return "No notification data.";
  const repeated = Array.isArray(note.non_repeatable_violations)
    ? note.non_repeatable_violations
    : [];
  return [
    `Voice reminder: ${note.voice_reminder ? "Yes" : "No"}`,
    `Non-repeatable repeated: ${repeated.length > 0 ? repeated.join(", ") : "No"}`,
    `Email sent: ${note.email_sent ? "Yes" : "No"}`,
    `Cooldown active: ${note.cooldown_active ? "Yes" : "No"}`
  ].join("\n");
}

function formatHumanReport(payload) {
  if (!payload || !payload.human_report) {
    return "No human summary available.";
  }
  return payload.human_report;
}

async function loadLatestHumanSummary() {
  try {
    const response = await fetch("/api/latest-report");
    if (!response.ok) {
      throw new Error("Failed to load latest report");
    }
    const data = await response.json();
    if (!data.ok || !data.data) {
      return "No human summary available.";
    }
    return data.data.latest_human_report || "No human summary available.";
  } catch (error) {
    return "No human summary available.";
  }
}

function startProgressLoop(token) {
  if (progressTimer) {
    clearInterval(progressTimer);
  }
  resetPipeline();
  progressValue = 6;
  const steps = [
    { key: "sync", label: "Syncing inputs", log: "Preparing input window." },
    { key: "vision", label: "Scanning frames", log: "Estimating frame window." },
    { key: "vitals", label: "Generating heart rate", log: "Generating HR data." },
    { key: "prompt", label: "Uploading to Gemini", log: "Uploading video to Gemini." },
    { key: "report", label: "Waiting for response", log: "Awaiting Gemini output." }
  ];
  let stepIndex = 0;
  setPipeline(steps[stepIndex].key, "active");
  updateReportProgress(progressValue, steps[stepIndex].label);
  pushStreamLine(steps[stepIndex].log);

  progressTimer = setInterval(() => {
    if (token !== inferenceToken) return;
    progressValue = Math.min(progressValue + 4, 90);
    if (progressValue >= (stepIndex + 1) * 18 && stepIndex < steps.length - 1) {
      setPipeline(steps[stepIndex].key, "done");
      stepIndex += 1;
      setPipeline(steps[stepIndex].key, "active");
      updateReportProgress(progressValue, steps[stepIndex].label);
      pushStreamLine(steps[stepIndex].log);
    } else {
      updateReportProgress(progressValue, steps[stepIndex].label);
    }
  }, 700);
}

function stopProgressLoop() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

async function renderReport(report, input, token, payload) {
  elements.reportJson.textContent = JSON.stringify(report, null, 2);
  const inputText = formatInputSummary(input);
  const windowText = formatWindow(report, input);
  const tasksText = formatTasks(report);
  const anomalyText = formatAnomalies(report);
  const notificationText = formatNotifications(report);
  const humanText = await loadLatestHumanSummary();

  updateReportProgress(94, "Streaming report");

  await typeText(elements.inputText, inputText, token, 6);
  await typeText(elements.windowText, windowText, token, 6);
  await typeText(elements.tasksText, tasksText, token, 4);
  await typeText(elements.anomalyText, anomalyText, token, 4);
  await typeText(elements.notificationText, notificationText, token, 4);
  await typeText(elements.humanText, humanText, token, 4);

  if (token !== inferenceToken) return;
  setPipeline("report", "done");
  updateReportProgress(100, "Report complete");
  elements.reportStage.textContent = "Report complete";
  pushStreamLine("Report validated against schema.");
}

function makePairsToRun() {
  if (pairQueue.length > 0) {
    return pairQueue.map((pair) => ({ ...pair }));
  }
  if (selection.video && selection.hrType) {
    return [{ video: selection.video, hrType: selection.hrType }];
  }
  return [];
}

async function runInferenceQueue(pairs) {
  if (pairs.length === 0) {
    pushStreamLine("Select a video and heart rate type first.");
    return;
  }

  inferenceToken += 1;
  const token = inferenceToken;
  queueResults = [];
  elements.downloadButton.disabled = true;
  setSystemStatus("Gemini running");
  setControlStatus(`Running ${pairs.length} task(s)`);
  setControlsDisabled(true);

  try {
    await fetch("/api/reset", { method: "POST" });
  } catch (error) {
    pushStreamLine("Failed to reset session state.");
  }

  for (let i = 0; i < pairs.length; i += 1) {
    if (token !== inferenceToken) return;
    const pair = pairs[i];

    elements.reportStage.textContent = `Running ${i + 1} / ${pairs.length}`;
    setControlStatus(`Running ${i + 1} / ${pairs.length}`);

    selection.video = pair.video;
    selection.hrType = pair.hrType;
    elements.videoSelect.value = pair.video.id;
    elements.hrSelect.value = pair.hrType.id;

    applyVideoSelection(pair.video);
    applyHeartRateTypeSelection(pair.hrType);

    caseStart = Date.now();
    setReportLoading();
    startProgressLoop(token);
    pushStreamLine(
      `Inference ${i + 1}/${pairs.length}: ${pair.video.label} · ${pair.hrType.label}`
    );

    try {
      const response = await fetch("/api/infer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: pair.video.id,
          hr_type: pair.hrType.id
        })
      });
      const payload = await response.json();

      if (token !== inferenceToken) return;

      stopProgressLoop();
      setPipeline("prompt", "done");
      setPipeline("report", "active");

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Inference failed");
      }

      pushStreamLine("Gemini response received.");
      let alertPlayed = false;
      if (payload.report?.notifications?.voice_reminder) {
        await playAlertTone();
        alertPlayed = true;
        pushStreamLine("Voice reminder triggered: alert tone played.");
      }
      if (Array.isArray(payload.non_repeatable_violations) && payload.non_repeatable_violations.length > 0) {
        if (!alertPlayed) {
          await playAlertTone();
          alertPlayed = true;
        }
        speakAlert("Task already completed and should not be repeated.");
        pushStreamLine(
          `Non-repeatable task repeated: ${payload.non_repeatable_violations.join(", ")}`
        );
      }
      if (hasAnomalyMatch(payload.report)) {
        const spoke = speakAlert("Anomaly is detected");
        if (!spoke && !alertPlayed) {
          await playAlertTone();
          alertPlayed = true;
        }
        pushStreamLine("Anomaly detected: voice alert issued.");
      }
      applyHeartRateSeries(payload.heart_rate_series, "Generated");
      queueResults.push(payload);
      await renderReport(payload.report, payload.input, token, payload);
      await loadLatestEmail();
    } catch (error) {
      stopProgressLoop();
      resetPipeline();
      elements.reportStage.textContent = "Error";
      clearReportLoading();
      elements.inputText.textContent = "Inference failed. See log for details.";
      pushStreamLine(`Error: ${error.message || error}`);
      break;
    }
  }

  if (token === inferenceToken) {
    setControlsDisabled(false);
    setControlStatus("Idle");
    setSystemStatus("System ready");
    if (queueResults.length === pairs.length) {
      elements.downloadButton.disabled = false;
      pushStreamLine("Queue complete. Report ready for download.");
    } else {
      pushStreamLine("Queue stopped before completion. Report not generated.");
    }
  }
}

function buildDownloadText(results) {
  if (!Array.isArray(results) || results.length === 0) return "";
  const latest = results[results.length - 1] || {};
  const lines = [];
  lines.push("Oldgogo - Human Readable Report");
  lines.push(`Generated: ${new Date().toISOString()}`);
  lines.push("");
  lines.push(latest.human_report || "No human summary available.");
  return lines.join("\n");
}

function downloadReport() {
  if (!Array.isArray(queueResults) || queueResults.length === 0) return;
  const timestamp = new Date().toISOString();
  const safeStamp = timestamp.replace(/[:]/g, "-");
  const filename = `analysis_report_queue_${safeStamp}.txt`;
  const data = buildDownloadText(queueResults);
  const blob = new Blob([data], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function attachHandlers() {
  elements.videoSelect.addEventListener("change", (event) => {
    selection.video = options.videos.find((item) => item.id === event.target.value);
    applyVideoSelection(selection.video);
  });

  elements.hrSelect.addEventListener("change", (event) => {
    selection.hrType = options.hrTypes.find((item) => item.id === event.target.value);
    applyHeartRateTypeSelection(selection.hrType);
  });

  elements.addPairButton.addEventListener("click", () => {
    addPairToQueue();
  });

  elements.clearPairsButton.addEventListener("click", () => {
    clearPairQueue();
  });

  elements.startButton.addEventListener("click", () => {
    initAudioContext();
    runInferenceQueue(makePairsToRun());
  });

  elements.downloadButton.addEventListener("click", () => {
    downloadReport();
  });
}

function init() {
  resizeCanvas();
  resetSamples();
  window.addEventListener("resize", () => {
    resizeCanvas();
    resetSamples();
  });

  if (window.location.protocol === "file:") {
    setSystemStatus("Open via server");
    pushStreamLine("Open http://localhost:8000/src/app/ui/ after running ./scripts/run_ui.sh");
  }

  attachHandlers();
  renderPairQueue();
  loadOptions();
  loadLatestEmail();
  updateBpm(true);
  setInterval(updateClock, 1000);
  setInterval(updateBpm, 1000);
  requestAnimationFrame(animate);
}

init();

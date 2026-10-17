/* Med Assistant - front-end logic.
 * Talks to the FastAPI backend; speaks results with the browser voice today
 * (swappable for Bulbul server-side). No framework, plain DOM. */
"use strict";

const $ = (id) => document.getElementById(id);
const state = { mode: null, stream: null, lastSpoken: "", mock: true };
const VOICE = { rec: null, on: false, want: false };

const MODE_META = {
  patient:  { heading: "Patient", show: ["verify", "ask", "logpanel"], voice: true },
  caretaker:{ heading: "Caretaker / Nurse", show: ["verify", "logpanel"], voice: false },
  quick:    { heading: "Quick read", show: [], voice: false },
};

/* ---------- boot ---------- */
async function boot() {
  try {
    const h = await (await fetch("/api/health")).json();
    const pill = $("mode-pill");
    state.mock = !!h.mock;
    if (h.mock) { pill.textContent = "Mock mode (no keys)"; pill.className = "pill pill-mock"; }
    else { pill.textContent = "Live: Sarvam"; pill.className = "pill pill-live"; }
    $("footer-models").textContent =
      `Sarvam Vision · ${h.models.chat} · Bulbul · Saaras`;
  } catch (e) { /* offline is fine */ }

  document.querySelectorAll(".mode-card").forEach((c) =>
    c.addEventListener("click", () => enterMode(c.dataset.mode)));
  $("back").addEventListener("click", leaveMode);

  $("btn-camera").addEventListener("click", startCamera);
  $("btn-stopcam").addEventListener("click", stopCamera);
  $("btn-capture").addEventListener("click", captureFrame);
  $("file").addEventListener("change", (e) => { if (e.target.files[0]) scanFile(e.target.files[0]); });
  setupDrop();

  $("btn-replay").addEventListener("click", () => speak(state.lastSpoken));
  $("btn-ask").addEventListener("click", askText);
  $("btn-mic").addEventListener("click", askVoice);
  $("btn-logadd").addEventListener("click", addLog);
  buildScenarioButtons();
  refreshUsage();

  // Voice control (optional layer; all clicks keep working without it).
  $("voice-toggle").addEventListener("click", toggleVoice);
  document.addEventListener("keydown", (e) => {
    const typing = /^(input|textarea|select)$/i.test((e.target.tagName || ""));
    if (!typing && (e.key === "v" || e.key === "V")) { e.preventDefault(); toggleVoice(); }
  });
}

/* ---------- voice control ---------- */
// Live navigation uses the browser's speech recognition (instant, no credits).
// At the event, voice *questions* can additionally route through Sarvam Saaras
// via /api/transcribe; see askVoice(). All of this is additive — buttons remain.
function supportsSR() {
  return "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
}
function toggleVoice() {
  if (VOICE.want || VOICE.on) stopVoice(); else startVoice();
}
function startVoice() {
  if (!supportsSR()) { setStatus("Voice control is not supported in this browser."); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new SR();
  VOICE.rec = rec; VOICE.want = true;
  rec.lang = "en-IN";              // commands are short English keywords -> robust
  rec.continuous = true;
  rec.interimResults = false;
  rec.onstart = () => { VOICE.on = true; paintVoice(true); speak(voicePrompt()); };
  rec.onresult = (e) => routeCommand(e.results[e.results.length - 1][0].transcript.toLowerCase());
  rec.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      VOICE.want = false; paintVoice(false);
      const msg = "Microphone is blocked. Please allow mic access, or use the buttons.";
      setStatus(msg);
      const hint = $("voice-hint");
      if (hint) { hint.textContent = msg; hint.classList.remove("hidden"); }
      speak(msg);
    }
  };
  rec.onend = () => {
    VOICE.on = false;
    if (VOICE.want) { try { rec.start(); } catch (_) {} } else paintVoice(false);
  };
  try { rec.start(); } catch (_) {}
}
function stopVoice() {
  VOICE.want = false;
  if (VOICE.rec) { try { VOICE.rec.stop(); } catch (_) {} }
  paintVoice(false);
}
function paintVoice(on) {
  const b = $("voice-toggle");
  b.classList.toggle("on", on);
  b.setAttribute("aria-pressed", on ? "true" : "false");
  $("voice-label").textContent = on ? "Listening…" : "Voice off";
  syncVoiceHint();
}
function syncVoiceHint() {
  const hint = $("voice-hint");
  if (!hint) return;
  const show = VOICE.on && !state.mode;
  if (show) hint.textContent = "Voice control is on. Say “patient”, “nurse”, or “general”.";
  hint.classList.toggle("hidden", !show);
}
function voicePrompt() {
  return state.mode ? "" : "Say patient, nurse, or general user.";
}
// Exposed so the routing can be unit-checked without a microphone.
function routeCommand(t) {
  if (/\b(patient|blind|रोगी|రోగి)\b/.test(t)) { enterMode("patient"); speak("Patient mode."); return "patient"; }
  if (/\b(nurse|caretaker|care\s?taker|care|नर्स|నర్స్)\b/.test(t)) { enterMode("caretaker"); speak("Caretaker mode."); return "caretaker"; }
  if (/\b(general|common|normal|quick|read|सामान्य|సాధారణ)\b/.test(t)) { enterMode("quick"); speak("Quick read."); return "quick"; }
  if (/\b(back|change user|menu|home)\b/.test(t)) { leaveMode(); speak("Main menu."); return "back"; }
  if (/\b(again|repeat|play)\b/.test(t)) { speak(state.lastSpoken); return "repeat"; }
  return null;
}
window.routeCommand = routeCommand;   // for verification

/* ---------- mode switching ---------- */
function enterMode(mode) {
  state.mode = mode;
  const meta = MODE_META[mode];
  $("chooser").classList.add("hidden");
  $("workspace").classList.remove("hidden");
  $("mode-heading").textContent = meta.heading;
  ["verify", "ask", "logpanel"].forEach((p) =>
    $(p).classList.toggle("hidden", !meta.show.includes(p)));
  $("rx-result").classList.add("hidden");
  refreshLog();
  syncVoiceHint();
}
function leaveMode() {
  stopCamera();
  state.mode = null;
  $("workspace").classList.add("hidden");
  $("chooser").classList.remove("hidden");
  syncVoiceHint();
}

/* ---------- camera + file ---------- */
async function startCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    const cam = $("cam");
    cam.srcObject = state.stream;
    cam.classList.remove("hidden");
    $("droparea").classList.add("hidden");
    $("cam-controls").classList.remove("hidden");
    if (MODE_META[state.mode].voice) speak("Hold the prescription flat in front of the camera, then press capture.");
  } catch (e) { setStatus("Camera not available. Use Choose file instead."); }
}
function stopCamera() {
  if (state.stream) { state.stream.getTracks().forEach((t) => t.stop()); state.stream = null; }
  $("cam").classList.add("hidden");
  $("cam-controls").classList.add("hidden");
  $("droparea").classList.remove("hidden");
}
function captureFrame() {
  const cam = $("cam"), snap = $("snap");
  snap.width = cam.videoWidth || 1280;
  snap.height = cam.videoHeight || 720;
  snap.getContext("2d").drawImage(cam, 0, 0, snap.width, snap.height);
  snap.toBlob((blob) => { stopCamera(); scanFile(new File([blob], "capture.png", { type: "image/png" })); }, "image/png");
}
function setupDrop() {
  const d = $("droparea");
  d.addEventListener("click", () => $("file").click());
  ["dragover", "dragenter"].forEach((ev) =>
    d.addEventListener(ev, (e) => { e.preventDefault(); d.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    d.addEventListener(ev, (e) => { e.preventDefault(); d.classList.remove("drag"); }));
  d.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) scanFile(e.dataTransfer.files[0]); });
}

/* ---------- scan prescription ---------- */
async function scanFile(file) {
  setStatus("Reading the prescription…");
  const fd = new FormData();
  fd.append("file", file);
  fd.append("language", $("language").value);
  fd.append("content_type", "handwritten");
  try {
    const r = await (await fetch("/api/scan", { method: "POST", body: fd })).json();
    setStatus("");
    renderRx(r.prescription, r.spoken_text);
    refreshUsage();
  } catch (e) { setStatus("Could not read. Please try again."); }
}
function renderRx(rx, spoken) {
  $("rx-result").classList.remove("hidden");
  $("spoken").textContent = spoken;
  const rows = [`<tr><th>Medicine</th><th>Strength</th><th>When</th><th>Days</th><th></th></tr>`];
  rx.medicines.forEach((m) => {
    const when = m.dose.prn ? "as needed" : (m.dose.times.join(", ") || "—") +
      (m.dose.food ? ` (${m.dose.food} food)` : "");
    const tag = m.matched ? `<span class="tag tag-ok">matched</span>`
                          : `<span class="tag tag-low">check</span>`;
    rows.push(`<tr><td>${esc(m.name)}</td><td>${esc(m.strength || "—")}</td>
      <td>${esc(when)}</td><td>${m.dose.days || "—"}</td><td>${tag}</td></tr>`);
  });
  $("med-table").innerHTML = rows.join("");
  state.lastSpoken = spoken;
  if (MODE_META[state.mode].voice) speak(spoken);
}

/* ---------- verify a strip ---------- */
function buildScenarioButtons() {
  // In mock mode the strip image is ignored, so we expose the four demo cases.
  const defs = [
    ["match", "Tablet on the list"],
    ["not_on_list", "Not on the list"],
    ["expired", "Expired strip"],
    ["unreadable", "Cannot read"],
  ];
  $("scenario-row").innerHTML = "";
  defs.forEach(([sc, label]) => {
    const b = document.createElement("button");
    b.className = "btn btn-ghost";
    b.textContent = label;
    b.addEventListener("click", () => checkStrip(sc));
    $("scenario-row").appendChild(b);
  });
}
async function checkStrip(scenario) {
  const fd = new FormData();
  fd.append("language", $("language").value);
  fd.append("scenario", scenario);
  const r = await (await fetch("/api/strip", { method: "POST", body: fd })).json();
  const map = { on_list: ["v-ok", "On your prescription"], not_on_list: ["v-warn", "Not on your prescription"],
                expired: ["v-bad", "Expired"], unreadable: ["v-info", "Could not read"] };
  const [cls, head] = map[r.verdict] || ["v-info", ""];
  const v = $("verdict");
  v.className = "verdict show " + cls;
  v.innerHTML = `<span class="vhead">${head}</span>${esc(r.spoken_text)}`;
  speak(r.spoken_text);
  refreshUsage();
}

/* ---------- ask ---------- */
async function askText() {
  const q = $("ask-input").value.trim();
  if (q) sendQuestion(q);
}
async function askVoice() {
  // Live mode: prefer Sarvam Saaras (record a short clip -> /api/transcribe).
  if (!state.mock) {
    const ok = await recordAndTranscribe((q) => { $("ask-input").value = q; sendQuestion(q); });
    if (ok) return;                 // on any failure, fall through to the browser
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { setStatus("Voice input not supported in this browser; type instead."); return; }
  const rec = new SR();
  rec.lang = $("language").value;
  rec.onresult = (e) => { const q = e.results[0][0].transcript; $("ask-input").value = q; sendQuestion(q); };
  rec.onerror = () => setStatus("Could not hear you; please type the question.");
  rec.start();
}
// Record ~4s and send to Sarvam Saaras via the backend. Returns true on success,
// false on any problem so the caller can fall back to browser recognition.
async function recordAndTranscribe(cb) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    const done = new Promise((res) => { rec.onstop = res; });
    rec.start();
    setStatus("Listening…");
    await new Promise((r) => setTimeout(r, 4000));
    rec.stop();
    await done;
    stream.getTracks().forEach((t) => t.stop());
    setStatus("");
    const fd = new FormData();
    fd.append("file", new File(chunks, "q.webm", { type: "audio/webm" }));
    fd.append("language", $("language").value);
    const r = await (await fetch("/api/transcribe", { method: "POST", body: fd })).json();
    if (r.text && r.text.indexOf("[") !== 0) { cb(r.text); return true; }
    return false;
  } catch (_) { setStatus(""); return false; }
}
async function sendQuestion(q) {
  const fd = new FormData();
  fd.append("question", q);
  fd.append("language", $("language").value);
  const r = await (await fetch("/api/ask", { method: "POST", body: fd })).json();
  $("answer").textContent = r.answer;
  speak(r.answer);
  refreshUsage();
}

/* ---------- dose log ---------- */
async function addLog() {
  const med = $("log-input").value.trim();
  if (!med) return;
  const fd = new FormData();
  fd.append("medicine", med);
  fd.append("actor", state.mode === "caretaker" ? "caretaker" : "patient");
  await fetch("/api/log", { method: "POST", body: fd });
  $("log-input").value = "";
  refreshLog();
}
async function refreshLog() {
  if ($("logpanel").classList.contains("hidden")) return;
  const r = await (await fetch("/api/log")).json();
  const rows = [`<tr><th>Medicine</th><th>Action</th><th>By</th><th>When</th></tr>`];
  r.events.forEach((e) => rows.push(
    `<tr><td>${esc(e.medicine)}</td><td>${esc(e.action)}</td><td>${esc(e.actor)}</td>
     <td>${esc(e.at.replace("T", " "))}</td></tr>`));
  $("log-table").innerHTML = rows.join("");
}

/* ---------- helpers ---------- */
function speak(text) {
  if (!text || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = $("language").value;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}
async function refreshUsage() {
  try {
    const u = await (await fetch("/api/usage")).json();
    const pill = $("usage-pill");
    if (!pill) return;
    const k = u.by_kind || {};
    const cost = (u.est_cost_inr != null) ? u.est_cost_inr.toFixed(2) : "0.00";
    pill.textContent = "Credits: ~₹" + cost;
    pill.title = `Estimated Sarvam spend this session (~₹${cost}). `
               + `Calls — Vision ${k.vision||0}, Chat ${k.chat||0}, `
               + `TTS ${k.tts||0}, STT ${k.stt||0}. `
               + (u.live ? "Exact figure on the Indus console." : "Mock mode = free.");
  } catch (_) {}
}
function setStatus(s) { $("scan-status").textContent = s; }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

boot();

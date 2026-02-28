// Developed by Nayan
// --- DOM references ---
const runBtn = document.getElementById("runBtn");
const runAgainBtn = document.getElementById("runAgainBtn");
const eligibilityBtn = document.getElementById("eligibilityBtn");
const runSelectedEligibilityBtn = document.getElementById("runSelectedEligibilityBtn");
const runSelectedFinalBtn = document.getElementById("runSelectedFinalBtn");
const selectedEligibilityPicker = document.getElementById("selectedEligibilityPicker");
const selectedFinalPicker = document.getElementById("selectedFinalPicker");
const selectedEligibilityMenu = document.getElementById("selectedEligibilityMenu");
const selectedFinalMenu = document.getElementById("selectedFinalMenu");
const selectedEligibilityLabel = document.getElementById("selectedEligibilityLabel");
const selectedFinalLabel = document.getElementById("selectedFinalLabel");
const logoutBtn = document.getElementById("logoutBtn");
const stopRunBtn = document.getElementById("stopRunBtn");
const yearPicker = document.getElementById("yearPicker");
const annualYearTrigger = document.getElementById("annualYearTrigger");
const annualYearMenu = document.getElementById("annualYearMenu");
const annualYearValue = document.getElementById("annualYearValue");
const notifyPicker = document.getElementById("notifyPicker");
const notifyTrigger = document.getElementById("notifyTrigger");
const notifyMenu = document.getElementById("notifyMenu");
const notifyBadge = document.getElementById("notifyBadge");
const viewScorecardBtn = document.getElementById("viewScorecard");
const scoreSection = document.getElementById("scoreSection");
const overlay = document.getElementById("overlay");
const progressBar = document.getElementById("progressBar");
const progressValue = document.getElementById("progressValue");
const progressHint = document.getElementById("progressHint");
const statusLabel = document.getElementById("statusLabel");
const stepListEl = document.getElementById("stepList");
const runTitle = document.getElementById("runTitle");
let stepItems = Array.from(document.querySelectorAll("#stepList .step"));
const logList = document.getElementById("logList");
const closeOverlay = document.getElementById("closeOverlay");
const openOverlayBtn = document.getElementById("openOverlay");
const confirmModal = document.getElementById("confirmModal");
const confirmTitle = document.getElementById("confirmTitle");
const confirmMessage = document.getElementById("confirmMessage");
const confirmOkBtn = document.getElementById("confirmOkBtn");
const confirmCancelBtn = document.getElementById("confirmCancelBtn");
const confidenceRing = document.getElementById("confidenceRing");
const healthValue = document.getElementById("healthValue");
const selectedBankChip = document.getElementById("selectedBankChip");
const selectedFinalBankNameEl = document.getElementById("selectedFinalBankName");
const selectedEligibilityBankNameEl = document.getElementById("selectedEligibilityBankName");
const totalScoreEl = document.getElementById("totalScore");
const scoreTierEl = document.getElementById("scoreTier");
const scoreFlagsEl = document.getElementById("scoreFlags");
const scoreNotesEl = document.getElementById("scoreNotes");
const featureBody = document.getElementById("featureBody");
const scoreList = document.getElementById("scoreList");
const peerMedianEl = document.getElementById("peerMedian");
const runBankName = document.getElementById("runBankName");
const resultValue = document.getElementById("resultValue");
const resultMeta = document.getElementById("resultMeta");
const resultDelta = document.getElementById("resultDelta");
const bankTabs = document.getElementById("bankTabs");
const comparisonSub = document.getElementById("comparisonSub");
const featureSub = document.getElementById("featureSub");
const strongCountEl = document.getElementById("strongCount");
const moderateCountEl = document.getElementById("moderateCount");
const weakCountEl = document.getElementById("weakCount");
const totalBankCountEl = document.getElementById("totalBankCount");
const eligibleBankCountEl = document.getElementById("eligibleBankCount");
const indicatorDonut = document.getElementById("indicatorDonut");
const indicatorDonutValue = document.getElementById("indicatorDonutValue");
const indicatorCountEl = document.getElementById("indicatorCount");
const indicatorLabelEl = document.getElementById("indicatorLabel");
const readinessChip = document.getElementById("readinessChip");
const readinessDots = [0, 1, 2].map((idx) => document.getElementById(`readinessDot${idx}`));
const readinessTitles = [0, 1, 2].map((idx) => document.getElementById(`readinessTitle${idx}`));
const readinessSubs = [0, 1, 2].map((idx) => document.getElementById(`readinessSub${idx}`));
const outputTabs = document.getElementById("outputTabs");
const outputPanels = document.getElementById("outputPanels");
const eligibilityTabs = document.getElementById("eligibilityTabs");
const eligibilityBody = document.getElementById("eligibilityBody");
const eligibilityScoreEl = document.getElementById("eligibilityScore");
const eligibilityMaxEl = document.getElementById("eligibilityMax");
const eligibilityTierEl = document.getElementById("eligibilityTier");
const eligibilityTierNoteEl = document.getElementById("eligibilityTierNote");
const eligibilityFlagsEl = document.getElementById("eligibilityFlags");
const eligibilityNotesEl = document.getElementById("eligibilityNotes");

// --- Indicator definitions and benchmarks ---
const indicatorBenchmarks = [
  {
    key: "crar",
    label: "Capital Adequacy Ratio (CRAR)",
    maxScore: 15,
    tiers: [
      { label: ">= 14%", score: 15, tone: "good" },
      { label: "12.5% - 13.9%", score: 10, tone: "warn" },
      { label: "10% - 12.4%", score: 7, tone: "warn" },
      { label: "< 10%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "leverage",
    label: "Leverage Ratio",
    maxScore: 5,
    tiers: [
      { label: ">= 3%", score: 5, tone: "good" },
      { label: "< 3%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "npl",
    label: "Non-Performing Loan (NPL) Ratio",
    maxScore: 15,
    tiers: [
      { label: "<= 3%", score: 15, tone: "good" },
      { label: "3.1% - 5%", score: 10, tone: "warn" },
      { label: "5.1% - 8%", score: 5, tone: "warn" },
      { label: "> 8%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "provision",
    label: "Provision Coverage Ratio",
    maxScore: 10,
    tiers: [
      { label: ">= 100%", score: 10, tone: "good" },
      { label: "< 100%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "ldr",
    label: "Loan to Deposit Ratio",
    maxScore: 5,
    tiers: [
      { label: "> 90%", score: 0, tone: "bad" },
      { label: "75% - 90%", score: 5, tone: "good" },
      { label: "< 75%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "roa",
    label: "Return on Assets (ROA)",
    maxScore: 5,
    tiers: [
      { label: ">= 1%", score: 5, tone: "good" },
      { label: "< 1%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "roe",
    label: "Return on Equity (ROE)",
    maxScore: 5,
    tiers: [
      { label: ">= 12%", score: 5, tone: "good" },
      { label: "< 12%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "nim",
    label: "Net Interest Margin (NIM)",
    maxScore: 5,
    tiers: [
      { label: ">= 3%", score: 5, tone: "good" },
      { label: "< 3%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "lcr",
    label: "Liquidity Coverage Ratio (LCR)",
    maxScore: 10,
    tiers: [
      { label: ">= 110%", score: 10, tone: "good" },
      { label: "< 110%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "nsfr",
    label: "Net Stable Funding Ratio (NSFR)",
    maxScore: 10,
    tiers: [
      { label: ">= 100%", score: 10, tone: "good" },
      { label: "< 100%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "cdr",
    label: "Cash-to-Deposit Ratio",
    maxScore: 5,
    tiers: [
      { label: ">= 10%", score: 5, tone: "good" },
      { label: "< 10%", score: 0, tone: "bad" },
    ],
  },
  {
    key: "creditRating",
    label: "Credit Rating",
    maxScore: 10,
    tiers: [
      { label: "AAA / AA", score: 10, tone: "good" },
      { label: "Below AA", score: 0, tone: "bad" },
    ],
  },
];

const eligibilityIndicators = indicatorBenchmarks.filter((indicator) =>
  ["npl", "provision", "creditRating"].includes(indicator.key)
);
const eligibilityMaxScore = eligibilityIndicators.reduce((sum, indicator) => sum + (indicator.maxScore || 0), 0);

// --- Run pipeline hints ---
const runSteps = {
  extraction: {
    steps: [
      "Seed discovery",
      "Download report",
      "Scan pages",
      "Extract indicators",
      "Apply benchmarks",
      "Build comparison",
      "Export scorecard",
    ],
    hints: [
      "Selecting bank seeds and report URLs",
      "Downloading report PDF",
      "Scanning pages and running OCR",
      "Extracting 12 indicators",
      "Applying regulatory benchmarks",
      "Building peer comparison",
      "Exporting scorecard output",
    ],
  },
  eligibility: {
    steps: [
      "Select bank",
      "Download report",
      "Scan pages",
      "Extract 3 indicators",
      "Send to APEX",
    ],
    hints: [
      "Selecting bank and annual report",
      "Downloading report PDF",
      "Scanning pages and running OCR",
      "Extracting 3 indicators",
      "Syncing eligibility to APEX",
    ],
  },
};

const readinessSteps = {
  extraction: [
    { title: "Seed discovery", sub: "Bank sites and data rooms" },
    { title: "PDF scan + OCR", sub: "Extraction in progress" },
    { title: "Scorecard build", sub: "12 indicators + ranking" },
  ],
  eligibility: [
    { title: "Worklist sync", sub: "Eligible banks from APEX" },
    { title: "Eligibility scan", sub: "3 indicators extraction" },
    { title: "APEX update", sub: "Eligibility results sent" },
  ],
};

// --- Formatting helpers ---
const percentKeys = new Set([
  "crar",
  "leverage",
  "npl",
  "provision",
  "ldr",
  "roa",
  "roe",
  "nim",
  "lcr",
  "nsfr",
  "cdr",
]);

// --- Shared button list ---
const runButtons = [runBtn, runAgainBtn].filter(Boolean);
const controlButtons = [
  runBtn,
  runAgainBtn,
  eligibilityBtn,
  runSelectedEligibilityBtn,
  runSelectedFinalBtn,
].filter(Boolean);
const defaultButtonLabels = new Map(
  [
    [runBtn, "Run extraction"],
    [runAgainBtn, "Run again"],
    [eligibilityBtn, "Eligibility scan"],
    [runSelectedEligibilityBtn, "Run Selected Eligibility"],
    [runSelectedFinalBtn, "Run Selected Final"],
    [stopRunBtn, "Close process"],
  ].filter(([button]) => Boolean(button))
);
const RUN_STATUS_STORAGE_KEY = "fdr-investments.runStatus.v1";
const RUN_STATUS_ENDPOINTS = ["/api/run-status", "api/run-status", "/run-status", "run-status"];
const RUN_UI_STORAGE_KEY = "fdr-investments.runUi.v1";
const AUTH_PREFS_KEY = "fdr-auth-prefs.v1";
const YEAR_PREFS_KEY = "fdr-selected-year.v1";
const NOTIFY_READ_TS_KEY = "fdr-run-notifications.readTs.v1";
const currentYear = new Date().getFullYear();
const MIN_YEAR_OPTION = currentYear - 2;
const MAX_YEAR_OPTION = currentYear + 1;

const readStoredYear = () => {
  try {
    const raw = localStorage.getItem(YEAR_PREFS_KEY);
    const year = Number(raw);
    if (!Number.isFinite(year) || year <= 0) {
      return null;
    }
    return year;
  } catch (_error) {
    return null;
  }
};

const readNotifyReadTs = () => {
  try {
    const raw = localStorage.getItem(NOTIFY_READ_TS_KEY);
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? value : 0;
  } catch (_error) {
    return 0;
  }
};

const saveNotifyReadTs = (ts) => {
  try {
    localStorage.setItem(NOTIFY_READ_TS_KEY, String(Number(ts) || 0));
  } catch (_error) {}
};

// --- App state ---
const state = {
  banks: {},
  bankOrder: [],
  activeBankKey: null,
  eligibilityBanks: {},
  eligibilityOrder: [],
  activeEligibilityKey: null,
  eligibilityMaxScore,
  hasPickedFinalBank: false,
  hasPickedEligibilityBank: false,
  outputMode: "extraction",
  totalBanks: 0,
  runSource: null,
  running: false,
  currentBankIndex: 0,
  runStart: 0,
  runBankOrder: [],
  currentRunType: null,
  stepHints: runSteps.extraction.hints,
  statusPollTimer: null,
  lastStatusKey: "",
  statusEndpoint: null,
  statusFetchErrorLogged: false,
  sourceTotalBanks: 0,
  sourceEligibleBanks: 0,
  sourceBankNames: [],
  sourceYears: [],
  selectedYear: readStoredYear(),
  selectedEligibilityBank: null,
  selectedFinalBank: null,
  selectiveEligibilityBanks: [],
  selectiveFinalBanks: [],
  lastRunRequest: null,
  notifications: [],
  unreadNotifications: 0,
};

const runConfigs = {
  extraction: {
    endpoint: "/api/run",
    label: "python scraper.py",
    statusText: "Running",
    runTitle: "Building scorecard for",
    initialHint: "Waiting for scraper",
    completeHint: "Run complete. Scorecards updated.",
    completedStatus: "Complete",
    resultValue: "All banks processed",
    resultMeta: "Scorecards streamed live from scraper output",
    deltaLabel: "Peer median delta",
    onComplete: () => {},
  },
  eligibility: {
    endpoint: "/api/eligibility-run",
    label: "python eligible_scraper.py",
    statusText: "Eligibility scan",
    runTitle: "Eligibility scan for",
    initialHint: "Waiting for eligibility scan",
    completeHint: "Eligibility scan complete. APEX sync done.",
    completedStatus: "Eligibility ready",
    resultValue: "Eligibility scan finished",
    resultMeta: "Eligible banks forwarded to APEX",
    deltaLabel: "APEX sync complete",
    onComplete: () => loadEligibilityScorecards(),
  },
};

let confirmResolver = null;

// --- Login preference helpers ---
const readAuthPrefs = () => {
  try {
    const raw = localStorage.getItem(AUTH_PREFS_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch (_error) {
    return null;
  }
};

const shouldRememberSession = () => {
  const prefs = readAuthPrefs();
  return Boolean(prefs && prefs.remember);
};

const currentNavigationType = () => {
  try {
    const [entry] = performance.getEntriesByType("navigation");
    if (entry && entry.type) {
      return entry.type;
    }
  } catch (_error) {
    return "";
  }
  return "";
};

const enforceFreshLoginOnReload = async () => {
  // If "remember" is not selected, a browser refresh should return to login.
  if (shouldRememberSession()) {
    return false;
  }
  if (currentNavigationType() !== "reload") {
    return false;
  }
  try {
    await fetch("/api/logout", { method: "POST", keepalive: true });
  } catch (_error) {
    // Ignore network errors and still redirect to login.
  }
  window.location.replace("/login");
  return true;
};

// --- Time and log utilities ---
const pad = (num) => String(num).padStart(2, "0");
const formatElapsed = (ms) => {
  const total = Math.floor(ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${pad(minutes)}:${pad(seconds)}`;
};

const addLog = (message) => {
  if (!state.runStart) {
    state.runStart = Date.now();
  }
  const li = document.createElement("li");
  const time = document.createElement("span");
  time.className = "console-time";
  time.textContent = formatElapsed(Date.now() - state.runStart);
  li.appendChild(time);
  li.append(message);
  logList.appendChild(li);
  if (logList.children.length > 200) {
    logList.removeChild(logList.firstChild);
  }
  logList.scrollTop = logList.scrollHeight;
};

const saveRunUiSnapshot = () => {
  try {
    const payload = {
      ts: Date.now(),
      running: Boolean(state.running),
      currentRunType: state.currentRunType || null,
      progressText: progressValue ? progressValue.textContent : "0%",
      progressHint: progressHint ? progressHint.textContent : "",
      runBank: runBankName ? runBankName.textContent : "",
      statusLabel: statusLabel ? statusLabel.textContent : "",
    };
    localStorage.setItem(RUN_UI_STORAGE_KEY, JSON.stringify(payload));
  } catch (error) {
    return;
  }
};

const loadRunUiSnapshot = () => {
  try {
    const raw = localStorage.getItem(RUN_UI_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch (error) {
    return null;
  }
};

const clearRunUiSnapshot = () => {
  try {
    localStorage.removeItem(RUN_UI_STORAGE_KEY);
  } catch (error) {
    return;
  }
};

const logoutUser = async () => {
  try {
    await fetch("/api/logout", { method: "POST", keepalive: true });
  } catch (_error) {
    // Redirect even when API fails, so user is moved to login screen.
  } finally {
    window.location.replace("/login");
  }
};

const saveRunStatusSnapshot = (runs) => {
  try {
    localStorage.setItem(
      RUN_STATUS_STORAGE_KEY,
      JSON.stringify({
        ts: Date.now(),
        runs: runs || {},
      })
    );
  } catch (error) {
    return;
  }
};

const clearRunStatusSnapshot = () => {
  try {
    localStorage.removeItem(RUN_STATUS_STORAGE_KEY);
  } catch (error) {
    return;
  }
};

const loadRunStatusSnapshot = () => {
  try {
    const raw = localStorage.getItem(RUN_STATUS_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    if (!parsed.runs || typeof parsed.runs !== "object") {
      return null;
    }
    return parsed;
  } catch (error) {
    return null;
  }
};

// --- Progress bar helpers ---
const setProgress = (value) => {
  const clamped = Math.max(0, Math.min(100, value));
  progressBar.style.width = `${Math.round(clamped)}%`;
  progressValue.textContent = `${Math.round(clamped)}%`;
  updateRunButtonLabel(clamped);
  saveRunUiSnapshot();
};

const setStepActive = (index) => {
  stepItems.forEach((step, idx) => {
    step.classList.toggle("active", idx === index);
    step.classList.toggle("done", idx < index);
  });
  const hints = state.stepHints || [];
  progressHint.textContent = hints[index] || "Running";
};

const resetSteps = () => {
  stepItems.forEach((step) => {
    step.classList.remove("active", "done");
  });
  if (stepItems[0]) {
    stepItems[0].classList.add("active");
  }
};

const setRunSteps = (runType) => {
  const config = runSteps[runType] || runSteps.extraction;
  state.stepHints = config.hints;
  if (!stepListEl) {
    return;
  }
  stepListEl.innerHTML = "";
  config.steps.forEach((label) => {
    const li = document.createElement("li");
    li.className = "step";
    li.textContent = label;
    stepListEl.appendChild(li);
  });
  stepItems = Array.from(stepListEl.querySelectorAll(".step"));
};

// --- Button state helpers ---
const setButtonsDisabled = (disabled) => {
  controlButtons.forEach((button) => {
    button.disabled = disabled;
    if (!disabled) {
      const label = defaultButtonLabels.get(button);
      if (label) {
        button.textContent = label;
      }
    }
  });
  if (disabled) {
    if (runBtn) {
      updateRunButtonLabel(0);
    }
    if (eligibilityBtn) {
      eligibilityBtn.textContent = "Checking eligibility…";
    }
  }
  updateStopButtonState();
};

const updateStopButtonState = () => {
  if (!stopRunBtn) {
    return;
  }
  stopRunBtn.disabled = !state.running;
};

// --- Run button label helpers ---
const updateRunButtonLabel = (progress) => {
  if (!runBtn) {
    return;
  }
  if (!state.running || state.currentRunType !== "extraction") {
    runBtn.textContent = defaultButtonLabels.get(runBtn) || "Run extraction";
    return;
  }
  runBtn.textContent = "Running";
};

const setReadinessDotState = (index, stateName) => {
  const dot = readinessDots[index];
  if (!dot) {
    return;
  }
  dot.classList.toggle("ok", stateName === "ok");
  dot.classList.toggle("active", stateName === "active");
};

const setReadinessContent = (runType) => {
  const config = readinessSteps[runType] || readinessSteps.extraction;
  config.forEach((step, idx) => {
    if (readinessTitles[idx]) {
      readinessTitles[idx].textContent = step.title;
    }
    if (readinessSubs[idx]) {
      readinessSubs[idx].textContent = step.sub;
    }
  });
};

const setReadinessIdle = () => {
  setReadinessContent("extraction");
  setReadinessDotState(0, "ok");
  setReadinessDotState(1, "ok");
  setReadinessDotState(2, "pending");
  if (readinessChip) {
    readinessChip.textContent = "Ready";
  }
  if (healthValue) {
    healthValue.textContent = "100%";
  }
  if (confidenceRing) {
    confidenceRing.style.setProperty("--progress", "1");
  }
};

const setReadinessActive = (runType, completed = 0, total = 0) => {
  setReadinessContent(runType);
  const percent = total > 0 ? Math.max(0, Math.min(100, Math.round((completed / total) * 100))) : Math.min(95, completed * 3);
  let stage = 0;
  if (percent >= 85) {
    stage = 2;
  } else if (percent >= 20) {
    stage = 1;
  }
  for (let i = 0; i < 3; i += 1) {
    if (i < stage) {
      setReadinessDotState(i, "ok");
    } else if (i === stage) {
      setReadinessDotState(i, "active");
    } else {
      setReadinessDotState(i, "pending");
    }
  }
  if (readinessChip) {
    readinessChip.textContent = runType === "eligibility" ? "Eligibility" : "Running";
  }
  if (healthValue) {
    healthValue.textContent = `${percent}%`;
  }
  if (confidenceRing) {
    confidenceRing.style.setProperty("--progress", (percent / 100).toFixed(2));
  }
};

// --- Overlay visibility helpers ---
const syncOverlayToggle = () => {
  if (!openOverlayBtn) {
    return;
  }
  openOverlayBtn.classList.add("visible");
  openOverlayBtn.disabled = !state.running;
};

const showOverlay = () => {
  overlay.classList.add("show");
  document.body.classList.add("locked");
  syncOverlayToggle();
};

const hideOverlay = () => {
  overlay.classList.remove("show");
  document.body.classList.remove("locked");
  syncOverlayToggle();
};

const closeConfirmModal = (value) => {
  if (!confirmModal) {
    return;
  }
  confirmModal.classList.remove("show");
  confirmModal.setAttribute("aria-hidden", "true");
  if (confirmResolver) {
    const resolve = confirmResolver;
    confirmResolver = null;
    resolve(Boolean(value));
  }
};

const openConfirmModal = (title, message) =>
  new Promise((resolve) => {
    if (!confirmModal || !confirmTitle || !confirmMessage) {
      resolve(true);
      return;
    }
    confirmResolver = resolve;
    confirmTitle.textContent = title || "Confirm action";
    confirmMessage.textContent = message || "Are you sure you want to continue?";
    confirmModal.classList.add("show");
    confirmModal.setAttribute("aria-hidden", "false");
    if (confirmCancelBtn) {
      confirmCancelBtn.focus();
    }
  });

// --- Value formatting and scoring helpers ---
const isMissingValue = (value) => {
  if (value === null || value === undefined) {
    return true;
  }
  if (typeof value === "number") {
    return !Number.isFinite(value);
  }
  if (typeof value === "string") {
    const trimmed = value.trim().toLowerCase();
    return trimmed === "" || trimmed === "none" || trimmed === "null" || trimmed === "nan" || trimmed === "n/a";
  }
  return false;
};

const formatValue = (value, key) => {
  if (isMissingValue(value)) {
    return "N/A";
  }
  if (typeof value === "number") {
    const formatted = Number.isInteger(value) ? value.toString() : value.toFixed(2);
    return percentKeys.has(key) ? `${formatted}%` : formatted;
  }
  return String(value);
};

const getScoreValue = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const getTotalScore = (bank) => {
  if (typeof bank.totalScore === "number") {
    return bank.totalScore;
  }
  return indicatorBenchmarks.reduce((sum, indicator) => {
    const entry = bank.indicators[indicator.key];
    const score = getScoreValue(entry?.score);
    return sum + (score ?? 0);
  }, 0);
};

const getEligibilityTotalScore = (bank) => {
  if (!bank || !bank.indicators) {
    return 0;
  }
  return eligibilityIndicators.reduce((sum, indicator) => {
    const entry = bank.indicators[indicator.key];
    const score = getScoreValue(entry?.score);
    return sum + (score ?? 0);
  }, 0);
};

const getEligibilityPercent = (bank) => {
  const max = state.eligibilityMaxScore || eligibilityMaxScore;
  if (!max) {
    return 0;
  }
  return Math.round((getEligibilityTotalScore(bank) / max) * 100);
};

const getCoveragePercent = (bank) => {
  if (!bank || !bank.indicators) {
    return 0;
  }
  const keys = indicatorBenchmarks.map((indicator) => indicator.key).filter((key) => key !== "cdr");
  const total = keys.length;
  if (!total) {
    return 0;
  }
  const filled = keys.reduce((count, key) => {
    const value = bank.indicators[key]?.value;
    const hasValue = value !== null && value !== undefined && value !== "";
    return count + (hasValue ? 1 : 0);
  }, 0);
  return Math.round((filled / total) * 100);
};

const donutPalette = ["#2ed9b8", "#6fd2ff", "#f2a93b", "#ff6f7d"];

const updateIndicatorDonut = (bank) => {
  if (!indicatorDonut || !bank?.indicators) {
    return;
  }
  const total = indicatorBenchmarks.length;
  if (!total) {
    return;
  }
  const angle = 360 / total;
  let current = 0;
  const segments = [];
  let totalScore = 0;
  let totalMax = 0;
  indicatorBenchmarks.forEach((indicator, idx) => {
    const entry = bank.indicators[indicator.key] || {};
    const score = getScoreValue(entry.score);
    const max = indicator.maxScore || 0;
    const ratio = max > 0 && score !== null ? Math.max(0, Math.min(1, score / max)) : 0;
    const start = current;
    const filled = start + angle * ratio;
    const end = start + angle;
    const fillColor = donutPalette[idx % donutPalette.length];
    const emptyColor = "rgba(255, 255, 255, 0.08)";
    if (ratio > 0) {
      segments.push(`${fillColor} ${start.toFixed(2)}deg ${filled.toFixed(2)}deg`);
    }
    segments.push(`${emptyColor} ${filled.toFixed(2)}deg ${end.toFixed(2)}deg`);
    current = end;
    if (max > 0) {
      totalMax += max;
      totalScore += Math.max(0, score ?? 0);
    }
  });
  indicatorDonut.style.background = `conic-gradient(${segments.join(", ")})`;
  if (indicatorDonutValue) {
    const percent = totalMax ? Math.round((totalScore / totalMax) * 100) : 0;
    indicatorDonutValue.textContent = `${percent}%`;
  }
};

const getTier = (score) => {
  if (score >= 80) return "Strong";
  if (score >= 60) return "Moderate";
  return "Weak";
};

const updateTierCounts = () => {
  if (!strongCountEl || !moderateCountEl || !weakCountEl) {
    return;
  }
  const counts = { Strong: 0, Moderate: 0, Weak: 0 };
  state.bankOrder.forEach((key) => {
    const bank = state.banks[key];
    const score = getTotalScore(bank);
    counts[getTier(score)] += 1;
  });
  strongCountEl.textContent = counts.Strong;
  moderateCountEl.textContent = counts.Moderate;
  weakCountEl.textContent = counts.Weak;
};

const updateBankCounts = () => {
  const totalFromSource =
    state.sourceTotalBanks ||
    state.totalBanks ||
    state.runBankOrder.length ||
    state.bankOrder.length ||
    state.eligibilityOrder.length ||
    0;
  if (totalBankCountEl) {
    totalBankCountEl.textContent = totalFromSource;
  }
  if (eligibleBankCountEl) {
    const eligible = state.sourceEligibleBanks || state.runBankOrder.length || state.bankOrder.length || 0;
    eligibleBankCountEl.textContent = eligible;
  }
};

const getFlags = (bank) => {
  const flags = [];
  const nplScore = getScoreValue(bank.indicators.npl?.score);
  const crarScore = getScoreValue(bank.indicators.crar?.score);

  if (nplScore !== null && nplScore <= 5) {
    flags.push("High NPL ratio");
  }
  if (crarScore !== null && crarScore <= 7) {
    flags.push("Low CRAR");
  }
  return flags;
};

const getEligibilityFlags = (bank) => {
  const flags = [];
  const nplScore = getScoreValue(bank.indicators.npl?.score);
  const pcrScore = getScoreValue(bank.indicators.provision?.score);
  const ratingScore = getScoreValue(bank.indicators.creditRating?.score);

  if (nplScore !== null && nplScore <= 5) {
    flags.push("High NPL ratio");
  }
  if (pcrScore !== null && pcrScore <= 0) {
    flags.push("Low PCR");
  }
  if (ratingScore !== null && ratingScore <= 0) {
    flags.push("Below AA rating");
  }
  return flags;
};

const normalizeRating = (value) => {
  if (isMissingValue(value)) {
    return "";
  }
  return String(value).trim().toUpperCase();
};

const getEligibilityStatus = (bank) => {
  if (!bank || !bank.indicators) {
    return "weak";
  }
  const nplValue = bank.indicators.npl?.value;
  const ratingValue = bank.indicators.creditRating?.value;
  if (isMissingValue(nplValue) || isMissingValue(ratingValue)) {
    return "weak";
  }
  const numericNpl = Number(nplValue);
  const rating = normalizeRating(ratingValue);
  if (Number.isFinite(numericNpl) && numericNpl < 8 && (rating === "AAA" || rating === "AA")) {
    return "strong";
  }
  return "moderate";
};

// --- UI rendering: feature table ---
const renderIndicatorRows = (bank, indicators, target) => {
  if (!target) {
    return;
  }
  target.innerHTML = "";
  if (!bank) {
    return;
  }

  indicators.forEach((indicator) => {
    const entry = bank.indicators[indicator.key] || {};
    const row = document.createElement("div");
    row.className = "feature-row";

    const indicatorCell = document.createElement("span");
    indicatorCell.className = "indicator-name";
    indicatorCell.textContent = indicator.label;

    const benchmarkCell = document.createElement("div");
    benchmarkCell.className = "benchmark-stack";

    indicator.tiers.forEach((tier) => {
      const chip = document.createElement("div");
      chip.className = `benchmark-chip ${tier.tone}`;

      const label = document.createElement("span");
      label.className = "chip-label";
      label.textContent = tier.label;

      const score = document.createElement("span");
      score.className = "chip-score";
      score.textContent = tier.score;

      chip.append(label, score);
      benchmarkCell.appendChild(chip);
    });

    const valueCell = document.createElement("span");
    const formattedValue = formatValue(entry.value, indicator.key);
    valueCell.textContent = formattedValue;
    if (formattedValue === "N/A") {
      valueCell.classList.add("na");
    }

    const scoreCell = document.createElement("span");
    const numericScore = getScoreValue(entry.score);
    const scoreClass =
      numericScore === null
        ? ""
        : numericScore < 0
        ? "score-negative"
        : numericScore === indicator.maxScore && indicator.maxScore > 0
        ? "score-positive"
        : numericScore > 0
        ? "score-warning"
        : "";
    scoreCell.className = `score-cell${scoreClass ? ` ${scoreClass}` : ""}`;
    const scoreText = isMissingValue(entry.score) ? "N/A" : entry.score;
    scoreCell.textContent = scoreText;
    if (scoreText === "N/A") {
      scoreCell.classList.add("na");
    }

    const pageCell = document.createElement("span");
    pageCell.className = "page-cell";
    const pageValue = entry.page ?? "";
    const pageText = isMissingValue(pageValue) ? "N/A" : pageValue;
    if (pageText === "N/A") {
      pageCell.textContent = pageText;
      pageCell.classList.add("na");
    } else if (entry.sourceUrl) {
      const link = document.createElement("a");
      link.className = "page-link";
      link.href = entry.sourceUrl;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = pageText;
      link.title = "Open source PDF at the highlighted value";
      pageCell.appendChild(link);
    } else {
      pageCell.textContent = pageText;
    }

    row.append(indicatorCell, benchmarkCell, valueCell, scoreCell, pageCell);
    target.appendChild(row);
  });
};

const renderFeatureRows = (bankKey) => {
  const bank = state.banks[bankKey];
  renderIndicatorRows(bank, indicatorBenchmarks, featureBody);
};

const renderEligibilityRows = (bankKey) => {
  const bank = state.eligibilityBanks[bankKey];
  renderIndicatorRows(bank, eligibilityIndicators, eligibilityBody);
};

// --- UI rendering: comparison list ---
const renderComparison = (activeKey) => {
  const totals = state.bankOrder.map((key) => {
    const bank = state.banks[key];
    return {
      key,
      name: bank.name,
      score: getTotalScore(bank),
    };
  });

  totals.sort((a, b) => b.score - a.score);
  const scores = totals.map((item) => item.score).sort((a, b) => a - b);
  const mid = Math.floor(scores.length / 2);
  const median = scores.length % 2 === 0 ? Math.round((scores[mid - 1] + scores[mid]) / 2) : scores[mid];

  if (peerMedianEl) {
    peerMedianEl.textContent = `Median score: ${median}`;
  }
  scoreList.innerHTML = "";

  totals.forEach((item) => {
    const scoreItem = document.createElement("div");
    scoreItem.className = "score-item";
    scoreItem.dataset.bank = item.key;
    scoreItem.setAttribute("role", "button");
    scoreItem.tabIndex = 0;
    scoreItem.title = "View scorecard";
    if (item.key === activeKey) {
      scoreItem.classList.add("active");
    }
    const tier = getTier(item.score).toLowerCase();
    scoreItem.classList.add(`tier-${tier}`);

    const head = document.createElement("div");
    head.className = "score-head";

    const value = document.createElement("span");
    value.className = "score-value";
    value.textContent = `${item.score} / 100`;

    const name = document.createElement("span");
    name.className = "score-name";
    name.textContent = item.name;

    head.append(value, name);

    const bar = document.createElement("div");
    bar.className = "score-bar";
    const barFill = document.createElement("span");
    barFill.style.setProperty("--value", item.score / 100);
    if (tier === "strong") {
      barFill.style.setProperty("--tier-color", "rgba(46, 217, 184, 0.9)");
      barFill.style.setProperty("--tier-color-fade", "rgba(46, 217, 184, 0.4)");
    } else if (tier === "moderate") {
      barFill.style.setProperty("--tier-color", "rgba(242, 169, 59, 0.9)");
      barFill.style.setProperty("--tier-color-fade", "rgba(242, 169, 59, 0.4)");
    } else {
      barFill.style.setProperty("--tier-color", "rgba(255, 111, 125, 0.9)");
      barFill.style.setProperty("--tier-color-fade", "rgba(255, 111, 125, 0.4)");
    }
    bar.appendChild(barFill);

    scoreItem.append(head, bar);
    scoreList.appendChild(scoreItem);
  });

  const activeItem = scoreList.querySelector(".score-item.active");
  if (activeItem) {
    activeItem.classList.add("active");
  }
};

const renderEligibilityComparison = (activeKey) => {
  const maxScore = state.eligibilityMaxScore || eligibilityMaxScore || 0;
  const totals = state.eligibilityOrder.map((key) => {
    const bank = state.eligibilityBanks[key];
    return {
      key,
      name: bank.name,
      score: getEligibilityTotalScore(bank),
    };
  });

  totals.sort((a, b) => b.score - a.score);
  scoreList.innerHTML = "";

  if (!totals.length) {
    scoreList.innerHTML = '<div class="empty-state">No eligibility results yet.</div>';
    return;
  }

  totals.forEach((item) => {
    const scoreItem = document.createElement("div");
    scoreItem.className = "score-item";
    scoreItem.dataset.bank = item.key;
    scoreItem.setAttribute("role", "button");
    scoreItem.tabIndex = 0;
    scoreItem.title = "View eligibility score";
    if (item.key === activeKey) {
      scoreItem.classList.add("active");
    }

    const head = document.createElement("div");
    head.className = "score-head";

    const value = document.createElement("span");
    value.className = "score-value";
    value.textContent = `${item.score} / ${maxScore || 0}`;

    const name = document.createElement("span");
    name.className = "score-name";
    name.textContent = item.name;

    head.append(value, name);

    const bar = document.createElement("div");
    bar.className = "score-bar";
    const barFill = document.createElement("span");
    const ratio = maxScore ? item.score / maxScore : 0;
    barFill.style.setProperty("--value", Math.max(0, Math.min(1, ratio)));
    bar.appendChild(barFill);

    scoreItem.append(head, bar);
    scoreList.appendChild(scoreItem);
  });

  const activeItem = scoreList.querySelector(".score-item.active");
  if (activeItem) {
    activeItem.classList.add("active");
  }
};

const getMedianScore = () => {
  const scores = state.bankOrder
    .map((key) => getTotalScore(state.banks[key]))
    .filter((score) => typeof score === "number")
    .sort((a, b) => a - b);
  if (!scores.length) {
    return null;
  }
  const mid = Math.floor(scores.length / 2);
  if (scores.length % 2 === 0) {
    return Math.round((scores[mid - 1] + scores[mid]) / 2);
  }
  return scores[mid];
};

// --- UI rendering: bank tabs ---
const renderBankTabs = () => {
  bankTabs.innerHTML = "";
  state.bankOrder.forEach((key) => {
    const bank = state.banks[key];
    const button = document.createElement("button");
    button.className = "bank-tab";
    button.dataset.bank = key;
    button.textContent = bank.name;
    const tier = getTier(getTotalScore(bank)).toLowerCase();
    button.classList.add(`tier-${tier}`);
    if (key === state.activeBankKey) {
      button.classList.add("active");
    }
    bankTabs.appendChild(button);
  });
};

const renderEligibilityTabs = () => {
  if (!eligibilityTabs) {
    return;
  }
  eligibilityTabs.innerHTML = "";
  state.eligibilityOrder.forEach((key) => {
    const bank = state.eligibilityBanks[key];
    const button = document.createElement("button");
    button.className = "bank-tab";
    button.dataset.bank = key;
    button.textContent = bank.name;
    const status = getEligibilityStatus(bank);
    button.classList.add(`tier-${status}`);
    if (key === state.activeEligibilityKey) {
      button.classList.add("active");
    }
    eligibilityTabs.appendChild(button);
  });
};

// --- UI rendering: active bank summary ---
const updateActiveBank = (bankKey) => {
  if (!state.banks[bankKey]) {
    return;
  }
  state.activeBankKey = bankKey;
  const bank = state.banks[bankKey];

  if (state.outputMode === "extraction" && selectedBankChip) {
    selectedBankChip.textContent = bank.name;
  }
  if (selectedFinalBankNameEl) {
    selectedFinalBankNameEl.textContent = state.hasPickedFinalBank ? bank.name || "" : "";
  }
  runBankName.textContent = bank.name;

  const totalScore = getTotalScore(bank);
  totalScoreEl.textContent = totalScore;
  scoreTierEl.textContent = getTier(totalScore);

  const flags = getFlags(bank);
  scoreFlagsEl.textContent = flags.length ? `${flags.length} flags` : "0 flags";
  scoreNotesEl.textContent = flags.length ? flags.join(" | ") : "No critical warnings";

  const coverageScore = getCoveragePercent(bank);
  healthValue.textContent = `${coverageScore}%`;
  if (confidenceRing) {
    confidenceRing.style.setProperty("--progress", (coverageScore / 100).toFixed(2));
  }

  updateIndicatorDonut(bank);
  renderFeatureRows(bankKey);
  if (state.outputMode === "extraction") {
    renderComparison(bankKey);
  }
  renderBankTabs();
  updateTierCounts();
  updateBankCounts();
  scheduleOutputPanelHeight();
};

const resetExtractionView = (message = "No extraction data yet.") => {
  state.activeBankKey = null;
  if (selectedBankChip) {
    selectedBankChip.textContent = "No bank selected";
  }
  if (selectedFinalBankNameEl) {
    selectedFinalBankNameEl.textContent = "";
  }
  state.hasPickedFinalBank = false;
  if (totalScoreEl) {
    totalScoreEl.textContent = "0";
  }
  if (scoreTierEl) {
    scoreTierEl.textContent = "--";
  }
  if (scoreFlagsEl) {
    scoreFlagsEl.textContent = "0 flags";
  }
  if (scoreNotesEl) {
    scoreNotesEl.textContent = "Waiting for extraction output";
  }
  if (featureBody) {
    featureBody.innerHTML = `<div class="empty-state">${message}</div>`;
  }
  if (bankTabs) {
    bankTabs.innerHTML = "";
  }
  if (scoreList) {
    scoreList.innerHTML = `<div class="empty-state">${message}</div>`;
  }
  updateTierCounts();
  updateBankCounts();
  scheduleOutputPanelHeight();
};

const updateActiveEligibilityBank = (bankKey) => {
  if (!state.eligibilityBanks[bankKey]) {
    return;
  }
  state.activeEligibilityKey = bankKey;
  const bank = state.eligibilityBanks[bankKey];

  if (state.outputMode === "eligibility" && selectedBankChip) {
    selectedBankChip.textContent = bank.name;
  }
  if (selectedEligibilityBankNameEl) {
    selectedEligibilityBankNameEl.textContent = state.hasPickedEligibilityBank ? bank.name || "" : "";
  }
  runBankName.textContent = bank.name;

  const totalScore = getEligibilityTotalScore(bank);
  const percent = getEligibilityPercent(bank);
  if (eligibilityScoreEl) {
    eligibilityScoreEl.textContent = totalScore;
  }
  if (eligibilityMaxEl) {
    const max = state.eligibilityMaxScore || eligibilityMaxScore;
    eligibilityMaxEl.textContent = `Out of ${max || 0}`;
  }
  const status = getEligibilityStatus(bank);
  if (eligibilityTierEl) {
    eligibilityTierEl.textContent = status === "strong" ? "Strong" : status === "moderate" ? "Moderate" : "Weak";
  }
  if (eligibilityTierNoteEl) {
    eligibilityTierNoteEl.textContent =
      status === "strong"
        ? "NPL < 8 and rating AA/AAA"
        : status === "moderate"
        ? "Eligibility not met"
        : "Missing NPL or rating";
  }

  const flags = getEligibilityFlags(bank);
  if (eligibilityFlagsEl) {
    eligibilityFlagsEl.textContent = flags.length ? `${flags.length} flags` : "0 flags";
  }
  if (eligibilityNotesEl) {
    eligibilityNotesEl.textContent = flags.length ? flags.join(" | ") : "No eligibility warnings";
  }

  renderEligibilityRows(bankKey);
  renderEligibilityTabs();
  if (state.outputMode === "eligibility") {
    renderEligibilityComparison(bankKey);
  }
  scheduleOutputPanelHeight();
};

const slugify = (value) => {
  if (!value) {
    return "unknown";
  }
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
};

// --- Bank name matching helpers ---
const normalizeBankName = (name) =>
  name
    .toLowerCase()
    .replace(/[()]/g, "")
    .replace(/\s+/g, " ")
    .trim();

const findBankKeyByName = (name) => {
  const normalized = normalizeBankName(name);
  return state.bankOrder.find((key) => {
    const candidate = normalizeBankName(state.banks[key].name);
    return candidate === normalized || candidate.includes(normalized) || normalized.includes(candidate);
  });
};

const findRunBankIndex = (name) => {
  const normalized = normalizeBankName(name);
  return state.runBankOrder.findIndex((bank) => normalizeBankName(bank) === normalized);
};

const setRunBankOrder = (banks) => {
  state.runBankOrder = banks.filter(Boolean);
  if (!state.totalBanks) {
    state.totalBanks = state.runBankOrder.length;
  } else {
    state.totalBanks = Math.max(state.totalBanks, state.runBankOrder.length);
  }
  updateBankCounts();
};

// --- Progress updates from log steps ---
const updateProgressForStep = (stepIndex) => {
  if (!state.totalBanks) {
    const stepProgress = (stepIndex + 1) / stepItems.length;
    setProgress(stepProgress * 100);
    return;
  }
  const base = state.currentBankIndex / state.totalBanks;
  const stepPortion = (stepIndex + 1) / stepItems.length / state.totalBanks;
  setProgress((base + stepPortion) * 100);
};

// --- Live log parsing ---
const handleLogLine = (line) => {
  if (!line) {
    return;
  }
  addLog(line);

  const processingMatch = line.match(/^Processing\s+(.+?)\s+\d{4}/);
  const eligibilityMatch = line.match(/^Eligibility scan:\s+(.+?)\s+\d{4}/);
  if (processingMatch || eligibilityMatch) {
    const bankName = (processingMatch ? processingMatch[1] : eligibilityMatch[1]).trim();
    runBankName.textContent = bankName;
    const runIndex = findRunBankIndex(bankName);
    if (runIndex >= 0) {
      state.currentBankIndex = runIndex;
    } else {
      state.currentBankIndex = state.runBankOrder.length;
      state.runBankOrder.push(bankName);
      state.totalBanks = Math.max(state.totalBanks, state.runBankOrder.length);
      updateBankCounts();
    }
    const key = findBankKeyByName(bankName);
    if (key) {
      updateActiveBank(key);
    }
    resetSteps();
    setStepActive(0);
    updateProgressForStep(0);
    return;
  }

  if (line.startsWith("Downloading PDF")) {
    setStepActive(1);
    updateProgressForStep(1);
    return;
  }

  if (line.startsWith("Scanning PDF")) {
    const idx = state.currentRunType === "eligibility" ? 2 : 2;
    setStepActive(idx);
    updateProgressForStep(idx);
    return;
  }

  if (line.startsWith("Scanning pages")) {
    const idx = state.currentRunType === "eligibility" ? 2 : 3;
    setStepActive(idx);
    updateProgressForStep(idx);
    return;
  }

  if (state.currentRunType === "eligibility") {
    if (line.startsWith("Eligibility result")) {
      setStepActive(3);
      updateProgressForStep(3);
      return;
    }
    if (line.startsWith("APEX sent") || line.startsWith("APEX response")) {
      setStepActive(stepItems.length - 1);
      updateProgressForStep(stepItems.length - 1);
      return;
    }
  } else if (line.startsWith("Total score")) {
    setStepActive(4);
    updateProgressForStep(4);
    return;
  }

  if (line.startsWith("Saved")) {
    setStepActive(stepItems.length - 1);
    updateProgressForStep(stepItems.length - 1);
    return;
  }
};

// --- Run lifecycle helpers ---
const finalizeRun = (runType = "extraction", options = {}) => {
  const config = runConfigs[runType] || runConfigs.extraction;
  overlay.classList.add("complete");
  statusLabel.textContent = config.completedStatus || config.statusText || "Complete";
  setProgress(100);
  progressHint.textContent = config.completeHint;
  resultValue.textContent = config.resultValue;
  resultMeta.textContent = config.resultMeta;
  if (resultDelta) {
    if (runType === "extraction") {
      if (state.activeBankKey) {
        const median = getMedianScore();
        const current = getTotalScore(state.banks[state.activeBankKey]);
        if (median !== null && typeof current === "number") {
          const delta = current - median;
          const sign = delta >= 0 ? "+" : "";
          resultDelta.textContent = `Peer median delta: ${sign}${delta}`;
        } else {
          resultDelta.textContent = "Peer median delta: N/A";
        }
      } else {
        resultDelta.textContent = "Peer median delta: N/A";
      }
    } else {
      resultDelta.textContent = config.deltaLabel;
    }
  }
  setButtonsDisabled(false);
  state.running = false;
  state.currentRunType = null;
  state.runSource = null;
  clearRunStatusSnapshot();
  clearRunUiSnapshot();
  stopRunStatusPolling();
  setReadinessIdle();
  refreshNotifications();
  updateStopButtonState();
  syncOverlayToggle();
};

// --- Start scraper run (SSE stream) ---
const startRunMode = (runType, options = {}) => {
  const config = runConfigs[runType] || runConfigs.extraction;
  if (state.running) {
    showOverlay();
    startRunStatusPolling();
    loadRunStatus(true);
    return;
  }
  if (state.runSource) {
    state.runSource.close();
  }

  state.running = true;
  state.currentRunType = runType;
  overlay.classList.add("show");
  overlay.classList.remove("complete");
  document.body.classList.add("locked");
  syncOverlayToggle();
  setButtonsDisabled(true);
  statusLabel.textContent = config.statusText || "Running";
  if (runTitle) {
    runTitle.textContent = config.runTitle || "Running";
  }
  setRunSteps(runType);
  state.currentBankIndex = 0;
  if (runType === "extraction") {
    state.banks = {};
    state.bankOrder = [];
    resetExtractionView("Waiting for extraction results...");
    setOutputMode("extraction");
  }
  setProgress(0);
  progressHint.textContent = config.initialHint || "Waiting for run";
  resetSteps();
  if (runBankName && options.selectedBank) {
    runBankName.textContent = String(options.selectedBank);
  }
  if (runType === "eligibility") {
    setOutputMode("eligibility");
  }

  state.runStart = Date.now();
  state.lastRunRequest = {
    runType,
    options: {
      selectedBank: options.selectedBank ? String(options.selectedBank) : null,
    },
  };
  startRunStatusPolling();
  addLog(`Run started: ${config.label}`);
  const query = new URLSearchParams();
  if (state.selectedYear) {
    query.set("year", String(state.selectedYear));
  }
  if (options.selectedBank) {
    query.set("bank", String(options.selectedBank));
  }
  const runUrl = query.toString() ? `${config.endpoint}?${query.toString()}` : config.endpoint;
  if (state.selectedYear) {
    addLog(`Using source year: ${state.selectedYear}`);
  }
  if (options.selectedBank) {
    addLog(`Using selected bank: ${options.selectedBank}`);
  }

  const source = new EventSource(runUrl);
  state.runSource = source;

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "log") {
        handleLogLine(payload.line);
      }
      if (payload.type === "eligibility") {
        applyEligibilityRecord(payload.record);
      }
      if (payload.type === "extraction") {
        applyExtractionRecord(payload.record);
      }
      if (payload.type === "complete") {
        source.close();
        const completedRun = payload.run || runType;
        finalizeRun(completedRun, { successful: Number(payload.returncode || 0) === 0 });
        const completedConfig = runConfigs[completedRun] || config;
        if (completedConfig.onComplete) {
          completedConfig.onComplete();
        }
      }
      if (payload.type === "error") {
        const message = String(payload.message || "");
        if (message.toLowerCase().includes("already in progress")) {
          addLog(`Info: ${message}`);
          source.close();
          state.runSource = null;
          state.running = true;
          showOverlay();
          startRunStatusPolling();
          loadRunStatus(true);
          return;
        }
        addLog(`Error: ${payload.message}`);
        source.close();
        state.runSource = null;
        finalizeRun(runType, { successful: false });
      }
    } catch (error) {
      addLog(event.data);
    }
  };

  source.onerror = () => {
    addLog("Connection lost. Make sure ui_server.py is running.");
    source.close();
    state.runSource = null;
    loadRunStatus(true);
  };
};

const startRun = () => startRunMode("extraction");
const startEligibilityRun = () => startRunMode("eligibility");
const startSelectedEligibilityRun = () => {
  const bankName = String(state.selectedEligibilityBank || "").trim();
  if (!bankName) {
    addLog("Select a bank from 'Run Selected Eligibility' first.");
    return;
  }
  startRunMode("eligibility", { selectedBank: bankName });
};
const startSelectedFinalRun = () => {
  const bankName = String(state.selectedFinalBank || "").trim();
  if (!bankName) {
    addLog("Select a bank from 'Run Selected Final' first.");
    return;
  }
  startRunMode("extraction", { selectedBank: bankName });
};

const runPreviousMode = () => {
  const previous = state.lastRunRequest;
  if (previous && previous.runType) {
    startRunMode(previous.runType, previous.options || {});
    return;
  }
  startRun();
};

const setSelectedYear = (yearValue) => {
  const numericYear = Number(yearValue);
  if (!Number.isFinite(numericYear) || numericYear <= 0) {
    state.selectedYear = null;
    if (annualYearValue) {
      annualYearValue.textContent = "----";
    }
    try {
      localStorage.removeItem(YEAR_PREFS_KEY);
    } catch (_error) {}
    return;
  }
  state.selectedYear = numericYear;
  if (annualYearValue) {
    annualYearValue.textContent = String(numericYear);
  }
  try {
    localStorage.setItem(YEAR_PREFS_KEY, String(numericYear));
  } catch (_error) {}
};
setSelectedYear(state.selectedYear);

const syncYearDropdown = (years) => {
  if (!annualYearMenu) {
    return;
  }
  const fixedYears = Array.from(
    { length: MAX_YEAR_OPTION - MIN_YEAR_OPTION + 1 },
    (_, index) => MIN_YEAR_OPTION + index
  );
  const normalizedYears = Array.from(
    new Set(
      [...fixedYears, ...(years || [])]
        .map((year) => Number(year))
        .filter((year) => Number.isFinite(year) && year > 0)
    )
  ).sort((a, b) => b - a);
  state.sourceYears = normalizedYears;

  const preferredYear = state.selectedYear;
  annualYearMenu.innerHTML = "";

  if (!normalizedYears.length) {
    state.selectedYear = null;
    if (annualYearValue) {
      annualYearValue.textContent = "----";
    }
    return;
  }

  normalizedYears.forEach((year) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "year-option";
    option.setAttribute("role", "option");
    option.dataset.year = String(year);
    option.textContent = String(year);
    annualYearMenu.appendChild(option);
  });

  const nextYear = normalizedYears.includes(preferredYear) ? preferredYear : null;
  setSelectedYear(nextYear);
  Array.from(annualYearMenu.querySelectorAll(".year-option")).forEach((node) => {
    node.classList.toggle("active", nextYear !== null && Number(node.dataset.year) === nextYear);
  });
};

const closeYearMenu = () => {
  if (!annualYearMenu || !annualYearTrigger) {
    return;
  }
  annualYearMenu.hidden = true;
  annualYearTrigger.setAttribute("aria-expanded", "false");
};

const openYearMenu = () => {
  if (!annualYearMenu || !annualYearTrigger) {
    return;
  }
  annualYearMenu.hidden = false;
  annualYearTrigger.setAttribute("aria-expanded", "true");
};

const renderNotifications = () => {
  if (!notifyMenu) {
    return;
  }
  notifyMenu.innerHTML = "";
  if (!state.notifications.length) {
    const empty = document.createElement("div");
    empty.className = "notify-empty";
    empty.textContent = "No notification yet.";
    notifyMenu.appendChild(empty);
    return;
  }
  state.notifications.forEach((item) => {
    const row = document.createElement("div");
    row.className = "notify-item";
    const ts = document.createElement("span");
    ts.className = "notify-time";
    ts.textContent = item.time || "";
    const text = document.createElement("span");
    text.className = "notify-text";
    text.textContent = item.text || "";
    row.append(ts, text);
    notifyMenu.appendChild(row);
  });
};

const refreshNotifications = async () => {
  try {
    const response = await fetch("/api/notifications", { cache: "no-store" });
    if (!response.ok) {
      state.notifications = [];
      state.unreadNotifications = 0;
      renderNotifications();
      syncNotifyBadge();
      return;
    }
    const payload = await response.json();
    const items = Array.isArray(payload?.items) ? payload.items : [];
    state.notifications = items
      .filter((item) => item && typeof item === "object" && String(item.text || "").trim())
      .slice(0, 10);
    const lastReadTs = readNotifyReadTs();
    state.unreadNotifications = state.notifications.filter((item) => Number(item.ts || 0) > lastReadTs).length;
    renderNotifications();
    syncNotifyBadge();
  } catch (_error) {
    state.notifications = [];
    state.unreadNotifications = 0;
    renderNotifications();
    syncNotifyBadge();
  }
};

const syncNotifyBadge = () => {
  if (!notifyBadge) {
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  if (unread <= 0) {
    notifyBadge.hidden = true;
    notifyBadge.style.display = "none";
    notifyBadge.setAttribute("aria-hidden", "true");
    notifyBadge.textContent = "0";
    return;
  }
  notifyBadge.hidden = false;
  notifyBadge.style.display = "inline-flex";
  notifyBadge.setAttribute("aria-hidden", "false");
  notifyBadge.textContent = unread > 99 ? "99+" : String(unread);
};

const closeNotifyMenu = () => {
  if (!notifyMenu || !notifyTrigger) {
    return;
  }
  notifyMenu.hidden = true;
  notifyTrigger.setAttribute("aria-expanded", "false");
};

const openNotifyMenu = () => {
  if (!notifyMenu || !notifyTrigger) {
    return;
  }
  notifyMenu.hidden = false;
  notifyTrigger.setAttribute("aria-expanded", "true");
  const latestTs = state.notifications.reduce((max, item) => Math.max(max, Number(item?.ts || 0)), 0);
  if (latestTs > 0) {
    saveNotifyReadTs(latestTs);
  }
  state.unreadNotifications = 0;
  syncNotifyBadge();
};

const appendRunNotification = (runType) => {
  const previous = state.lastRunRequest || {};
  const selectedBank = String(previous?.options?.selectedBank || "").trim();
  const yearPart = state.selectedYear ? ` (${state.selectedYear})` : "";
  let text = "";
  if (runType === "eligibility") {
    text = selectedBank
      ? `Selective eligibility completed: ${selectedBank}${yearPart}`
      : `Full eligibility scan completed${yearPart}`;
  } else {
    text = selectedBank
      ? `Selective final scraping completed: ${selectedBank}${yearPart}`
      : `Full final scraping completed${yearPart}`;
  }
  const now = new Date();
  const message = {
    time: now.toLocaleString(),
    text,
  };
  state.notifications.unshift(message);
  state.notifications = state.notifications.slice(0, 10);
  state.unreadNotifications = Math.min(999, Number(state.unreadNotifications || 0) + 1);
  renderNotifications();
  syncNotifyBadge();
  saveNotifyReadTs(0);
};

const stopRunStatusPolling = () => {
  if (state.statusPollTimer) {
    clearInterval(state.statusPollTimer);
    state.statusPollTimer = null;
  }
};

const applyRunStatus = (runs, announce = false) => {
  const extraction = runs.extraction || {};
  const eligibility = runs.eligibility || {};
  const activeType = extraction.running ? "extraction" : eligibility.running ? "eligibility" : null;

  if (!activeType) {
    state.running = false;
    state.currentRunType = null;
    clearRunStatusSnapshot();
    clearRunUiSnapshot();
    setButtonsDisabled(false);
    stopRunStatusPolling();
    updateStopButtonState();
    setReadinessIdle();
    return;
  }

  const active = runs[activeType] || {};
  const config = runConfigs[activeType] || runConfigs.extraction;
  state.running = true;
  state.currentRunType = activeType;
  saveRunStatusSnapshot(runs);
  if (announce) {
    overlay.classList.remove("complete");
    showOverlay();
  }
  statusLabel.textContent = config.statusText || "Running";
  if (runTitle) {
    runTitle.textContent = config.runTitle || "Running";
  }
  setRunSteps(activeType);

  if (activeType === "extraction" && Array.isArray(active.records) && active.records.length) {
    active.records.forEach((record) => applyExtractionRecord(record));
  }
  if (activeType === "eligibility" && Array.isArray(active.records) && active.records.length) {
    active.records.forEach((record) => applyEligibilityRecord(record));
  }

  const completed = Number(active.completed_banks || 0);
  const total = Number(active.total_banks || 0);
  setReadinessActive(activeType, completed, total);
  const percent = total > 0 ? Math.min(99, Math.round((completed / total) * 100)) : Math.min(95, completed * 3);
  setProgress(percent);

  if (active.current_bank && runBankName) {
    runBankName.textContent = active.current_bank;
  }
  if (active.current_bank && total > 0) {
    progressHint.textContent = `Processing ${active.current_bank} (${completed}/${total})`;
  } else if (active.current_bank) {
    progressHint.textContent = `Processing ${active.current_bank}...`;
  } else if (total > 0) {
    progressHint.textContent = `Processed ${completed}/${total} banks`;
  } else {
    progressHint.textContent = `Processed ${completed} banks`;
  }

  setButtonsDisabled(true);
  syncOverlayToggle();

  const statusKey = `${activeType}:${completed}:${total}:${active.current_bank || ""}`;
  if (announce && state.lastStatusKey !== statusKey) {
    addLog(`Background ${activeType} run in progress (${completed}/${total || "?"}).`);
  }
  state.lastStatusKey = statusKey;
  saveRunUiSnapshot();
};

const loadRunStatus = async (announce = false) => {
  const candidates = [state.statusEndpoint, ...RUN_STATUS_ENDPOINTS].filter(
    (endpoint, index, list) => endpoint && list.indexOf(endpoint) === index
  );
  for (const endpoint of candidates) {
    try {
      const response = await fetch(`${endpoint}?ts=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) {
        if (response.status === 404) {
          continue;
        }
        return;
      }
      const data = await response.json();
      const runs = data.runs || {};
      state.statusEndpoint = endpoint;
      state.statusFetchErrorLogged = false;
      applyRunStatus(runs, announce);
      return;
    } catch (error) {
      continue;
    }
  }
  if (announce && !state.statusFetchErrorLogged) {
    addLog("Run status endpoint not found (404). Check API route in ui_server.py.");
    state.statusFetchErrorLogged = true;
  }
};

const startRunStatusPolling = () => {
  if (state.statusPollTimer) {
    return;
  }
  state.statusPollTimer = setInterval(() => {
    loadRunStatus(false);
  }, 2000);
};

const stopRunProcesses = async () => {
  const activeLabel =
    state.currentRunType === "eligibility"
      ? "eligibility scan"
      : state.currentRunType === "extraction"
      ? "final extraction run"
      : "running process";
  const confirmed = await openConfirmModal(
    "Close process?",
    `Are you sure you want to close the ${activeLabel}? This will terminate execution.`
  );
  if (!confirmed) {
    addLog("Close process cancelled. Run continues in background.");
    return;
  }

  try {
    const response = await fetch("/api/stop-run?type=all");
    console.log(response);
    if (!response.ok) {
      throw new Error("Failed to stop process");
    }
    const data = await response.json();
    const stopped = Array.isArray(data.stopped) ? data.stopped : [];
    if (stopped.length) {
      addLog(`Stopped: ${stopped.join(", ")}`);
    } else {
      addLog("No active scraper process to stop.");
    }
    if (state.runSource) {
      state.runSource.close();
      state.runSource = null;
    }
    stopRunStatusPolling();
    state.running = false;
    state.currentRunType = null;
    clearRunStatusSnapshot();
    clearRunUiSnapshot();
    overlay.classList.remove("complete");
    setButtonsDisabled(false);
    updateStopButtonState();
    hideOverlay();
    await loadRunStatus(true);
  } catch (error) {
    addLog("Failed to stop process. Check ui_server.py logs.");
  }
};

// --- Scorecard data loading ---
const setBanks = (banks) => {
  state.banks = {};
  state.bankOrder = [];
  banks.forEach((bank) => {
    state.banks[bank.key] = bank;
    state.bankOrder.push(bank.key);
  });
  if (!state.bankOrder.length) {
    resetExtractionView("No final-score output yet.");
    return;
  }
  if (!state.totalBanks) {
    state.totalBanks = state.bankOrder.length;
  }
  if (!state.runBankOrder.length) {
    setRunBankOrder(state.bankOrder.map((key) => state.banks[key].name));
  }
  if (!state.activeBankKey && state.bankOrder.length) {
    state.activeBankKey = state.bankOrder[0];
  }
  updateActiveBank(state.activeBankKey);
  updateTierCounts();
  updateBankCounts();
  scheduleOutputPanelHeight();
};

const setEligibilityBanks = (banks) => {
  state.eligibilityBanks = {};
  state.eligibilityOrder = [];
  banks.forEach((bank) => {
    state.eligibilityBanks[bank.key] = bank;
    state.eligibilityOrder.push(bank.key);
  });
  ensureEligibilityCoverageFromSources();
  if (!state.activeEligibilityKey && state.eligibilityOrder.length) {
    state.activeEligibilityKey = state.eligibilityOrder[0];
  }
  if (state.activeEligibilityKey) {
    updateActiveEligibilityBank(state.activeEligibilityKey);
  } else {
    renderEligibilityTabs();
  }
  updateBankCounts();
  scheduleOutputPanelHeight();
};

const ensureEligibilityCoverageFromSources = () => {
  if (!Array.isArray(state.sourceBankNames) || !state.sourceBankNames.length) {
    return;
  }
  let changed = false;
  state.sourceBankNames.forEach((name) => {
    if (!name) {
      return;
    }
    const key = slugify(name);
    if (!state.eligibilityBanks[key]) {
      state.eligibilityBanks[key] = {
        key,
        name,
        totalScore: 0,
        indicators: {
          npl: { value: null, score: null, page: null, sourceUrl: null },
          provision: { value: null, score: null, page: null, sourceUrl: null },
          creditRating: { value: null, score: null, page: null, sourceUrl: null },
        },
      };
      changed = true;
      return;
    }
    if (!state.eligibilityBanks[key].name) {
      state.eligibilityBanks[key].name = name;
      changed = true;
    }
  });

  const ordered = [];
  state.sourceBankNames.forEach((name) => {
    const key = slugify(name);
    if (state.eligibilityBanks[key] && !ordered.includes(key)) {
      ordered.push(key);
    }
  });
  state.eligibilityOrder.forEach((key) => {
    if (state.eligibilityBanks[key] && !ordered.includes(key)) {
      ordered.push(key);
    }
  });

  if (
    changed ||
    ordered.length !== state.eligibilityOrder.length ||
    ordered.some((key, index) => state.eligibilityOrder[index] !== key)
  ) {
    state.eligibilityOrder = ordered;
  }
  if (!state.activeEligibilityKey || !state.eligibilityBanks[state.activeEligibilityKey]) {
    state.activeEligibilityKey = state.eligibilityOrder[0] || null;
  }
};

const applyEligibilityRecord = (record) => {
  if (!record || !record.bank) {
    return;
  }
  const key = slugify(record.bank);
  const existing = state.eligibilityBanks[key] || { key, name: record.bank, indicators: {} };
  existing.name = record.bank;
  existing.year = record.year;
  existing.indicators.npl = {
    value: record.npl,
    score: record.nplScore,
    page: record.nplPage,
    sourceUrl: record.nplSource,
  };
  existing.indicators.creditRating = {
    value: record.rating,
    score: record.ratingScore,
    page: record.ratingPage,
    sourceUrl: record.ratingSource,
  };
  state.eligibilityBanks[key] = existing;
  if (!state.eligibilityOrder.includes(key)) {
    state.eligibilityOrder.push(key);
  }
  if (!state.activeEligibilityKey) {
    state.activeEligibilityKey = key;
  }
  renderEligibilityTabs();
  if (state.outputMode === "eligibility") {
    updateActiveEligibilityBank(key);
  } else if (state.activeEligibilityKey) {
    renderEligibilityComparison(state.activeEligibilityKey);
  }
};

const applyExtractionRecord = (record) => {
  if (!record || !record.key) {
    return;
  }
  state.banks[record.key] = record;
  if (!state.bankOrder.includes(record.key)) {
    state.bankOrder.push(record.key);
  }
  if (!state.activeBankKey) {
    state.activeBankKey = record.key;
  }
  renderBankTabs();
  if (state.outputMode === "extraction") {
    updateActiveBank(record.key);
  } else if (state.activeBankKey) {
    renderComparison(state.activeBankKey);
  }
  updateTierCounts();
  updateBankCounts();
  scheduleOutputPanelHeight();
};

const normalizeBankList = (names) =>
  Array.from(new Set((names || []).map((name) => String(name || "").trim()).filter(Boolean))).sort((a, b) =>
    a.localeCompare(b)
  );

const closeBankMenus = () => {
  if (selectedEligibilityMenu) {
    selectedEligibilityMenu.hidden = true;
  }
  if (selectedFinalMenu) {
    selectedFinalMenu.hidden = true;
  }
  if (runSelectedEligibilityBtn) {
    runSelectedEligibilityBtn.setAttribute("aria-expanded", "false");
  }
  if (runSelectedFinalBtn) {
    runSelectedFinalBtn.setAttribute("aria-expanded", "false");
  }
};

const populateBankMenu = (menuEl, names, currentName, onPick, emptyLabel) => {
  if (!menuEl) {
    return;
  }
  menuEl.innerHTML = "";
  const normalized = normalizeBankList(names);
  if (!normalized.length) {
    const empty = document.createElement("button");
    empty.type = "button";
    empty.className = "year-option";
    empty.textContent = emptyLabel;
    empty.disabled = true;
    menuEl.appendChild(empty);
    return;
  }
  normalized.forEach((name) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "year-option";
    option.textContent = name;
    option.dataset.bank = name;
    if (currentName && name === currentName) {
      option.classList.add("active");
    }
    option.addEventListener("click", () => onPick(name));
    menuEl.appendChild(option);
  });
};

// --- API calls: sources ---
const loadSources = async () => {
  try {
    const sourcesUrl = state.selectedYear
      ? `/api/sources?year=${encodeURIComponent(String(state.selectedYear))}`
      : "/api/sources";
    const response = await fetch(sourcesUrl);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    const allSources = Array.isArray(data.sources) ? data.sources : [];
    const eligibleSources = Array.isArray(data.eligible_sources) ? data.eligible_sources : [];
    state.sourceTotalBanks = allSources.length;
    state.sourceEligibleBanks = eligibleSources.length;
    state.sourceBankNames = allSources
      .map((entry) => (entry && entry.bank ? String(entry.bank).trim() : ""))
      .filter(Boolean);
    const sourceForYear = eligibleSources.length ? eligibleSources : allSources;
    const years = Array.from(
      new Set(
        sourceForYear
          .map((entry) => Number(entry?.year))
          .filter((year) => Number.isFinite(year) && year > 0)
      )
    ).sort((a, b) => b - a);
    syncYearDropdown(years);
    state.selectiveEligibilityBanks = normalizeBankList(allSources.map((entry) => entry?.bank));
    state.selectiveFinalBanks = normalizeBankList(eligibleSources.map((entry) => entry?.bank));
    if (state.selectedEligibilityBank && !state.selectiveEligibilityBanks.includes(state.selectedEligibilityBank)) {
      state.selectedEligibilityBank = null;
    }
    if (state.selectedFinalBank && !state.selectiveFinalBanks.includes(state.selectedFinalBank)) {
      state.selectedFinalBank = null;
    }
    if (selectedEligibilityLabel) {
      selectedEligibilityLabel.textContent = state.selectedEligibilityBank || "Select bank";
    }
    if (selectedFinalLabel) {
      selectedFinalLabel.textContent = state.selectedFinalBank || "Select eligible bank";
    }
    populateBankMenu(
      selectedEligibilityMenu,
      state.selectiveEligibilityBanks,
      state.selectedEligibilityBank,
      (picked) => {
        state.selectedEligibilityBank = picked;
        if (selectedEligibilityLabel) {
          selectedEligibilityLabel.textContent = picked;
        }
        closeBankMenus();
        startSelectedEligibilityRun();
      },
      "No banks for selected year"
    );
    populateBankMenu(
      selectedFinalMenu,
      state.selectiveFinalBanks,
      state.selectedFinalBank,
      (picked) => {
        state.selectedFinalBank = picked;
        if (selectedFinalLabel) {
          selectedFinalLabel.textContent = picked;
        }
        closeBankMenus();
        startSelectedFinalRun();
      },
      "No eligible banks for selected year"
    );
    if (eligibleSources.length) {
      setRunBankOrder(eligibleSources.map((entry) => entry.bank));
    } else if (allSources.length) {
      setRunBankOrder(allSources.map((entry) => entry.bank));
    }
    ensureEligibilityCoverageFromSources();
    if (state.outputMode === "eligibility") {
      if (state.activeEligibilityKey) {
        updateActiveEligibilityBank(state.activeEligibilityKey);
      } else {
        renderEligibilityTabs();
        renderEligibilityComparison(null);
      }
    }
    updateBankCounts();
  } catch (error) {
    return;
  }
};

if (annualYearTrigger && annualYearMenu) {
  annualYearTrigger.addEventListener("click", () => {
    if (annualYearMenu.hidden) {
      openYearMenu();
    } else {
      closeYearMenu();
    }
  });

  annualYearMenu.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".year-option") : null;
    if (!target) {
      return;
    }
    const nextYear = Number(target.dataset.year);
    setSelectedYear(nextYear);
    Array.from(annualYearMenu.querySelectorAll(".year-option")).forEach((node) => {
      node.classList.toggle("active", node === target);
    });
    closeYearMenu();
    if (state.selectedYear) {
      addLog(`Year selected: ${state.selectedYear}`);
    }
    loadSources();
  });

  document.addEventListener("click", (event) => {
    if (!yearPicker || yearPicker.contains(event.target)) {
      return;
    }
    closeYearMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeYearMenu();
      closeBankMenus();
      closeNotifyMenu();
    }
  });
}

if (runSelectedEligibilityBtn && selectedEligibilityMenu) {
  runSelectedEligibilityBtn.addEventListener("click", () => {
    const willOpen = selectedEligibilityMenu.hidden;
    closeBankMenus();
    if (willOpen) {
      selectedEligibilityMenu.hidden = false;
      runSelectedEligibilityBtn.setAttribute("aria-expanded", "true");
    }
  });
}

if (runSelectedFinalBtn && selectedFinalMenu) {
  runSelectedFinalBtn.addEventListener("click", () => {
    const willOpen = selectedFinalMenu.hidden;
    closeBankMenus();
    if (willOpen) {
      selectedFinalMenu.hidden = false;
      runSelectedFinalBtn.setAttribute("aria-expanded", "true");
    }
  });
}

if (notifyTrigger && notifyMenu) {
  notifyTrigger.addEventListener("click", () => {
    const willOpen = notifyMenu.hidden;
    closeNotifyMenu();
    if (willOpen) {
      refreshNotifications().finally(() => openNotifyMenu());
      return;
    }
  });
}

document.addEventListener("click", (event) => {
  const inEligibilityPicker = selectedEligibilityPicker && selectedEligibilityPicker.contains(event.target);
  const inFinalPicker = selectedFinalPicker && selectedFinalPicker.contains(event.target);
  const inNotifyPicker = notifyPicker && notifyPicker.contains(event.target);
  if (!inEligibilityPicker && !inFinalPicker) {
    closeBankMenus();
  }
  if (!inNotifyPicker) {
    closeNotifyMenu();
  }
});

// --- API calls: scorecards ---
const loadScorecards = async () => {
  try {
    const response = await fetch("/api/scorecards");
    if (!response.ok) {
      throw new Error("Failed to load scorecards");
    }
    const data = await response.json();
    if (data.banks && data.banks.length) {
      setBanks(data.banks);
      scheduleOutputPanelHeight();
      return;
    }
    resetExtractionView("No final-score output yet.");
  } catch (error) {
    resetExtractionView("Scorecard data not available yet.");
    addLog("Scorecard data not available yet. Run extraction to stream live results.");
  }
};

const loadEligibilityScorecards = async () => {
  try {
    const response = await fetch("/api/eligibility-scorecards");
    if (!response.ok) {
      throw new Error("Failed to load eligibility scorecards");
    }
    const data = await response.json();
    if (data.banks && data.banks.length) {
      setEligibilityBanks(data.banks);
      scheduleOutputPanelHeight();
      return;
    }
    if (eligibilityBody) {
      eligibilityBody.innerHTML = '<div class="empty-state">No eligibility scan data yet.</div>';
    }
  } catch (error) {
    return;
  }
};

// --- Event listeners ---
closeOverlay.addEventListener("click", () => {
  hideOverlay();
  if (scoreSection) {
    scoreSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

if (openOverlayBtn) {
  openOverlayBtn.addEventListener("click", () => {
    if (openOverlayBtn.disabled) {
      return;
    }
    showOverlay();
  });
}

if (runBtn) {
  runBtn.addEventListener("click", startRun);
}

if (runAgainBtn) {
  runAgainBtn.addEventListener("click", runPreviousMode);
}

if (eligibilityBtn) {
  eligibilityBtn.addEventListener("click", startEligibilityRun);
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", logoutUser);
}

if (stopRunBtn) {
  stopRunBtn.addEventListener("click", stopRunProcesses);
}

if (confirmOkBtn) {
  confirmOkBtn.addEventListener("click", () => closeConfirmModal(true));
}

if (confirmCancelBtn) {
  confirmCancelBtn.addEventListener("click", () => closeConfirmModal(false));
}

if (confirmModal) {
  confirmModal.addEventListener("click", (event) => {
    if (event.target === confirmModal) {
      closeConfirmModal(false);
    }
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && confirmModal && confirmModal.classList.contains("show")) {
    closeConfirmModal(false);
  }
});

if (viewScorecardBtn && scoreSection) {
  viewScorecardBtn.addEventListener("click", () => {
    scoreSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

if (bankTabs) {
  bankTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".bank-tab");
    if (!button) {
      return;
    }
    state.hasPickedFinalBank = true;
    updateActiveBank(button.dataset.bank);
  });
}

if (eligibilityTabs) {
  eligibilityTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".bank-tab");
    if (!button) {
      return;
    }
    state.hasPickedEligibilityBank = true;
    updateActiveEligibilityBank(button.dataset.bank);
  });
}

if (scoreList) {
  scoreList.addEventListener("click", (event) => {
    const item = event.target.closest(".score-item");
    if (!item) {
      return;
    }
    if (state.outputMode === "eligibility") {
      state.hasPickedEligibilityBank = true;
      updateActiveEligibilityBank(item.dataset.bank);
    } else {
      state.hasPickedFinalBank = true;
      updateActiveBank(item.dataset.bank);
    }
  });
  scoreList.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " " && event.key !== "Spacebar") {
      return;
    }
    const item = event.target.closest(".score-item");
    if (!item) {
      return;
    }
    event.preventDefault();
    if (state.outputMode === "eligibility") {
      state.hasPickedEligibilityBank = true;
      updateActiveEligibilityBank(item.dataset.bank);
    } else {
      state.hasPickedFinalBank = true;
      updateActiveBank(item.dataset.bank);
    }
  });
}

function setOutputPanelHeight() {
  if (!outputPanels) {
    return;
  }
  const activePanel = outputPanels.querySelector(".output-panel.active");
  if (!activePanel) {
    return;
  }
  outputPanels.style.height = `${activePanel.offsetHeight}px`;
}

const scheduleOutputPanelHeight = () => {
  if (!outputPanels) {
    return;
  }
  const recompute = () => {
    setOutputPanelHeight();
  };
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      recompute();
      setTimeout(recompute, 120);
    });
  });
};

function setOutputMode(mode) {
  if (!outputTabs || !outputPanels) {
    state.outputMode = mode;
    return;
  }
  state.outputMode = mode;
  outputTabs.querySelectorAll(".output-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  outputPanels.querySelectorAll(".output-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.mode === mode);
  });
  if (mode === "eligibility") {
    if (!state.activeEligibilityKey && state.eligibilityOrder.length) {
      state.activeEligibilityKey = state.eligibilityOrder[0];
    }
    if (state.activeEligibilityKey) {
      updateActiveEligibilityBank(state.activeEligibilityKey);
    }
    if (comparisonSub) {
      comparisonSub.textContent = "Ranked by eligibility score";
    }
    if (featureSub) {
      featureSub.textContent = "3 eligibility indicators with benchmark scoring";
    }
    if (indicatorCountEl) {
      indicatorCountEl.textContent = "3";
    }
    if (indicatorLabelEl) {
      indicatorLabelEl.textContent = "Eligibility benchmarked";
    }
    renderEligibilityComparison(state.activeEligibilityKey);
  } else {
    if (comparisonSub) {
      comparisonSub.textContent = "Ranked by 12-indicator score";
    }
    if (featureSub) {
      featureSub.textContent = "12 regulatory indicators with benchmark scoring";
    }
    if (indicatorCountEl) {
      indicatorCountEl.textContent = "12";
    }
    if (indicatorLabelEl) {
      indicatorLabelEl.textContent = "Regulatory benchmarked";
    }
    if (state.activeBankKey && state.banks[state.activeBankKey]) {
      updateActiveBank(state.activeBankKey);
      renderComparison(state.activeBankKey);
    } else {
      resetExtractionView("No final-score output yet.");
    }
  }
  updateBankCounts();
  scheduleOutputPanelHeight();
}

if (outputTabs) {
  outputTabs.addEventListener("click", (event) => {
    const button = event.target.closest(".output-tab");
    if (!button) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    setOutputMode(button.dataset.mode || "extraction");
  });
}

if (outputTabs) {
  outputTabs.addEventListener(
    "mousedown",
    (event) => {
      if (event.target.closest(".output-tab")) {
        event.preventDefault();
      }
    },
    true
  );
  outputTabs.addEventListener(
    "mouseup",
    (event) => {
      if (event.target.closest(".output-tab")) {
        event.preventDefault();
      }
    },
    true
  );
}

// --- Background parallax for glow orbs ---
const glows = Array.from(document.querySelectorAll(".bg-glows .glow"));
if (glows.length) {
  let mouseX = 0;
  let mouseY = 0;
  let ticking = false;

  const updateGlow = () => {
    const scrollFactor = Math.min(window.scrollY / window.innerHeight, 1.5);
    glows.forEach((glow) => {
      const depth = Number(glow.dataset.depth || 10);
      const x = mouseX * depth;
      const y = mouseY * depth + scrollFactor * depth * 4;
      glow.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    });
    ticking = false;
  };

  const requestUpdate = () => {
    if (!ticking) {
      window.requestAnimationFrame(updateGlow);
      ticking = true;
    }
  };

  window.addEventListener("mousemove", (event) => {
    mouseX = (event.clientX / window.innerWidth - 0.5) * 2;
    mouseY = (event.clientY / window.innerHeight - 0.5) * 2;
    requestUpdate();
  });

  window.addEventListener("scroll", () => {
    requestUpdate();
  }, { passive: true });

  updateGlow();
}

// --- Initial boot ---
window.addEventListener("load", () => {
  enforceFreshLoginOnReload().then((redirecting) => {
    if (redirecting) {
      return;
    }
    document.body.classList.add("loaded");
    refreshNotifications();
    const uiSnapshot = loadRunUiSnapshot();
    if (uiSnapshot && uiSnapshot.running) {
      state.running = true;
      state.currentRunType = uiSnapshot.currentRunType || "extraction";
      setButtonsDisabled(true);
      statusLabel.textContent = uiSnapshot.statusLabel || "Running";
      if (runBankName && uiSnapshot.runBank) {
        runBankName.textContent = uiSnapshot.runBank;
      }
      if (progressHint) {
        progressHint.textContent = uiSnapshot.progressHint || "Resuming previous run state...";
      }
      const progressMatch = String(uiSnapshot.progressText || "").match(/(\d+)/);
      const restoredProgress = progressMatch ? Number(progressMatch[1]) : 0;
      setProgress(Number.isFinite(restoredProgress) ? restoredProgress : 0);
    }
    const snapshot = loadRunStatusSnapshot();
    if (snapshot && snapshot.runs) {
      applyRunStatus(snapshot.runs, false);
    }
    loadRunStatus(false);
    startRunStatusPolling();
    loadSources();
    loadScorecards();
    loadEligibilityScorecards();
    scheduleOutputPanelHeight();
    if (!state.running) {
      hideOverlay();
      clearRunUiSnapshot();
      clearRunStatusSnapshot();
    }
    syncOverlayToggle();
  });
});

window.addEventListener("resize", () => {
  scheduleOutputPanelHeight();
});

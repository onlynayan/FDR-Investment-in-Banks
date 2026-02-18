// --- DOM references ---
const runBtn = document.getElementById("runBtn");
const runBtnHero = document.getElementById("runBtnHero");
const runAgainBtn = document.getElementById("runAgainBtn");
const viewScorecardBtn = document.getElementById("viewScorecard");
const scoreSection = document.getElementById("scoreSection");
const overlay = document.getElementById("overlay");
const progressBar = document.getElementById("progressBar");
const progressValue = document.getElementById("progressValue");
const progressHint = document.getElementById("progressHint");
const statusLabel = document.getElementById("statusLabel");
const stepItems = Array.from(document.querySelectorAll("#stepList .step"));
const logList = document.getElementById("logList");
const closeOverlay = document.getElementById("closeOverlay");
const openOverlayBtn = document.getElementById("openOverlay");
const confidenceRing = document.getElementById("confidenceRing");
const healthValue = document.getElementById("healthValue");
const selectedBankChip = document.getElementById("selectedBankChip");
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
const strongCountEl = document.getElementById("strongCount");
const moderateCountEl = document.getElementById("moderateCount");
const weakCountEl = document.getElementById("weakCount");
const indicatorDonut = document.getElementById("indicatorDonut");
const indicatorDonutValue = document.getElementById("indicatorDonutValue");

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

// --- Run pipeline hints ---
const stepHints = [
  "Selecting bank seeds and report URLs",
  "Downloading report PDF",
  "Scanning pages and running OCR",
  "Extracting 12 indicators",
  "Applying regulatory benchmarks",
  "Building peer comparison",
  "Exporting scorecard output",
];

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
const runButtons = [runBtn, runBtnHero, runAgainBtn].filter(Boolean);

// --- App state ---
const state = {
  banks: {},
  bankOrder: [],
  activeBankKey: null,
  totalBanks: 0,
  runSource: null,
  running: false,
  currentBankIndex: 0,
  runStart: 0,
  runBankOrder: [],
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

// --- Progress bar helpers ---
const setProgress = (value) => {
  const clamped = Math.max(0, Math.min(100, value));
  progressBar.style.width = `${Math.round(clamped)}%`;
  progressValue.textContent = `${Math.round(clamped)}%`;
  updateRunButtonLabel(clamped);
};

const setStepActive = (index) => {
  stepItems.forEach((step, idx) => {
    step.classList.toggle("active", idx === index);
    step.classList.toggle("done", idx < index);
  });
  progressHint.textContent = stepHints[index] || "Running";
};

const resetSteps = () => {
  stepItems.forEach((step) => {
    step.classList.remove("active", "done");
  });
  if (stepItems[0]) {
    stepItems[0].classList.add("active");
  }
};

// --- Button state helpers ---
const setButtonsDisabled = (disabled) => {
  runButtons.forEach((button) => {
    button.disabled = disabled;
    if (button === runBtn && !disabled) {
      button.textContent = "Run extraction";
    }
    if (button === runBtn && disabled) {
      updateRunButtonLabel(0);
    }
  });
};

// --- Run button label helpers ---
const updateRunButtonLabel = (progress) => {
  if (!runBtn) {
    return;
  }
  if (!state.running) {
    runBtn.textContent = "Run extraction";
    return;
  }
  const value = Math.round(progress ?? 0);
  runBtn.textContent = `Running ${value}%`;
};

// --- Overlay visibility helpers ---
const syncOverlayToggle = () => {
  if (!openOverlayBtn) {
    return;
  }
  const isHidden = !overlay.classList.contains("show");
  const shouldShow = isHidden && (state.running || overlay.classList.contains("complete"));
  openOverlayBtn.classList.toggle("visible", shouldShow);
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

// --- Value formatting and scoring helpers ---
const formatValue = (value, key) => {
  if (value === null || value === undefined || value === "") {
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

// --- UI rendering: feature table ---
const renderFeatureRows = (bankKey) => {
  const bank = state.banks[bankKey];
  featureBody.innerHTML = "";

  indicatorBenchmarks.forEach((indicator) => {
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
    const scoreText = entry.score ?? "N/A";
    scoreCell.textContent = scoreText;
    if (scoreText === "N/A") {
      scoreCell.classList.add("na");
    }

    const pageCell = document.createElement("span");
    pageCell.className = "page-cell";
    const pageValue = entry.page ?? "";
    const pageText = pageValue === "" ? "N/A" : pageValue;
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
    featureBody.appendChild(row);
  });
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
    bar.appendChild(barFill);

    scoreItem.append(head, bar);
    scoreList.appendChild(scoreItem);
  });

  const activeItem = scoreList.querySelector(".score-item.active");
  if (activeItem) {
    activeItem.scrollIntoView({ block: "nearest" });
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

// --- UI rendering: active bank summary ---
const updateActiveBank = (bankKey) => {
  if (!state.banks[bankKey]) {
    return;
  }
  state.activeBankKey = bankKey;
  const bank = state.banks[bankKey];

  selectedBankChip.textContent = bank.name;
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
  renderComparison(bankKey);
  renderBankTabs();
  updateTierCounts();
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
  if (processingMatch) {
    const bankName = processingMatch[1].trim();
    runBankName.textContent = bankName;
    const runIndex = findRunBankIndex(bankName);
    if (runIndex >= 0) {
      state.currentBankIndex = runIndex;
    } else {
      state.currentBankIndex = state.runBankOrder.length;
      state.runBankOrder.push(bankName);
      state.totalBanks = Math.max(state.totalBanks, state.runBankOrder.length);
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
    setStepActive(2);
    updateProgressForStep(2);
    return;
  }

  if (line.startsWith("Scanning pages")) {
    setStepActive(3);
    updateProgressForStep(3);
    return;
  }

  if (line.startsWith("Total score")) {
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
const finalizeRun = () => {
  overlay.classList.add("complete");
  statusLabel.textContent = "Complete";
  setProgress(100);
  progressHint.textContent = "Run complete. Scorecards updated.";
  resultValue.textContent = "All banks processed";
  resultMeta.textContent = "Scorecards refreshed from output XLSX files";
  if (resultDelta && state.activeBankKey) {
    const median = getMedianScore();
    const current = getTotalScore(state.banks[state.activeBankKey]);
    if (median !== null && typeof current === "number") {
      const delta = current - median;
      const sign = delta >= 0 ? "+" : "";
      resultDelta.textContent = `Peer median delta: ${sign}${delta}`;
    } else {
      resultDelta.textContent = "Peer median delta: N/A";
    }
  }
  setButtonsDisabled(false);
  state.running = false;
  syncOverlayToggle();
};

// --- Start scraper run (SSE stream) ---
const startRun = () => {
  if (state.running) {
    return;
  }
  if (state.runSource) {
    state.runSource.close();
  }

  state.running = true;
  overlay.classList.add("show");
  overlay.classList.remove("complete");
  document.body.classList.add("locked");
  syncOverlayToggle();
  setButtonsDisabled(true);
  statusLabel.textContent = "Running";
  state.currentBankIndex = 0;
  setProgress(0);
  progressHint.textContent = "Waiting for scraper";
  resetSteps();

  state.runStart = Date.now();
  addLog("Run started: python scraper.py");

  const source = new EventSource("/api/run");
  state.runSource = source;

  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "log") {
        handleLogLine(payload.line);
      }
      if (payload.type === "complete") {
        source.close();
        finalizeRun();
        loadScorecards();
      }
      if (payload.type === "error") {
        addLog(`Error: ${payload.message}`);
      }
    } catch (error) {
      addLog(event.data);
    }
  };

  source.onerror = () => {
    addLog("Connection lost. Make sure ui_server.py is running.");
    source.close();
    setButtonsDisabled(false);
    state.running = false;
  };
};

// --- Scorecard data loading ---
const setBanks = (banks) => {
  state.banks = {};
  state.bankOrder = [];
  banks.forEach((bank) => {
    state.banks[bank.key] = bank;
    state.bankOrder.push(bank.key);
  });
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
};

// --- API calls: sources ---
const loadSources = async () => {
  try {
    const response = await fetch("/api/sources");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (Array.isArray(data.sources) && data.sources.length) {
      setRunBankOrder(data.sources.map((entry) => entry.bank));
    }
  } catch (error) {
    return;
  }
};

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
      return;
    }
  } catch (error) {
    addLog("Scorecard data not available yet. Run the scraper to generate XLSX files.");
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
    showOverlay();
  });
}

runButtons.forEach((button) => {
  button.addEventListener("click", startRun);
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
    updateActiveBank(button.dataset.bank);
  });
}

if (scoreList) {
  scoreList.addEventListener("click", (event) => {
    const item = event.target.closest(".score-item");
    if (!item) {
      return;
    }
    updateActiveBank(item.dataset.bank);
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
    updateActiveBank(item.dataset.bank);
  });
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
  document.body.classList.add("loaded");
  loadSources();
  loadScorecards();
  syncOverlayToggle();
});

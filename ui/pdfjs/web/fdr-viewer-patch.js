// Developed by Nayan
// Custom search behavior for FDR links:
// - focus on target page
// - avoid global highlight spam
// - keep phrase matching for cleaner, exact-like selection
(function () {
  const parseHash = () => {
    const raw = window.location.hash ? window.location.hash.slice(1) : "";
    return new URLSearchParams(raw);
  };

  const waitForApp = (cb) => {
    const tick = () => {
      const app = window.PDFViewerApplication;
      if (app && app.eventBus && app.pdfViewer) {
        cb(app);
        return;
      }
      window.setTimeout(tick, 120);
    };
    tick();
  };

  const showFocusNotice = (message) => {
    const box = document.createElement("div");
    box.textContent = message;
    box.style.position = "fixed";
    box.style.right = "14px";
    box.style.top = "54px";
    box.style.zIndex = "9999";
    box.style.padding = "8px 10px";
    box.style.borderRadius = "10px";
    box.style.background = "rgba(8, 12, 18, 0.88)";
    box.style.border = "1px solid rgba(255,255,255,0.2)";
    box.style.color = "#d7e6f9";
    box.style.font = "12px/1.3 'Segoe UI', sans-serif";
    box.style.boxShadow = "0 12px 24px rgba(0,0,0,0.35)";
    box.style.maxWidth = "320px";
    box.style.pointerEvents = "none";
    document.body.appendChild(box);
    window.setTimeout(() => {
      if (box && box.parentNode) {
        box.parentNode.removeChild(box);
      }
    }, 3200);
  };

  const runFocusedSearch = (app, opts) => {
    const page = Number(opts.page);
    if (Number.isFinite(page) && page > 0) {
      app.page = page;
    }

    const query = String(opts.search || "").trim();
    if (!query) {
      return;
    }

    const hasLetters = /[A-Za-z]/.test(query);
    const singleLetter = /^[A-Za-z]$/.test(query);
    const hasTokenChars = /[+\-/.%]/.test(query);

    // One-letter tokens like "A" create excessive false positives in PDF text.
    // For these, keep page targeting only and avoid noisy auto-highlighting.
    if (singleLetter) {
      return;
    }

    const findOptions = {
      query,
      phraseSearch: true,
      caseSensitive: hasLetters && query === query.toUpperCase(),
      // For short rating values like A / AA / A+, keep token matching flexible.
      entireWord: hasLetters && !singleLetter && !hasTokenChars,
      highlightAll: false,
      findPrevious: false,
      matchDiacritics: false,
    };

    const escapeRe = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pageHasQuery = async () => {
      if (!Number.isFinite(page) || page <= 0 || !app.pdfDocument) {
        return false;
      }
      try {
        const pdfPage = await app.pdfDocument.getPage(page);
        const textContent = await pdfPage.getTextContent();
        const pageText = (textContent.items || [])
          .map((item) => String(item.str || ""))
          .join(" ");
        if (!pageText.trim()) {
          return false;
        }
        const haystack = findOptions.caseSensitive ? pageText : pageText.toLowerCase();
        const needle = findOptions.caseSensitive ? query : query.toLowerCase();
        if (findOptions.entireWord) {
          const rx = new RegExp(`(^|[^A-Za-z0-9])${escapeRe(needle)}([^A-Za-z0-9]|$)`);
          return rx.test(haystack);
        }
        return haystack.includes(needle);
      } catch (_err) {
        return false;
      }
    };

    pageHasQuery().then((existsOnTargetPage) => {
      // If match is absent on target page (often image-only/OCR gap), do not jump elsewhere.
      if (!existsOnTargetPage) {
        if (Number.isFinite(page) && page > 0) {
          app.page = page;
        }
        showFocusNotice("Focused target page. Match not found on this page; highlight skipped.");
        return;
      }
      app.eventBus.dispatch("find", findOptions);
      // Second pass after rendering settles improves page-targeted selection stability.
      window.setTimeout(() => app.eventBus.dispatch("find", findOptions), 220);
    });
  };

  const params = parseHash();
  const hasSearch = Boolean(params.get("search"));
  const searchSkipped = params.get("searchskipped") === "ambiguous";
  const focusOnly = params.get("focus") === "1";
  if (!hasSearch && !focusOnly) {
    return;
  }

  if (hasSearch) {
    // Reduce visual noise: keep only the currently selected match highlighted.
    // PDF.js still finds across pages internally, but users won't see dozens of highlights.
    const style = document.createElement("style");
    style.textContent = `
      .textLayer .highlight {
        background: transparent !important;
        box-shadow: none !important;
      }
      .textLayer .highlight.selected {
        background: rgba(255, 214, 74, 0.65) !important;
        border-radius: 2px;
        box-shadow: 0 0 0 1px rgba(179, 138, 15, 0.55) inset;
      }
    `;
    document.head.appendChild(style);
  }

  waitForApp((app) => {
    const start = () => {
      const page = params.get("page");
      if (page) {
        const pageNum = Number(page);
        if (Number.isFinite(pageNum) && pageNum > 0) {
          app.page = pageNum;
        }
      }
      if (hasSearch) {
        runFocusedSearch(app, {
          page,
          search: params.get("search"),
        });
      } else if (searchSkipped) {
        showFocusNotice("Focused target page. Exact highlight skipped for ambiguous value.");
      }
    };

    if (app.initializedPromise && typeof app.initializedPromise.then === "function") {
      app.initializedPromise.then(start);
    } else {
      start();
    }
  });
})();

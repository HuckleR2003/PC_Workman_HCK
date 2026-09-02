/* Scaling Laws — roadmap interaction layer
   The full roadmap exists in static HTML for crawlability.
   This file only filters, deep-links and adds presentation mode.
*/
(() => {
  "use strict";

  const body = document.body;
  const root = document.documentElement;
  const cards = [...document.querySelectorAll("[data-roadmap-item]")];
  const categorySections = [...document.querySelectorAll("[data-roadmap-category]")];
  const categoryButtons = [...document.querySelectorAll("[data-category-filter]")];
  const laneButtons = [...document.querySelectorAll("[data-lane-filter]")];
  const search = document.querySelector("[data-roadmap-search]");
  const results = document.querySelector("[data-roadmap-results]");
  const empty = document.querySelector("[data-roadmap-empty]");
  const presentation = document.querySelector("[data-presentation-toggle]");
  const copyView = document.querySelector("[data-copy-view]");
  const versionNode = document.querySelector("[data-roadmap-version]");

  // The Polish page is the same markup with <html lang="pl">, so the strings this file
  // builds at runtime follow the document language instead of staying English.
  const isPl = root.lang === "pl";
  const t = {
    shown: (n) => isPl
      ? `${n} ${n === 1 ? "funkcja widoczna" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "funkcje widoczne" : "funkcji widocznych"}`
      : `${n} feature${n === 1 ? "" : "s"} shown`,
    category: isPl ? "kategoria" : "category",
    lane: isPl ? "tor" : "lane",
    search: isPl ? "szukaj" : "search",
    copied: isPl ? "Skopiowano" : "Copied"
  };

  const state = {
    category: "all",
    lane: "all",
    query: ""
  };

  const params = new URLSearchParams(window.location.search);
  if (params.get("category")) state.category = params.get("category");
  if (params.get("lane")) state.lane = params.get("lane");
  if (params.get("q")) state.query = params.get("q");

  const normalize = (value) =>
    (value || "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/\p{Diacritic}/gu, "");

  const apply = () => {
    const q = normalize(state.query);
    let visibleCount = 0;

    cards.forEach((card) => {
      const categoryMatch = state.category === "all" || card.dataset.category === state.category;
      const laneMatch = state.lane === "all" || card.dataset.lane === state.lane;
      const searchMatch = !q || normalize(card.dataset.search).includes(q);
      const show = categoryMatch && laneMatch && searchMatch;

      card.hidden = !show;
      if (show) visibleCount += 1;
    });

    categorySections.forEach((section) => {
      const hasVisible = [...section.querySelectorAll("[data-roadmap-item]")]
        .some((card) => !card.hidden);
      section.hidden = !hasVisible;
    });

    categoryButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.categoryFilter === state.category);
    });

    laneButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.laneFilter === state.lane);
    });

    if (search && search.value !== state.query) search.value = state.query;

    if (results) {
      const parts = [t.shown(visibleCount)];
      if (state.category !== "all") parts.push(`${t.category}: ${state.category}`);
      if (state.lane !== "all") parts.push(`${t.lane}: ${state.lane}`);
      if (state.query) parts.push(`${t.search}: “${state.query}”`);
      results.textContent = parts.join(" / ");
    }

    if (empty) empty.hidden = visibleCount !== 0;

    const nextParams = new URLSearchParams();
    if (state.category !== "all") nextParams.set("category", state.category);
    if (state.lane !== "all") nextParams.set("lane", state.lane);
    if (state.query) nextParams.set("q", state.query);

    const query = nextParams.toString();
    history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
  };

  categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.category = button.dataset.categoryFilter || "all";
      apply();
    });
  });

  laneButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.lane = button.dataset.laneFilter || "all";
      apply();
    });
  });

  if (search) {
    search.addEventListener("input", () => {
      state.query = search.value.trim();
      apply();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && document.activeElement !== search) {
        event.preventDefault();
        search.focus();
      }
      if (event.key === "Escape" && document.activeElement === search) {
        search.value = "";
        state.query = "";
        search.blur();
        apply();
      }
    });
  }

  if (presentation) {
    presentation.addEventListener("click", () => {
      const active = body.classList.toggle("is-presentation");
      presentation.classList.toggle("is-active", active);
      presentation.setAttribute("aria-pressed", String(active));

      if (active && state.category === "all") {
        state.category = "hardware-compute";
        apply();
      }
    });
  }

  if (copyView) {
    copyView.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(window.location.href);
        const original = copyView.textContent;
        copyView.textContent = t.copied;
        window.setTimeout(() => copyView.textContent = original, 1200);
      } catch {
        // Clipboard can be blocked in insecure contexts. The URL still remains shareable.
      }
    });
  }

  // roadmap.json stays the authoring source of truth.
  // The page contains a generated static snapshot for crawlers and no-JS users.
  if (versionNode) {
    fetch("../assets/data/roadmap.json", { credentials: "same-origin" })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (!data || !data.version) return;
        const htmlVersion = versionNode.dataset.roadmapVersion;
        if (htmlVersion !== data.version) {
          console.warn(
            `[Scaling Laws roadmap] Static HTML snapshot is ${htmlVersion}, JSON is ${data.version}. Regenerate the page so no-JS crawlers see the new state.`
          );
        }
      })
      .catch(() => {});
  }

  apply();
})();

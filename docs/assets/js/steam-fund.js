/* HCK Labs: "Scaling Laws on Steam" counter pill in the site header.
   One source of truth: /assets/data/steam-fund.json. Update "raised" there and every page follows.
   Progressive enhancement only: no data, no pill, nothing breaks. */
(function () {
  "use strict";
  if (window.__hckSteamFund) return;
  window.__hckSteamFund = true;

  var DEFAULTS = { raised: 0, goal: 100, currency: "$", ends: "2026-10-19",
                   url: "https://github.com/sponsors/HuckleR2003" };

  var polish = (document.documentElement.lang || "").toLowerCase().indexOf("pl") === 0;

  function css() {
    if (document.getElementById("hck-fund-style")) return;
    var s = document.createElement("style");
    s.id = "hck-fund-style";
    s.textContent =
      ".hck-fund{display:inline-flex;align-items:center;gap:8px;flex:0 0 auto;margin:0 10px;padding:5px 11px 5px 9px;" +
      "border:1px solid rgba(163,230,53,.42);border-radius:999px;background:linear-gradient(135deg,rgba(163,230,53,.10),rgba(27,40,56,.55));" +
      "color:#e8f5d0;font:700 11.5px/1.1 Inter,system-ui,sans-serif;letter-spacing:.02em;text-decoration:none;white-space:nowrap;" +
      "transition:border-color .18s ease,background .18s ease,transform .18s ease}" +
      ".hck-fund:hover{border-color:rgba(163,230,53,.8);background:linear-gradient(135deg,rgba(163,230,53,.18),rgba(27,40,56,.7));transform:translateY(-1px)}" +
      ".hck-fund__icon{width:15px;height:15px;flex:0 0 auto;opacity:.95}" +
      ".hck-fund__label{color:#f4fbe8}" +
      ".hck-fund__bar{position:relative;width:54px;height:6px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden}" +
      ".hck-fund__fill{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,#a3e635,#4ade80)}" +
      ".hck-fund__num{font-family:'JetBrains Mono',Consolas,monospace;font-size:11px;color:#a3e635}" +
      "@media (max-width:1560px){.hck-nav .hck-fund__label{display:none}}" +
      "@media (max-width:760px){.hck-fund__label{display:none}.hck-fund{margin:0 6px}}";
    document.head.appendChild(s);
  }

  var STEAM_SVG = '<svg class="hck-fund__icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11.98 0C5.7 0 .55 4.84.06 11l6.44 2.66a3.4 3.4 0 0 1 1.92-.59h.19l2.86-4.15v-.06a4.53 4.53 0 1 1 4.53 4.53h-.1l-4.08 2.91v.16a3.4 3.4 0 0 1-6.75.6L.4 15.13A12 12 0 1 0 11.98 0Zm-4.5 18.2-1.47-.61a2.55 2.55 0 1 0 1.4-3.3l1.52.63a1.88 1.88 0 1 1-1.45 3.28Zm11.38-9.27a3.02 3.02 0 1 0-6.04 0 3.02 3.02 0 0 0 6.04 0Zm-5.28 0a2.27 2.27 0 1 1 4.54 0 2.27 2.27 0 0 1-4.54 0Z"/></svg>';

  function build(d) {
    var goal = Math.max(1, +d.goal || 100);
    var raised = Math.max(0, +d.raised || 0);
    var pct = Math.min(100, Math.round(raised / goal * 100));
    var a = document.createElement("a");
    a.className = "hck-fund";
    a.href = d.url || DEFAULTS.url;
    a.target = "_blank";
    a.rel = "noopener";
    var label = polish ? "Scaling Laws na Steam" : "Scaling Laws on Steam";
    var done = raised >= goal;
    a.title = done
      ? (polish ? "Cel osiągnięty. Dziękuję!" : "Goal reached. Thank you!")
      : (polish ? "Pomóż wystawić grę na Steam: klucz i twoje imię w napisach" : "Help put the game on Steam: a key and your name in the credits");
    a.setAttribute("aria-label", label + ": " + d.currency + raised + " / " + d.currency + goal);
    a.innerHTML = STEAM_SVG +
      '<span class="hck-fund__label">' + label + "</span>" +
      '<span class="hck-fund__bar" aria-hidden="true"><span class="hck-fund__fill" style="width:' + Math.max(pct, 4) + '%"></span></span>' +
      '<span class="hck-fund__num">' + d.currency + raised + "/" + d.currency + goal + "</span>";
    return a;
  }

  function place(pill) {
    var gt = document.getElementById("globalTopnav");
    if (gt) {
      var spacer = gt.querySelector(".gt-spacer");
      if (spacer && spacer.nextSibling) gt.insertBefore(pill, spacer.nextSibling);
      else gt.appendChild(pill);
      return true;
    }
    var nav = document.querySelector(".hck-nav");
    if (nav) {
      var links = nav.querySelector(".hck-nav__links");
      if (links) nav.insertBefore(pill, links); else nav.appendChild(pill);
      return true;
    }
    return false;
  }

  function run(d) {
    d = Object.assign({}, DEFAULTS, d || {});
    if (d.ends && new Date() > new Date(d.ends + "T23:59:59")) return;
    if (d.hidden) return;
    css();
    place(build(d));
  }

  function start() {
    var done = false;
    var fallback = setTimeout(function () { if (!done) { done = true; run(null); } }, 2500);
    fetch("/assets/data/steam-fund.json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (d) { if (!done) { done = true; clearTimeout(fallback); run(d); } });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();

/* Scaling Laws — project interactions
   No dependencies. Progressive enhancement only.
*/
(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  class RoomSequence {
    constructor(element) {
      this.element = element;
      this.image = element.querySelector("img");
      this.interval = Math.max(100, Number(element.dataset.interval) || 200);
      this.index = 0;
      this.timer = null;
      this.visible = false;
      this.frames = [];

      if (!this.image) return;

      this.observe();
      this.loadFrames();
      document.addEventListener("visibilitychange", () => this.sync());
      reduceMotion.addEventListener?.("change", () => this.sync());
    }

    async loadFrames() {
      const inlineFrames = (this.element.dataset.frames || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      let requested = inlineFrames;

      const manifestUrl = this.element.dataset.manifest;
      if (manifestUrl) {
        try {
          const response = await fetch(manifestUrl, { credentials: "same-origin" });
          if (response.ok) {
            const manifest = await response.json();
            if (Array.isArray(manifest.frames)) requested = manifest.frames;
            if (Number.isFinite(Number(manifest.intervalMs))) {
              this.interval = Math.max(100, Number(manifest.intervalMs));
            }
          }
        } catch {
          // The fallback <img> remains valid. No visible error is needed.
        }
      }

      if (!requested.length) return;

      const results = await Promise.all(
        requested.map((src) => new Promise((resolve) => {
          const preload = new Image();
          preload.decoding = "async";
          preload.onload = () => resolve(src);
          preload.onerror = () => resolve(null);
          preload.src = src;
        }))
      );

      this.frames = results.filter(Boolean);

      if (this.frames.length) {
        this.image.src = this.frames[0];
      }

      this.sync();
    }

    observe() {
      if (!("IntersectionObserver" in window)) {
        this.visible = true;
        return;
      }

      this.observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.target !== this.element) return;
          this.visible = entry.isIntersecting;
          this.sync();
        });
      }, { threshold: 0.34 });

      this.observer.observe(this.element);
    }

    sync() {
      const shouldRun =
        this.frames.length > 1 &&
        this.visible &&
        !document.hidden &&
        !reduceMotion.matches;

      if (shouldRun) this.start();
      else this.stop();
    }

    start() {
      if (this.timer) return;

      this.timer = window.setInterval(() => {
        this.index = (this.index + 1) % this.frames.length;
        this.image.src = this.frames[this.index];
      }, this.interval);
    }

    stop() {
      if (!this.timer) return;
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }

  document.querySelectorAll("[data-room-sequence]").forEach((element) => {
    new RoomSequence(element);
  });

  document.querySelectorAll("[data-bar]").forEach((bar) => {
    const value = Math.max(4, Math.min(100, Number(bar.dataset.bar) || 4));
    bar.style.height = `${value}%`;
  });

  if (!reduceMotion.matches && "IntersectionObserver" in window) {
    const counters = [...document.querySelectorAll("[data-count-to]")];

    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const node = entry.target;
        const target = Number(node.dataset.countTo);
        if (!Number.isFinite(target)) {
          instance.unobserve(node);
          return;
        }

        const duration = Math.max(240, Number(node.dataset.countDuration) || 700);
        const decimals = Math.max(0, Number(node.dataset.countDecimals) || 0);
        const suffix = node.dataset.countSuffix || "";
        const prefix = node.dataset.countPrefix || "";
        const start = performance.now();

        const draw = (now) => {
          const progress = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - progress, 3);
          node.textContent =
            `${prefix}${(target * eased).toFixed(decimals)}${suffix}`;
          if (progress < 1) requestAnimationFrame(draw);
        };

        requestAnimationFrame(draw);
        instance.unobserve(node);
      });
    }, { threshold: .5 });

    counters.forEach((counter) => observer.observe(counter));
  }
})();

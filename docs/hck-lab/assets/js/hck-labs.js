/* HCK Labs — shared interaction layer
   Progressive enhancement only. The site remains usable without this file.
*/
(() => {
  "use strict";

  document.documentElement.classList.add("has-js");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const navToggle = document.querySelector("[data-nav-toggle]");
  const navLinks = document.querySelector("[data-nav-links]");

  if (navToggle && navLinks) {
    const closeNav = () => {
      navToggle.setAttribute("aria-expanded", "false");
      navLinks.classList.remove("is-open");
    };

    navToggle.addEventListener("click", () => {
      const open = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!open));
      navLinks.classList.toggle("is-open", !open);
    });

    navLinks.addEventListener("click", (event) => {
      if (event.target.closest("a")) closeNav();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeNav();
    });
  }

  const normalizePath = (value) => {
    const path = value.replace(/index\.html$/i, "");
    return path.endsWith("/") ? path : `${path}/`;
  };

  const currentPath = normalizePath(window.location.pathname);

  document.querySelectorAll("[data-nav-link]").forEach((link) => {
    try {
      const linkPath = normalizePath(new URL(link.href, window.location.href).pathname);
      if (linkPath === currentPath) {
        link.classList.add("is-active");
        link.setAttribute("aria-current", "page");
      }
    } catch {
      /* Ignore malformed external URLs. */
    }
  });

  const revealItems = [...document.querySelectorAll("[data-reveal]")];

  if (!reduceMotion.matches && "IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, {
      threshold: 0.13,
      rootMargin: "0px 0px -6% 0px"
    });

    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll(".hck-edge-shine").forEach((element) => {
    element.addEventListener("pointermove", (event) => {
      const rect = element.getBoundingClientRect();
      const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
      element.style.setProperty("--shine-x", `${(x / rect.width) * 100}%`);
    });
  });
})();

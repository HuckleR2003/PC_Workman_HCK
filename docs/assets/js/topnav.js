/* PC Workman — shared global top nav behaviour.
   Hide on scroll down, reveal on scroll up; remember language choice. */
(function () {
    var topnav = document.getElementById('globalTopnav');
    if (!topnav) return;
    var lastY = window.scrollY, ticking = false;
    function onScroll() {
        var y = window.scrollY;
        if (y > lastY && y > 90) topnav.classList.add('gt-hidden');
        else topnav.classList.remove('gt-hidden');
        lastY = y; ticking = false;
    }
    window.addEventListener('scroll', function () {
        if (!ticking) { window.requestAnimationFrame(onScroll); ticking = true; }
    }, { passive: true });
    topnav.querySelectorAll('.gt-lang a[data-lang]').forEach(function (a) {
        a.addEventListener('click', function () {
            try { localStorage.setItem('pcw_lang', a.getAttribute('data-lang')); } catch (e) {}
        });
    });
})();

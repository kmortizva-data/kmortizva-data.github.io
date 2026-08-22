/* Motion only, and every bit of it optional. Without this file the pages read
   completely: scrolly panels show their final figure, curves are already drawn. */
(function () {
  var reduced = window.matchMedia &&
                window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------- scrollytelling */

  /* One observer per scrolly block: the step nearest the middle of the viewport is
     the active one, and the panel shows its figure. */
  var blocks = document.querySelectorAll(".scrolly");
  Array.prototype.forEach.call(blocks, function (block) {
    var figs = block.querySelectorAll(".scrolly-fig");
    var steps = block.querySelectorAll(".paso");

    function activate(index) {
      Array.prototype.forEach.call(figs, function (fig) {
        fig.classList.toggle("activa", fig.getAttribute("data-paso") === String(index));
      });
      Array.prototype.forEach.call(steps, function (step) {
        step.classList.toggle("activo", step.getAttribute("data-paso") === String(index));
      });
    }
    activate(0);

    if (reduced || !("IntersectionObserver" in window)) {
      /* Reduced motion: jump straight to the final state and leave it alone. */
      activate(figs.length - 1);
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          activate(entry.target.getAttribute("data-paso"));
        }
      });
    }, { rootMargin: "-45% 0px -45% 0px" });
    Array.prototype.forEach.call(steps, function (step) { observer.observe(step); });
  });

  /* ------------------------------------------ the self-drawing curve, fallback */

  /* Browsers with animation-timeline: view() never reach this branch's work: the CSS
     drives the drawing. Everywhere else, scroll position writes --avance by hand. */
  var curves = document.querySelectorAll(".dibujar");
  if (!curves.length) return;

  Array.prototype.forEach.call(curves, function (path) {
    if (path.getTotalLength) {
      var length = Math.ceil(path.getTotalLength());
      path.style.setProperty("--largo", length);
    }
  });

  if (reduced) {
    Array.prototype.forEach.call(curves, function (path) {
      path.style.setProperty("--avance", 1);
    });
    return;
  }
  if (window.CSS && CSS.supports && CSS.supports("animation-timeline: view()")) {
    return;   /* the stylesheet is already driving it */
  }

  var ticking = false;
  function place() {
    Array.prototype.forEach.call(curves, function (path) {
      var box = path.closest("svg").getBoundingClientRect();
      var viewport = window.innerHeight;
      /* 0 when the svg enters at the bottom, 1 when its top clears 40% of the view */
      var progress = (viewport - box.top) / (viewport * 0.6 + box.height * 0.4);
      path.style.setProperty("--avance", Math.max(0, Math.min(1, progress)).toFixed(3));
    });
    ticking = false;
  }
  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(place); }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  place();
})();

/* Motion only. The site used to ship two themes with a toggle labelled "froth / pulp",
   which read as a bug rather than as an option, so the light theme and the toggle are
   both gone and the page is dark, full stop.

   Everything below is an enhancement: with JavaScript off, or with reduced motion asked
   for, the page is fully readable and nothing moves. */
(function () {
  var reduced = window.matchMedia &&
                window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var reveals = document.querySelectorAll(".reveal");

  if (reduced || !("IntersectionObserver" in window)) {
    reveals.forEach(function (el) { el.classList.add("in"); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px" });
  reveals.forEach(function (el) { io.observe(el); });

  /* A restrained parallax on the screenshots: the image drifts a few pixels against the
     scroll, which makes a static grid feel alive without anyone noticing why. The work is
     done in a rAF so scrolling stays smooth, and it is capped so nothing can slide out of
     its frame. */
  var shots = Array.prototype.slice.call(document.querySelectorAll(".assay-shot img"));
  if (!shots.length) return;

  var ticking = false;

  function place() {
    var middle = window.innerHeight / 2;
    shots.forEach(function (img) {
      var box = img.getBoundingClientRect();
      if (box.bottom < -200 || box.top > window.innerHeight + 200) return;
      var offset = ((box.top + box.height / 2) - middle) / middle;   /* -1 .. 1 */
      var shift = Math.max(-14, Math.min(14, offset * 14));
      img.style.transform = "translate3d(0," + shift.toFixed(1) + "px,0) scale(1.06)";
    });
    ticking = false;
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(place);
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  place();
})();

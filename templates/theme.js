/* The toggle is a cross section of a flotation cell: froth floats on top, pulp
   sits below. A saved choice has to win over the operating system's setting,
   which is the whole reason this runs instead of leaving it to the media query. */
(function () {
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem("theme");
    if (saved === "froth" || saved === "pulp") root.setAttribute("data-theme", saved);
  } catch (e) {
    /* Private browsing can refuse storage. The media query still themes the page. */
  }

  var btn = document.querySelector("[data-toggle-theme]");
  if (btn) {
    btn.addEventListener("click", function () {
      var dark = getComputedStyle(root).colorScheme.indexOf("dark") !== -1;
      var next = dark ? "froth" : "pulp";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduced && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    document.querySelectorAll(".reveal").forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("in"); });
  }
})();

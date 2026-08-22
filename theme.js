/* Motion only. The site used to ship two themes with a toggle labelled "froth / pulp",
   which read as a bug rather than as an option, so the light theme and the toggle are
   both gone and the page is dark, full stop.

   Everything below is an enhancement. With JavaScript off, or with reduced motion asked
   for, the page is fully readable, nothing moves, and the transition curtain lifts by
   itself because that part is a CSS animation rather than something this file drives. */
(function () {
  var root = document.documentElement;
  var reduced = window.matchMedia &&
                window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------------- entrance */

  /* The hero is hidden by CSS from the first paint and "ready" releases it. Two nested
     frames, because a transition asked for in the same frame an element first paints in
     is skipped by the browser rather than played. */
  function release() {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { root.classList.add("ready"); });
    });
  }
  release();

  /* ----------------------------------------------------------------- curtain */

  var curtain = document.querySelector(".curtain");

  /* Coming back with the Back button can restore the page exactly as it was left, mid
     transition, which would mean arriving at a covered screen. */
  window.addEventListener("pageshow", function () {
    if (curtain) curtain.classList.remove("on");
  });

  if (curtain && !reduced) {
    document.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest("a");
      if (!link) return;
      var href = link.getAttribute("href");
      if (!href || link.target === "_blank") return;
      if (link.hasAttribute("download")) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;

      /* Only http(s) gets a curtain. mailto: and tel: hand off to another application and
         never load a new page here, so covering the screen for them leaves it covered. */
      if (link.protocol !== "http:" && link.protocol !== "https:") return;
      if (link.host !== window.location.host) return;              /* leaving the site */

      /* The important one. The nav writes its in-page links as "index.html#about" rather
         than "#about", so a check on the first character missed them: the curtain came
         down, the browser only moved the hash instead of loading anything, and the page
         stayed black. Compare resolved paths, not the text of the href. */
      if (link.pathname === window.location.pathname) return;

      event.preventDefault();
      curtain.classList.add("on");
      window.setTimeout(function () { window.location.href = link.href; }, 280);
    });
  }

  /* ------------------------------------------------------------- work index */

  /* Hovering or tabbing to a row swaps which screenshot the panel shows. The first pane
     is already marked visible in the HTML, so with this file absent the panel still
     shows a real image and every row is still a plain link to its project. */
  var panel = document.querySelector(".index-panel");
  if (panel) {
    var panes = panel.querySelectorAll(".index-pane");

    function showPane(slug) {
      Array.prototype.forEach.call(panes, function (pane) {
        pane.classList.toggle("on", pane.getAttribute("data-slug") === slug);
      });
    }

    Array.prototype.forEach.call(document.querySelectorAll(".index-row"), function (row) {
      var slug = row.getAttribute("data-slug");
      /* mouseenter for the cursor, focusin for the keyboard: the panel has to follow
         both or tabbing through the list shows the wrong picture. */
      row.addEventListener("mouseenter", function () { showPane(slug); });
      row.addEventListener("focusin", function () { showPane(slug); });
    });
  }

  /* ----------------------------------------------------------------- contact */

  /* Copy the address with a visible confirmation. The button only exists with this file
     running (CSS hides it otherwise), and the mailto link next to it stays for everyone.
     The clipboard API needs a secure context: GitHub Pages is https, localhost counts. */
  var copy = document.querySelector(".copy-email");
  if (copy && navigator.clipboard) {
    var copyLabel = copy.textContent;
    copy.addEventListener("click", function () {
      navigator.clipboard.writeText(copy.getAttribute("data-email")).then(function () {
        copy.textContent = copy.getAttribute("data-copied");
        copy.classList.add("done");
        window.setTimeout(function () {
          copy.textContent = copyLabel;
          copy.classList.remove("done");
        }, 2000);
      });
    });
  }

  /* The form posts on its own without this; with it, the reply lands on the page
     instead of on the form service's thank-you screen. */
  var form = document.querySelector(".contact-form");
  if (form && window.fetch && window.FormData) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var status = form.querySelector(".form-status");
      var button = form.querySelector("button[type=submit]");
      button.disabled = true;
      fetch(form.action, { method: "POST", body: new FormData(form),
                           headers: { "Accept": "application/json" } })
        .then(function (response) {
          if (!response.ok) throw new Error(String(response.status));
          form.reset();
          status.textContent = status.getAttribute("data-sent");
        })
        .catch(function () { status.textContent = status.getAttribute("data-error"); })
        .then(function () { button.disabled = false; });
    });
  }

  var reveals = document.querySelectorAll(".reveal");

  if (reduced || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(reveals, function (el) { el.classList.add("in"); });
    return;
  }

  /* ------------------------------------------------------------ smooth scroll */

  /* Lenis is vendored next to this file. If it failed to load for any reason the page
     simply scrolls the way the browser scrolls, which is not a defect. */
  var lenis = null;
  var framesRun = false;
  if (typeof window.Lenis === "function") {
    lenis = new window.Lenis({ duration: 1.1, smoothWheel: true });
    /* The loop has to be started BY requestAnimationFrame, never called by hand with a
       made up first timestamp. Seeding it with 0 meant the next real frame arrived as a
       two minute jump, which broke Lenis's time base: it left lenis-scrolling stuck on
       <html> and scrollTo silently stopped moving anything. */
    function frame(time) {
      framesRun = true;
      lenis.raf(time);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);

    /* The in-page nav links have to go through Lenis or they fight it. */
    document.addEventListener("click", function (event) {
      var link = event.target.closest && event.target.closest('a[href*="#"]');
      if (!link) return;
      var id = link.getAttribute("href").split("#")[1];
      var target = id && document.getElementById(id);
      if (!target) return;
      event.preventDefault();

      /* Only hand the scroll to Lenis if Lenis is actually animating. A background or
         hidden tab suspends requestAnimationFrame, so its rAF loop never ticks, and
         scrollTo would queue a move that never happens: the link would cancel the click
         and then do nothing at all, which is the worst of both. */
      if (framesRun) {
        lenis.scrollTo(target, { offset: -24 });
      } else {
        target.scrollIntoView();
      }
    });
  }

  /* ----------------------------------------------------------------- reveals */

  /* Fire when the block has reached 82% of the way down the viewport, once each. */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -18% 0px" });
  Array.prototype.forEach.call(reveals, function (el) { io.observe(el); });

  /* ---------------------------------------------------------------- parallax */

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

  if (lenis) lenis.on("scroll", onScroll);
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  place();
})();

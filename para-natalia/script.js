/* Para Natalia — gate, theme, letter, gallery, games. No dependencies. */
(() => {
  "use strict";

  // SHA-256 of the normalized pass word (lowercase, trimmed, accents removed).
  // Regenerate with:  python -c "import hashlib;print(hashlib.sha256(b'palabra').hexdigest())"
  const PASS_HASH = "9b871512327c09ce91dd649b3f96a63b7408ef267c8cc5710114e629730cb61f";
  // The gate asks every visit on purpose (a shared PC must not stay open).
  // Older versions remembered the unlock; clear that leftover.
  try { localStorage.removeItem("natalia:unlocked"); } catch { /* ignore */ }

  const $ = (sel, root = document) => root.querySelector(sel);

  /* ---------- helpers ---------- */
  const normalize = (s) =>
    s.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ");

  async function sha256(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  const safeGet = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const safeSet = (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } };

  /* ---------- gate ---------- */
  function unlock() {
    $("#gate").remove();
    document.body.classList.remove("locked");
    $("#app").hidden = false;
    loadLetter();
    loadGallery();
    loadGames();
    initReveal();
    initBubbles();
    initDock();
  }

  function initGate() {
    document.body.classList.add("locked");
    const form = $("#gate-form");
    const input = $("#gate-word");
    const error = $("#gate-error");
    setTimeout(() => input.focus(), 300);

    // Hash while typing so the submit click can start the music synchronously
    // (browsers only allow audio inside the user's own gesture).
    let pending = null;
    input.addEventListener("input", () => {
      const v = normalize(input.value);
      if (!crypto.subtle) return;
      sha256(v).then((h) => { pending = { v, h }; });
    });

    const decide = (ok) => {
      if (ok) {
        music.start();                       // still inside the click gesture
        unlock();
      } else {
        error.textContent = "Ese no es. Piensa en un número nuestro.";
        const gate = $("#gate");
        gate.classList.remove("gate--shake");
        void gate.offsetWidth; // restart animation
        gate.classList.add("gate--shake");
        input.select();
      }
    };

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      if (!crypto.subtle) { error.textContent = "Abre la página desde el link https, no como archivo."; return; }
      const v = normalize(input.value);
      if (pending && pending.v === v) { decide(pending.h === PASS_HASH); return; }
      decide((await sha256(v)) === PASS_HASH);   // typed and submitted in the same instant
    });
  }

  /* ---------- music: official YouTube visualizer in a small card ---------- */
  const music = (() => {
    const VIDEO_ID = "v9T_MGfzq7I";          // BAD BUNNY - DtMF (Visualizer), canal oficial
    const VOL_KEY = "natalia:volume";
    const MUTE_KEY = "natalia:muted";
    let player = null, ready = false, wantPlay = false, unlocked = false, closed = false;
    let vol = Math.min(100, Math.max(0, parseInt(safeGet(VOL_KEY), 10) || 60));
    let muted = safeGet(MUTE_KEY) === "1";
    const card = $("#player");

    function render() {
      card.classList.toggle("is-muted", muted);
      const bars = card.querySelectorAll("#vol-level i");
      const lit = muted ? 0 : Math.round(vol / 10);
      bars.forEach((b, i) => b.classList.toggle("on", i < lit));
      $("#vol-mute").setAttribute("aria-label", muted ? "Activar sonido" : "Silenciar");
    }
    function apply() {
      if (!ready) return;
      player.setVolume(vol);
      if (muted) player.mute(); else player.unMute();
      safeSet(VOL_KEY, String(vol)); safeSet(MUTE_KEY, muted ? "1" : "0");
      render();
    }
    function show() { if (!closed) card.classList.add("is-on"); }
    function isPlaying() { return ready && [1, 3].includes(player.getPlayerState()); }

    // If the browser refused to start audio, ask for one tap anywhere.
    function armTapFallback() {
      const hint = $("#player-hint");
      setTimeout(() => {
        if (isPlaying() || closed) return;
        hint.hidden = false;
        const once = () => { if (ready) player.playVideo(); hint.hidden = true; document.removeEventListener("pointerdown", once); };
        document.addEventListener("pointerdown", once);
      }, 1500);
    }

    window.onYouTubeIframeAPIReady = () => {
      player = new YT.Player("yt", {
        videoId: VIDEO_ID, width: 200, height: 200,
        playerVars: { playsinline: 1, controls: 1, rel: 0, modestbranding: 1, origin: location.origin },
        events: {
          onReady: () => {
            ready = true; apply();
            if (wantPlay) { player.playVideo(); armTapFallback(); }
          },
          onStateChange: (e) => {
            card.classList.toggle("is-paused", e.data !== 1 && e.data !== 3);
            if (e.data === 1) $("#player-hint").hidden = true;
            // keep our icon honest if she used YouTube's own mute
            if (ready && player.isMuted() !== muted) { muted = player.isMuted(); safeSet(MUTE_KEY, muted ? "1" : "0"); render(); }
          },
          onError: () => { card.classList.add("is-paused"); },
        },
      });
    };

    $("#vol-down").addEventListener("click", () => { vol = Math.max(0, vol - 10); muted = vol === 0 ? true : false; apply(); });
    $("#vol-up").addEventListener("click", () => { vol = Math.min(100, vol + 10); muted = false; apply(); });
    $("#vol-mute").addEventListener("click", () => { muted = !muted; if (!muted && vol === 0) vol = 30; apply(); });
    $("#player-fold").addEventListener("click", () => card.classList.toggle("is-folded"));
    $("#player-close").addEventListener("click", () => { closed = true; if (ready) player.stopVideo(); card.classList.remove("is-on"); });
    render();

    let ducked = false;
    return {
      // called synchronously inside the "Entrar" click
      start() {
        unlocked = true; show();
        if (ready) { player.playVideo(); armTapFallback(); } else { wantPlay = true; }
      },
      // pause the song while one of Natalia's videos plays, resume after
      duck() { if (ready && isPlaying()) { ducked = true; player.pauseVideo(); } },
      resume() { if (ready && ducked) { ducked = false; player.playVideo(); } },
    };
  })();

  /* ---------- letter (message.md: blank line = new paragraph) ---------- */
  async function loadLetter() {
    const box = $("#letter");
    try {
      const res = await fetch("message.md", { cache: "no-store" });
      if (!res.ok) throw new Error(res.status);
      const text = await res.text();
      const paras = text.replace(/\r\n/g, "\n").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
      box.innerHTML = "";
      paras.forEach((p, i) => {
        const el = document.createElement("p");
        // single line breaks inside a paragraph are kept (lists, sayings)
        p.split("\n").forEach((line, j) => {
          if (j > 0) el.appendChild(document.createElement("br"));
          el.appendChild(document.createTextNode(line.trim()));
        });
        if (i === paras.length - 1 && p.length < 40) el.className = "letter__sign";
        box.appendChild(el);
      });
    } catch (err) {
      box.innerHTML = "<p class='letter__loading'>El mensaje no cargó. Recarga la página.</p>";
      console.error("message.md", err);
    }
  }

  /* ---------- gallery ---------- */
  let photos = [];
  let current = 0;

  async function loadGallery() {
    const grid = $("#gallery");
    try {
      const res = await fetch("photos/manifest.json", { cache: "no-store" });
      if (!res.ok) throw new Error(res.status);
      photos = await res.json();
    } catch {
      photos = [];
    }
    grid.innerHTML = "";
    if (!photos.length) {
      grid.innerHTML =
        "<div class='gallery__empty'><strong>Aquí van las fotos.</strong>Todavía las estoy eligiendo (hay demasiadas buenas).</div>";
      $("#grid-wrap").hidden = false;
      return;
    }
    const FIRST = 24;
    const addTile = (p, i, extra) => {
      const fig = document.createElement("figure");
      if (extra) { fig.classList.add("is-extra"); fig.hidden = true; }
      const img = document.createElement("img");
      img.src = isVideo(p) ? p.poster : p.src;
      img.alt = "";
      img.loading = "lazy";
      img.decoding = "async";
      if (p.w && p.h) { img.width = p.w; img.height = p.h; }
      fig.appendChild(img);
      if (isVideo(p)) {
        fig.classList.add("is-video");
        const dur = document.createElement("span");
        dur.className = "gallery__dur";
        dur.textContent = fmtDur(p.dur);
        fig.appendChild(dur);
      }
      fig.addEventListener("click", () => openLightbox(i));
      grid.appendChild(fig);
    };
    photos.forEach((p, i) => addTile(p, i, i >= FIRST));
    const more = $("#gallery-more");
    if (photos.length > FIRST) {
      more.hidden = false;
      const btn = $("#gallery-more-btn");
      const label = $("#gallery-more-label");
      const rest = photos.length - FIRST;
      let open = false;
      const paint = () => {
        grid.querySelectorAll("figure.is-extra").forEach((f) => { f.hidden = !open; });
        btn.setAttribute("aria-expanded", String(open));
        label.textContent = open ? "Ver menos" : `Ver más (${rest})`;
      };
      paint();
      btn.addEventListener("click", () => {
        open = !open;
        paint();
        if (!open) $("#grid-wrap").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
    book = initBook(photos);
    initLightbox();
  }

  /* full-screen carousel: three slots (prev / current / next) on a sliding track */
  const isVideo = (p) => p && p.type === "video";
  const fmtDur = (s) => { s = Math.round(s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  const still = (p) => (isVideo(p) ? p.poster : p.src);   // what to show in the side slots
  const wrap = (i) => (i + photos.length) % photos.length;
  function stopVideo() {
    const v = $("#lightbox-video");
    if (!v.hidden) { v.pause(); v.removeAttribute("src"); v.load(); v.hidden = true; }
    $("#lightbox-img").hidden = false;
  }
  function render() {
    stopVideo();
    const p = photos[current];
    $("#lightbox-prev-img").src = still(photos[wrap(current - 1)]);
    $("#lightbox-next-img").src = still(photos[wrap(current + 1)]);
    if (isVideo(p)) {
      const v = $("#lightbox-video");
      $("#lightbox-img").hidden = true;
      v.poster = p.poster; v.src = p.src; v.hidden = false;
      v.play().catch(() => { /* needs a tap on some phones: controls are visible */ });
    } else {
      $("#lightbox-img").src = p.src;
    }
    $("#lightbox-count").textContent = `${current + 1} / ${photos.length}`;
  }
  function openLightbox(i) {
    current = i;
    render();
    const track = $("#lightbox-track");
    track.classList.remove("is-animating");
    track.style.transform = "";
    $("#lightbox").showModal();
    document.body.classList.add("locked");
  }
  function closeLightbox() {
    stopVideo();
    $("#lightbox").close();
    document.body.classList.remove("locked");
    if (book && lightboxFromBook) book.show(current);   // the book waits on the page you were looking at
    lightboxFromBook = false;
  }
  let sliding = false;
  function step(delta) {
    if (sliding || photos.length < 2) return;
    sliding = true;
    const track = $("#lightbox-track");
    const w = innerWidth;
    track.classList.add("is-animating");
    track.style.transform = `translateX(${-delta * w}px)`;
    const done = () => {
      track.removeEventListener("transitionend", done);
      current = wrap(current + delta);
      track.classList.remove("is-animating");
      track.style.transform = "";
      render();
      sliding = false;
    };
    track.addEventListener("transitionend", done);
    setTimeout(() => { if (sliding) done(); }, 400);   // safety if transitionend never fires
  }
  function initLightbox() {
    const dlg = $("#lightbox");
    const stage = $("#lightbox-stage");
    const track = $("#lightbox-track");
    $("#lightbox-close").addEventListener("click", closeLightbox);
    $("#lightbox-prev").addEventListener("click", () => step(-1));
    $("#lightbox-next").addEventListener("click", () => step(1));
    dlg.addEventListener("cancel", (e) => { e.preventDefault(); closeLightbox(); });   // Esc
    dlg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    });
    // the song steps aside while a video plays
    const vid = $("#lightbox-video");
    vid.addEventListener("play", () => music.duck());
    vid.addEventListener("pause", () => music.resume());
    vid.addEventListener("ended", () => music.resume());

    // swipe: horizontal drag changes photo, downward drag closes, tap on the sides steps
    let start = null;
    stage.addEventListener("pointerdown", (e) => {
      if (sliding) return;
      if (e.target.closest("video")) return;   // let the video's own controls work
      start = { x: e.clientX, y: e.clientY, t: performance.now() };
      stage.setPointerCapture(e.pointerId);
      track.classList.remove("is-animating");
    });
    stage.addEventListener("pointermove", (e) => {
      if (!start) return;
      const dx = e.clientX - start.x, dy = e.clientY - start.y;
      if (Math.abs(dx) > Math.abs(dy)) track.style.transform = `translateX(${dx}px)`;
      else if (dy > 0) track.style.transform = `translateY(${dy}px)`;
    });
    const end = (e) => {
      if (!start) return;
      const dx = e.clientX - start.x, dy = e.clientY - start.y;
      const dt = performance.now() - start.t;
      start = null;
      const fast = dt < 250 && Math.abs(dx) > 20;
      if (Math.abs(dx) > Math.abs(dy) && (Math.abs(dx) > 40 || fast)) { step(dx < 0 ? 1 : -1); return; }
      if (dy > 90 && Math.abs(dx) < 60) { closeLightbox(); track.style.transform = ""; return; }
      if (Math.abs(dx) < 6 && Math.abs(dy) < 6) {          // a tap: left third back, right third forward
        const x = e.clientX / innerWidth;
        if (x < 0.3) step(-1); else if (x > 0.7) step(1);
        return;
      }
      track.classList.add("is-animating");
      track.style.transform = "";
    };
    stage.addEventListener("pointerup", end);
    stage.addEventListener("pointercancel", end);
  }

  /* ---------- adventure book: the photos pasted two pages per spread ---------- */
  // Each leaf is one sheet of paper: its front is a right-hand page, its back the left-hand
  // page of the next spread. Turning a page rotates one leaf -180° around the spine.
  let book = null;
  let lightboxFromBook = false;
  const ROUTE_ART =
    '<svg class="route" viewBox="0 0 200 110" aria-hidden="true">' +
    '<path d="M22 88C62 18 112 108 176 30" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-dasharray="0.1 8"/>' +
    '<circle cx="22" cy="88" r="6" fill="currentColor"/>' +
    '<circle cx="176" cy="30" r="6" fill="none" stroke="currentColor" stroke-width="2.6"/>' +
    '<path d="M74 52l34 9-34 9 7-9z" fill="currentColor"/></svg>';
  // brass protectors on the outer corners of each cover
  const CORNERS = '<span class="cover__corner cover__corner--top"></span><span class="cover__corner cover__corner--bottom"></span>';
  // stickers on the front cover: sparkles and a small heart, drawn here (no artwork from elsewhere)
  const SPARKLE = '<path d="M12 0C13 8 16 11 24 12 16 13 13 16 12 24 11 16 8 13 0 12 8 11 11 8 12 0z"/>';
  const STICKERS =
    `<svg class="sticker sticker--s1" viewBox="0 0 24 24" aria-hidden="true">${SPARKLE}</svg>` +
    `<svg class="sticker sticker--s2" viewBox="0 0 24 24" aria-hidden="true">${SPARKLE}</svg>` +
    `<svg class="sticker sticker--s3" viewBox="0 0 24 24" aria-hidden="true">${SPARKLE}</svg>` +
    '<svg class="sticker sticker--heart" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21C5 15 2 11.5 2 8a5 5 0 0 1 10-1 5 5 0 0 1 10 1c0 3.5-3 7-10 13z"/></svg>';

  function initBook(list) {
    const wrap = $("#book-wrap");
    const stage = $("#book-stage");
    const count = $("#book-count");
    const prev = $("#book-prev");
    const next = $("#book-next");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Page geometry, in % of the page width (the unit of cqw inside a page). Up to two
    // pictures share a page, one above the other; a very tall one (9:16) fills a page alone.
    const R = parseFloat(getComputedStyle(wrap).getPropertyValue("--page-ratio")) || 1.55;  // height / width
    const TOP = 7, AREA_W = 88, AREA_H = R * 100 - 17;   // the bottom 10 keep the page number clear
    const PAD = 2.4, PAD_B = 7, GAP = 5;                  // polaroid border (wider below), space between two
    const ratio = (p) => (p.w && p.h ? p.w / p.h : 0.75);
    const isTall = (p) => ratio(p) < 0.66;
    const groups = [];
    for (let i = 0; i < list.length; i++) {
      if (!isTall(list[i]) && list[i + 1] && !isTall(list[i + 1])) { groups.push([i, i + 1]); i++; }
      else groups.push([i]);
    }

    // cover, inside cover, the pictures, then the pages still to be filled, back cover
    const pages = [{ kind: "cover" }, { kind: "endpaper" }];
    const pageOf = [];                 // picture index -> page index
    groups.forEach((g) => { g.forEach((i) => { pageOf[i] = pages.length; }); pages.push({ kind: "photo", g }); });
    pages.push({ kind: "title" }, { kind: "blank" }, { kind: "blank" }, { kind: "blank" });
    if (pages.length % 2) pages.push({ kind: "blank" });   // "play" must land on a right-hand page
    pages.push({ kind: "play" }, { kind: "back" });
    const N = pages.length / 2;        // leaves
    const LAST = pages.length - 2;     // inner pages are numbered 1..LAST

    // Where each picture of a page goes: its width and the centre of its frame. Two share
    // one width, as large as fits, and sit a little apart sideways, like pasted by hand.
    function layout(g, n) {
      const a = g.map((i) => ratio(list[i]));
      if (a.length === 1) {
        const w = Math.min(AREA_W - 2 * PAD, (AREA_H - PAD - PAD_B) * a[0]);
        return [{ i: g[0], w, x: 50, y: TOP + AREA_H / 2 }];
      }
      const w = Math.min(AREA_W - 2 * PAD, (AREA_H - 2 * (PAD + PAD_B) - GAP) / (1 / a[0] + 1 / a[1]));
      const f0 = w / a[0] + PAD + PAD_B, f1 = w / a[1] + PAD + PAD_B;
      const top = TOP + (AREA_H - f0 - f1 - GAP) / 2;
      const nudge = (AREA_W - w - 2 * PAD) * 0.35 * (n % 2 ? 1 : -1);
      return [
        { i: g[0], w, x: 50 + nudge, y: top + f0 / 2 },
        { i: g[1], w, x: 50 - nudge, y: top + f0 + GAP + f1 / 2 },
      ];
    }

    function snap({ i, w, x, y }) {
      const p = list[i];
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "snap" + (isVideo(p) ? " is-video" : "");
      btn.setAttribute("aria-label", `${isVideo(p) ? "Ver video" : "Ver foto"} ${i + 1}`);
      btn.style.setProperty("--iw", w.toFixed(2));
      btn.style.setProperty("--ih", (w / ratio(p)).toFixed(2));
      btn.style.setProperty("--x", x.toFixed(2));
      btn.style.setProperty("--y", y.toFixed(2));
      btn.style.setProperty("--rot", `${((i * 7) % 5 - 2) * 1.1}deg`);
      btn.innerHTML =
        '<span class="tape tape--a"></span><span class="tape tape--b"></span>' +
        '<span class="snap__pic"><img alt="" decoding="async" draggable="false"></span>';
      btn.querySelector("img").dataset.src = still(p);
      if (isVideo(p)) {
        btn.querySelector(".snap__pic").insertAdjacentHTML("beforeend", `<span class="snap__dur">${fmtDur(p.dur)}</span>`);
      }
      btn.addEventListener("click", () => { lightboxFromBook = true; openLightbox(i); });
      return btn;
    }

    function face(pg, n) {
      const el = document.createElement("div");
      el.className = `leaf__face leaf__face--${n % 2 ? "back" : "front"}`;
      const inner = document.createElement("div");
      inner.className = `pg pg--${pg.kind}`;
      if (pg.kind === "cover") {
        // a paper label taped on the leather, the first photo pasted under it, a few stickers
        const first = list[0];
        inner.innerHTML =
          `<div class="pg__stitch"></div>${CORNERS}${STICKERS}` +
          '<div class="cover__label"><span class="tape tape--a"></span><span class="tape tape--b"></span>' +
          '<p class="cover__title"><small>Fotos con</small>mi pana</p></div>' +
          '<figure class="cover__photo"><span class="tape tape--a"></span><img alt="" decoding="async" draggable="false"></figure>' +
          ROUTE_ART;
        const img = inner.querySelector(".cover__photo img");
        img.dataset.src = still(first);
        if (first.w && first.h) { img.width = first.w; img.height = first.h; }
      } else if (pg.kind === "back") {
        inner.innerHTML = `<div class="pg__stitch"></div>${CORNERS}`;
      } else if (pg.kind === "photo") {
        layout(pg.g, n).forEach((slot) => inner.appendChild(snap(slot)));
      } else if (pg.kind === "title") {
        inner.innerHTML = '<p class="pg__heading">Lo que todavía nos falta por vivir</p>';
      } else if (pg.kind === "play") {
        inner.innerHTML = `${ROUTE_ART}<button class="btn btn--primary pg__play" type="button">Vamos a jugar</button>`;
        inner.querySelector("button").addEventListener("click", () => $("#juegos").scrollIntoView({ block: "start" }));
      }
      if (pg.kind === "photo" || pg.kind === "title" || pg.kind === "blank") {
        inner.insertAdjacentHTML("beforeend", `<span class="pg__num">${n}</span>`);
      }
      el.appendChild(inner);
      return el;
    }

    stage.innerHTML = "";
    const leaves = [];
    for (let k = 0; k < N; k++) {
      const leaf = document.createElement("div");
      leaf.className = "leaf";
      leaf.append(face(pages[2 * k], 2 * k), face(pages[2 * k + 1], 2 * k + 1));
      stage.appendChild(leaf);
      leaves.push(leaf);
    }

    let f = 0;          // leaves turned; 0 = closed on the cover, N = closed on the back
    let busy = false;
    // Pictures load two spreads ahead and are let go far behind, so a phone never holds
    // all 85 decoded at once.
    function load(around) {
      leaves.forEach((leaf, k) => {
        const near = k >= around - 3 && k <= around + 2;
        const far = k < around - 7 || k > around + 6;
        leaf.querySelectorAll("img").forEach((img) => {
          if (near && !img.getAttribute("src")) {
            img.src = img.dataset.src;
            img.decode().catch(() => {});   // ready before its page turns into view
          } else if (far) img.removeAttribute("src");
        });
      });
    }
    // Stack the leaves for spread f. The leaf in the air (if any) goes over everything, and
    // both the spread it leaves and the one it reaches stay painted until it lands.
    function paint(flying = null, from = f) {
      const lo = Math.min(from, f) - 2, hi = Math.max(from, f) + 1;
      leaves.forEach((leaf, k) => {
        leaf.classList.toggle("is-turned", k < f);
        leaf.style.zIndex = leaf === flying ? N + 10 : k < f ? k + 1 : N - k;
        leaf.style.visibility = k >= lo && k <= hi ? "" : "hidden";
        leaf.firstChild.inert = k !== f;       // right-hand page on show
        leaf.lastChild.inert = k !== f - 1;    // left-hand page on show
      });
      load(f);
      stage.style.setProperty("--shift", f === 0 ? "-25%" : f === N ? "25%" : "0%");
      count.textContent = f === 0 ? "Toca la tapa para abrirlo"
        : f === N ? "Contratapa"
        : `Páginas ${2 * f - 1} y ${2 * f} de ${LAST}`;
      prev.disabled = f === 0;
      next.disabled = f === N;
    }
    function turn(d) {
      const from = f, to = f + d;
      if (busy || to < 0 || to > N) return;
      const leaf = leaves[d > 0 ? from : from - 1];
      f = to;
      if (reduced) { paint(); return; }
      busy = true;
      paint(leaf, from);
      let timer = 0;
      const done = (e) => {
        if (e && (e.target !== leaf || e.propertyName !== "transform")) return;
        leaf.removeEventListener("transitionend", done);
        clearTimeout(timer);
        busy = false;
        paint();
      };
      leaf.addEventListener("transitionend", done);
      timer = setTimeout(done, 1300);   // safety if transitionend never fires
    }
    // jump without animating, e.g. back from the full-screen viewer
    function show(i) {
      const to = Math.ceil(pageOf[i] / 2);
      if (busy || to === f) return;
      f = to;
      stage.classList.add("is-instant");
      paint();
      void stage.offsetWidth;
      stage.classList.remove("is-instant");
      $("#book").focus({ preventScroll: true });   // the photo that had focus may now be out of sight
    }

    prev.addEventListener("click", () => turn(-1));
    next.addEventListener("click", () => turn(1));
    $("#book").addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { e.preventDefault(); turn(1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); turn(-1); }
    });

    // swipe turns the page; a tap on a photo opens it, a tap elsewhere on a page turns that way
    let down = null, swiped = false;
    stage.addEventListener("pointerdown", (e) => {
      if (e.button > 0) return;
      down = { x: e.clientX, y: e.clientY, t: performance.now() };
    });
    addEventListener("pointerup", (e) => {
      if (!down) return;
      const dx = e.clientX - down.x, dy = e.clientY - down.y;
      const fast = performance.now() - down.t < 250 && Math.abs(dx) > 20;
      down = null;
      if (Math.abs(dx) > Math.abs(dy) && (Math.abs(dx) > 40 || fast)) {
        swiped = true;
        setTimeout(() => { swiped = false; }, 0);   // only swallow the click this swipe makes
        turn(dx < 0 ? 1 : -1);
      }
    });
    addEventListener("pointercancel", () => { down = null; });
    stage.addEventListener("click", (e) => {
      if (swiped) { e.preventDefault(); e.stopPropagation(); swiped = false; return; }
      if (e.target.closest(".snap, button, a")) return;
      const side = e.target.closest(".leaf__face");
      if (side) turn(side.classList.contains("leaf__face--back") ? -1 : 1);
    }, true);

    const gridBtn = $("#grid-toggle");
    const gridWrap = $("#grid-wrap");
    gridBtn.addEventListener("click", () => {
      const open = gridWrap.hidden;
      gridWrap.hidden = !open;
      gridBtn.setAttribute("aria-expanded", String(open));
      gridBtn.textContent = open ? "Ocultar la cuadrícula" : "Ver todas en cuadrícula";
    });

    paint();
    wrap.hidden = false;
    return { show };
  }

  /* ---------- games ---------- */
  const ICONS = {
    Misterio: '<svg viewBox="0 0 24 24"><circle cx="8" cy="15" r="4"/><path d="M10.5 12.5L20 3l1 1-2 2 1.5 1.5-2 2-1.5-1.5-1 1 1.5 1.5-2 2-1.5-1.5-2 2"/></svg>',
    Palabras: '<svg viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/></svg>',
    Dibujo: '<svg viewBox="0 0 24 24"><path d="M4 20l4-1L19 8l-3-3L5 16z"/><path d="M13 7l3 3"/></svg>',
    Mesa: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1" fill="currentColor"/><circle cx="15" cy="15" r="1" fill="currentColor"/><circle cx="15" cy="9" r="1" fill="currentColor"/><circle cx="9" cy="15" r="1" fill="currentColor"/></svg>',
    Tranqui: '<svg viewBox="0 0 24 24"><path d="M9 4h6v3a2 2 0 1 0 0 3.5V13h3a2 2 0 1 1 0 4h-3v3H9v-3a2 2 0 1 0 0-4H6v-3h3V9a2 2 0 1 1 0-4z"/></svg>',
    Mapa: '<svg viewBox="0 0 24 24"><path d="M12 21s6-5.5 6-11a6 6 0 1 0-12 0c0 5.5 6 11 6 11z"/><circle cx="12" cy="10" r="2"/></svg>',
    Cine: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18M7 5v14M17 5v14"/></svg>',
  };

  async function loadGames() {
    const grid = $("#games");
    let games = [];
    try {
      const res = await fetch("games.json", { cache: "no-store" });
      games = await res.json();
    } catch (err) {
      grid.innerHTML = "<p>La lista de juegos no cargó. Recarga la página.</p>";
      console.error("games.json", err);
      return;
    }
    grid.innerHTML = "";
    games.forEach((g) => {
      const card = document.createElement("article");
      card.className = "game";
      card.dataset.cat = g.category;
      const steps = g.howto.map((s) => `<li>${esc(s)}</li>`).join("");
      const site = g.site.toLowerCase() !== g.name.toLowerCase() ? `<div class="game__site">${esc(g.site)}</div>` : "";
      card.innerHTML = `
        <div class="game__top">
          <div class="game__icon">${ICONS[g.category] || ICONS.Mesa}</div>
          <div class="game__meta">
            <div class="game__cat">${esc(g.category)}</div>
            <h3 class="game__name">${esc(g.name)}</h3>
            ${site}
          </div>
          <span class="game__num">${String(g.n).padStart(2, "0")}</span>
        </div>
        <p class="game__blurb">${esc(g.blurb)}</p>
        <div class="game__actions">
          <a class="game__play" href="${esc(g.url)}" target="_blank" rel="noopener">
            Jugar
            <svg viewBox="0 0 24 24"><path d="M7 17L17 7M9 7h8v8"/></svg>
          </a>
        </div>
        <details>
          <summary>¿Cómo entramos a dos?</summary>
          <ol>${steps}</ol>
        </details>`;
      grid.appendChild(card);
    });
  }

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- floating bubbles (simple 2D physics, DOM based) ---------- */
  function initBubbles() {
    const box = $("#bubbles");
    if (!box) return;
    const els = [...box.querySelectorAll(".bubble")];
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0, H = 0, base = 0;
    const bubbles = els.map((el) => ({ el, k: parseFloat(el.dataset.r) || 0.5, x: 0, y: 0, vx: 0, vy: 0, r: 0, m: 1, held: false }));

    function layout() {
      W = box.clientWidth; H = box.clientHeight;
      // radius of the main bubble; phones keep a bit more size so the labels still fit
      base = Math.min(W * (W < 600 ? 0.19 : 0.14), H * 0.23);
      bubbles.forEach((b, i) => {
        b.r = base * b.k;
        b.m = b.r * b.r;
        b.el.style.setProperty("--d", (b.r * 2).toFixed(1));
        if (b.x === 0 && b.y === 0) {
          // main in the middle, the rest on a ring around it
          if (i === 0) { b.x = W / 2; b.y = H / 2; }
          else {
            const a = (i - 1) / (bubbles.length - 1) * Math.PI * 2 - Math.PI / 2;
            const ring = Math.min(W, H) * 0.5 - b.r;
            b.x = W / 2 + Math.cos(a) * ring * 0.8;
            b.y = H / 2 + Math.sin(a) * ring * 0.8;
          }
          const ang = Math.random() * Math.PI * 2, sp = 90 + Math.random() * 60;
          b.vx = Math.cos(ang) * sp;
          b.vy = Math.sin(ang) * sp;
        }
        b.x = Math.min(Math.max(b.x, b.r), W - b.r);
        b.y = Math.min(Math.max(b.y, b.r), H - b.r);
      });
      draw();
    }

    function draw() {
      bubbles.forEach((b) => { b.el.style.transform = `translate(${(b.x - b.r).toFixed(1)}px, ${(b.y - b.r).toFixed(1)}px)`; });
    }

    function step(dt) {
      const MAX = 170, MIN = 70;      // px per second
      bubbles.forEach((b) => {
        if (b.held) return;
        // gentle wandering so they never settle in a corner
        b.vx += (Math.random() - 0.5) * 200 * dt;
        b.vy += (Math.random() - 0.5) * 200 * dt;
        const s = Math.hypot(b.vx, b.vy);
        if (s > MAX) { b.vx *= MAX / s; b.vy *= MAX / s; }
        if (s < MIN) { const k = (MIN + 5) / (s || 1); b.vx *= k; b.vy *= k; }
        b.x += b.vx * dt; b.y += b.vy * dt;
        // walls
        if (b.x < b.r) { b.x = b.r; b.vx = Math.abs(b.vx) * 0.9; }
        if (b.x > W - b.r) { b.x = W - b.r; b.vx = -Math.abs(b.vx) * 0.9; }
        if (b.y < b.r) { b.y = b.r; b.vy = Math.abs(b.vy) * 0.9; }
        if (b.y > H - b.r) { b.y = H - b.r; b.vy = -Math.abs(b.vy) * 0.9; }
      });
      // pairwise collisions: separate, then exchange momentum along the normal
      for (let i = 0; i < bubbles.length; i++) {
        for (let j = i + 1; j < bubbles.length; j++) {
          const a = bubbles[i], c = bubbles[j];
          let dx = c.x - a.x, dy = c.y - a.y;
          let d = Math.hypot(dx, dy) || 0.01;
          const min = a.r + c.r;
          if (d >= min) continue;
          const nx = dx / d, ny = dy / d;
          const overlap = min - d;
          const ta = a.held ? 0 : (c.held ? 1 : c.m / (a.m + c.m));
          const tc = c.held ? 0 : (a.held ? 1 : a.m / (a.m + c.m));
          a.x -= nx * overlap * ta; a.y -= ny * overlap * ta;
          c.x += nx * overlap * tc; c.y += ny * overlap * tc;
          const rvx = c.vx - a.vx, rvy = c.vy - a.vy;
          const vn = rvx * nx + rvy * ny;
          if (vn > 0) continue;
          const e = 0.92;
          const jImp = -(1 + e) * vn / (1 / a.m + 1 / c.m);
          if (!a.held) { a.vx -= jImp / a.m * nx; a.vy -= jImp / a.m * ny; }
          if (!c.held) { c.vx += jImp / c.m * nx; c.vy += jImp / c.m * ny; }
        }
      }
    }

    // drag with the pointer: the bubble follows the finger and keeps its throw speed
    let grabbed = null, last = null;
    box.addEventListener("pointerdown", (e) => {
      const rect = box.getBoundingClientRect();
      const px = e.clientX - rect.left, py = e.clientY - rect.top;
      grabbed = bubbles.find((b) => Math.hypot(b.x - px, b.y - py) <= b.r) || null;
      if (!grabbed) return;
      grabbed.held = true; grabbed.vx = grabbed.vy = 0;
      last = { x: px, y: py, t: performance.now() };
      box.setPointerCapture(e.pointerId);
    });
    box.addEventListener("pointermove", (e) => {
      if (!grabbed) return;
      const rect = box.getBoundingClientRect();
      const px = e.clientX - rect.left, py = e.clientY - rect.top;
      const now = performance.now(), dt = Math.max((now - last.t) / 1000, 0.008);
      grabbed.vx = (px - last.x) / dt; grabbed.vy = (py - last.y) / dt;
      grabbed.x = Math.min(Math.max(px, grabbed.r), W - grabbed.r);
      grabbed.y = Math.min(Math.max(py, grabbed.r), H - grabbed.r);
      last = { x: px, y: py, t: now };
    });
    const release = () => { if (grabbed) { grabbed.held = false; grabbed = null; } };
    box.addEventListener("pointerup", release);
    box.addEventListener("pointercancel", release);

    layout();
    if (reduced) return;                  // static composition, no animation
    let prev = performance.now();
    function frame(now) {
      const dt = Math.min((now - prev) / 1000, 0.05);
      prev = now;
      if (!document.hidden) { step(dt); draw(); }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    addEventListener("resize", () => {
      const ow = W, oh = H;
      bubbles.forEach((b) => { b.x = b.x / ow * box.clientWidth; b.y = b.y / oh * box.clientHeight; });
      layout();
    });
  }

  /* ---------- side dock: quick jumps, hideable, highlights the current section ---------- */
  function initDock() {
    const dock = $("#dock");
    const toggle = $("#dock-toggle");
    const DOCK_KEY = "natalia:dock";
    const setHidden = (h) => {
      dock.classList.toggle("is-hidden", h);
      toggle.setAttribute("aria-expanded", String(!h));
      toggle.setAttribute("aria-label", h ? "Mostrar atajos" : "Ocultar atajos");
      safeSet(DOCK_KEY, h ? "hidden" : "shown");
    };
    setHidden(safeGet(DOCK_KEY) === "hidden");
    toggle.addEventListener("click", () => setHidden(!dock.classList.contains("is-hidden")));
    const links = [...dock.querySelectorAll(".dock__link")];
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) return;
          links.forEach((a) => a.classList.toggle("is-active", a.dataset.target === en.target.id));
        });
      }, { rootMargin: "-40% 0px -50% 0px" });
      ["inicio", "mensaje", "fotos", "juegos"].forEach((id) => { const el = document.getElementById(id); if (el) io.observe(el); });
    }
  }

  /* ---------- reveal on scroll ---------- */
  function initReveal() {
    const els = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("is-in")); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    els.forEach((e) => io.observe(e));
  }

  /* ---------- boot ---------- */
  initGate();
})();

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
        if (!open) $("#fotos").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
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

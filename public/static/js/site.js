"use strict";

// Every feature here enhances markup that already works without JavaScript.
const root = document.documentElement;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
requestAnimationFrame(() => root.classList.add("is-loaded"));

(function revealOnScroll() {
  const targets = document.querySelectorAll("[data-reveal]");
  if (!targets.length) return;
  if (!("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("is-in"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("is-in");
      observer.unobserve(entry.target);
    }
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
  targets.forEach((el) => observer.observe(el));
  window.addEventListener("load", () => setTimeout(() => {
    targets.forEach((el) => {
      const box = el.getBoundingClientRect();
      if (box.top < innerHeight && box.bottom > 0) el.classList.add("is-in");
    });
  }, 2500));
})();

(function siteHeader() {
  const header = document.querySelector(".site-header");
  if (!header) return;
  const toggle = header.querySelector(".nav__toggle");
  const label = header.querySelector(".nav__toggle-label");
  const setOpen = (open) => {
    header.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    if (label) label.textContent = open ? "Close" : "Menu";
  };
  if (toggle) {
    toggle.addEventListener("click", () => setOpen(!header.classList.contains("is-open")));
    header.querySelectorAll(".nav a").forEach((link) => link.addEventListener("click", () => setOpen(false)));
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") setOpen(false); });
  }
  const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
})();

(function scrollProgress() {
  const bar = document.querySelector("[data-scroll-progress]");
  if (!bar) return;
  let queued = false;
  const draw = () => {
    queued = false;
    const span = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = span > 0 ? Math.min(1, Math.max(0, window.scrollY / span)) : 0;
    bar.style.transform = `scaleX(${ratio})`;
  };
  draw();
  window.addEventListener("scroll", () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(draw);
  }, { passive: true });
  window.addEventListener("resize", draw);
})();

(function announcement() {
  const bar = document.querySelector("[data-announce]");
  if (!bar) return;
  const close = bar.querySelector("[data-announce-close]");
  const key = "otto-announce:" + bar.textContent.trim().slice(0, 80);
  try {
    if (sessionStorage.getItem(key) === "hidden") { bar.remove(); return; }
  } catch (error) {
    // Storage can be blocked (private mode); the bar then simply stays visible.
  }
  close.hidden = false;
  close.addEventListener("click", () => {
    bar.remove();
    try { sessionStorage.setItem(key, "hidden"); } catch (error) { /* see above */ }
  });
})();

(function officeStatus() {
  const badges = document.querySelectorAll("[data-office-status]");
  if (!badges.length || !window.Intl) return;
  let week;
  try {
    week = JSON.parse(badges[0].dataset.hours || "{}");
  } catch (error) {
    console.error("Office hours data on the page is not valid JSON; keeping the server-rendered status.", error);
    return;
  }
  const timeZone = badges[0].dataset.timezone || "America/New_York";
  // Days the owner marked as time off in the portal. The server rendered today's
  // wording already; this list keeps the badge honest if the page stays open past
  // midnight or a visitor has the page open across a holiday.
  let awayDates = new Set();
  try { awayDates = new Set(JSON.parse(badges[0].dataset.awayDates || "[]")); } catch (error) { awayDates = new Set(); }
  if (badges[0].dataset.away === "yes" && !awayDates.size) return;
  const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const toMinutes = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
  const clock = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "am" : "pm"}`; };
  const localNow = () => {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone, weekday: "long", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
    const pick = (type) => parts.find((part) => part.type === type).value;
    return {
      weekday: dayNames.indexOf(pick("weekday")),
      minutes: Number(pick("hour")) * 60 + Number(pick("minute")),
      date: `${pick("year")}-${pick("month")}-${pick("day")}`,
    };
  };
  const describe = () => {
    const { weekday, minutes, date } = localNow();
    if (awayDates.has(date)) return [false, "Away today, call and we will get back to you"];
    const today = week[String(weekday)];
    if (today && today[0] && minutes >= toMinutes(today[1]) && minutes < toMinutes(today[2])) return [true, `Open now, until ${clock(today[2])}`];
    if (today && today[0] && minutes < toMinutes(today[1])) return [false, `Closed now, opens today at ${clock(today[1])}`];
    for (let offset = 1; offset < 8; offset += 1) {
      const next = week[String((weekday + offset) % 7)];
      if (!next || !next[0]) continue;
      // Walk forward past any time off so the badge never promises a day we are away.
      let day = new Date(`${date}T12:00:00`);
      let label = offset === 1 ? "tomorrow" : dayNames[(weekday + offset) % 7];
      let blocked = false;
      for (let step = 1; step <= offset; step += 1) {
        day = new Date(day.getTime() + 86400000);
        if (awayDates.has(day.toISOString().slice(0, 10))) { blocked = true; break; }
      }
      if (blocked) continue;
      return [false, `Closed now, opens ${label} at ${clock(next[1])}`];
    }
    return [false, "Closed now, call to arrange a time"];
  };
  const render = () => {
    const [isOpen, text] = describe();
    badges.forEach((badge) => {
      badge.textContent = text;
      badge.classList.toggle("is-open", isOpen);
      badge.classList.toggle("is-closed", !isOpen);
    });
  };
  render();
  setInterval(render, 60_000);
})();

(function quoteWizard() {
  const form = document.querySelector("[data-wizard]");
  if (!form) return;
  const steps = Array.from(form.querySelectorAll("[data-step]"));
  const bar = form.querySelector("[data-progress-bar]");
  const progress = form.querySelector("[data-progress]");
  const next = form.querySelector("[data-next]");
  const back = form.querySelector("[data-back]");
  const itemsError = form.querySelector("[data-items-error]");
  const countLabel = form.querySelector("[data-count-label]");
  const boxes = Array.from(form.querySelectorAll('input[name="items"]'));
  const chosen = () => boxes.filter((box) => box.checked).length;

  const show = (index) => {
    steps.forEach((step, i) => step.classList.toggle("is-current", i === index));
    bar.style.width = `${((index + 1) / steps.length) * 100}%`;
    if (index === 1) form.querySelector("#q-name").focus({ preventScroll: true });
  };
  const updateCount = () => {
    const n = chosen();
    countLabel.textContent = n ? `${n} selected` : "";
    if (n) itemsError.hidden = true;
  };

  boxes.forEach((box) => box.addEventListener("change", updateCount));
  next.addEventListener("click", () => {
    if (!chosen()) { itemsError.hidden = false; return; }
    show(1);
  });
  back.addEventListener("click", () => show(0));
  form.addEventListener("submit", (event) => {
    if (!chosen()) { event.preventDefault(); show(0); itemsError.hidden = false; }
  });

  // Coverage buttons ("Get an auto quote") jump here and tick the matching choice.
  document.querySelectorAll("[data-quote-item]").forEach((link) => {
    link.addEventListener("click", () => {
      const match = boxes.find((box) => box.value === link.dataset.quoteItem);
      if (match && !match.checked) { match.checked = true; updateCount(); }
      show(0);
    });
  });

  progress.hidden = false;
  next.hidden = false;
  back.hidden = false;
  form.classList.add("is-wizard");
  show(0);
})();

(function carrierFilter() {
  const input = document.querySelector("[data-filter]");
  if (!input) return;
  const wrap = document.querySelector("[data-filter-wrap]");
  const items = Array.from(document.querySelectorAll("[data-filter-list] > li"));
  const empty = document.querySelector("[data-filter-empty]");
  wrap.hidden = false;
  input.addEventListener("input", () => {
    const term = input.value.trim().toLowerCase();
    let shown = 0;
    items.forEach((item) => {
      const match = !term || item.dataset.name.includes(term);
      item.hidden = !match;
      if (match) { shown += 1; item.classList.add("is-in"); }
    });
    empty.hidden = shown !== 0;
  });
})();

(function countUp() {
  const numbers = document.querySelectorAll("[data-count]");
  if (!numbers.length || reduceMotion || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      const target = Number(entry.target.dataset.count);
      const start = performance.now();
      const tick = (now) => {
        const t = Math.min(1, (now - start) / 1200);
        entry.target.textContent = String(Math.round(target * (1 - Math.pow(1 - t, 3))));
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }, { threshold: 0.6 });
  numbers.forEach((el) => observer.observe(el));
})();

(function headlineRotator() {
  const holder = document.querySelector("[data-rotator]");
  if (!holder) return;
  const text = holder.querySelector("[data-rotator-text]");
  const fitEl = holder.querySelector(".hero__fit");
  let quotes;
  try { quotes = JSON.parse(holder.dataset.quotes || "[]"); } catch (error) { console.error("Headline list is not valid JSON.", error); return; }
  if (!quotes.length || !fitEl) return;

  const dots = document.querySelector("[data-rotator-dots]");
  const buttons = dots ? Array.from(dots.querySelectorAll("button")) : [];
  const interval = 5400;
  let sizes = [];
  let index = 0;
  let timer;
  let paused = false;
  if (dots && quotes.length > 1) { dots.hidden = false; dots.style.setProperty("--rotate-time", `${interval}ms`); }

  const words = (line) => line.split(/(\s+)/).filter(Boolean).map((part, i) => {
    const span = document.createElement("span");
    span.className = "w";
    span.style.setProperty("--i", String(i));
    span.textContent = part;
    return span;
  });

  const setDots = () => buttons.forEach((button, i) => {
    if (i === index) {
      button.setAttribute("aria-current", "true");
      const bar = button.querySelector("span");
      bar.replaceWith(bar.cloneNode()); // restarts the progress fill
    } else {
      button.removeAttribute("aria-current");
    }
  });

  // Size every saying to fill the same fixed box: the largest type whose wrapped
  // block still fits the height. Because only the type size changes, the page below
  // never moves when the headline rotates. The box itself is fixed in CSS.
  const measure = () => {
    const height = holder.clientHeight;
    const width = holder.clientWidth;
    if (!height || !width) return;
    const fits = (size) => {
      holder.style.fontSize = `${size}px`;
      // Leave room for descenders: at this scale the line box clips the tails of
      // g, y and p if the type is measured to the last pixel.
      const room = fitEl.getBoundingClientRect();
      return room.height <= height - size * 0.13 && room.width <= width + 1;
    };
    const fitted = quotes.map((line) => {
      text.replaceChildren(...words(line));
      let low = 12;
      let high = Math.min(width * 2.4, 520);
      while (high - low > 1) {
        const mid = (low + high) / 2;
        if (fits(mid)) low = mid; else high = mid;
      }
      return Math.max(12, Math.floor(low));
    });
    sizes = fitted;
    holder.style.fontSize = `${sizes[index]}px`;
    text.replaceChildren(...words(quotes[index]));
    holder.classList.add("is-ready");
  };

  const show = (next) => {
    index = (next + quotes.length) % quotes.length;
    if (reduceMotion) {
      holder.style.fontSize = sizes[index] ? `${sizes[index]}px` : "";
      text.replaceChildren(...words(quotes[index]));
      setDots();
      return;
    }
    if (!text.querySelector(".w")) text.replaceChildren(...words(text.textContent));
    // Collapse the highlighter while the old line leaves, so no empty gold bar is left behind.
    text.classList.add("is-sweeping");
    text.querySelectorAll(".w").forEach((w) => w.classList.add("is-out"));
    const leaveTime = 190 + text.querySelectorAll(".w").length * 16;
    setTimeout(() => {
      const incoming = words(quotes[index]);
      if (sizes[index]) holder.style.fontSize = `${sizes[index]}px`;
      incoming.forEach((w) => w.classList.add("is-in-start"));
      text.replaceChildren(...incoming);
      void text.offsetWidth;
      incoming.forEach((w) => w.classList.remove("is-in-start"));
      requestAnimationFrame(() => text.classList.remove("is-sweeping"));
      setDots();
    }, leaveTime);
  };

  const schedule = () => {
    clearInterval(timer);
    if (quotes.length < 2) return;
    timer = setInterval(() => { if (!paused && !document.hidden) show(index + 1); }, interval);
  };

  // Wait for the real typeface before the first measurement, otherwise the fallback
  // font is measured and the headline visibly changes size once Fraunces arrives.
  if (document.fonts && document.fonts.status !== "loaded") {
    document.fonts.ready.then(measure).catch(measure);
  } else {
    measure();
  }
  let resizeTimer;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(measure, 160); });
  buttons.forEach((button, i) => button.addEventListener("click", () => { if (i !== index) show(i); schedule(); }));
  const inner = holder.closest(".hero__inner");
  if (inner) {
    inner.addEventListener("mouseenter", () => { paused = true; });
    inner.addEventListener("mouseleave", () => { paused = false; });
  }
  setDots();
  schedule();
})();

(function coveragePreview() {
  const list = document.querySelector("[data-hover-reveal]");
  if (!list) return;
  const rows = Array.from(list.querySelectorAll("details.cov"));
  const arts = Array.from(document.querySelectorAll("[data-peek-art]"));
  const show = (index) => arts.forEach((art, i) => art.classList.toggle("is-current", i === index));
  rows.forEach((row) => {
    const index = Number(row.dataset.artIndex);
    // Older browsers ignore <details name>, so close the others ourselves.
    row.addEventListener("toggle", () => {
      if (row.open) { rows.forEach((other) => { if (other !== row) other.open = false; }); show(index); }
    });
    row.querySelector("summary").addEventListener("mouseenter", () => show(index));
    row.querySelector("summary").addEventListener("focus", () => show(index));
  });
  list.addEventListener("mouseleave", () => {
    const open = rows.find((row) => row.open);
    if (open) show(Number(open.dataset.artIndex));
  });
})();

(function companyRolodex() {
  const finder = document.querySelector("[data-finder]");
  if (!finder) return;
  const picks = Array.from(finder.querySelectorAll("[data-pick]"));
  const cards = Array.from(finder.querySelectorAll("[data-detail]"));
  const count = finder.querySelector("[data-rolex-count]");
  const stage = finder.querySelector(".rolex__stage");
  if (!picks.length || !cards.length) return;
  let index = 0;
  const pad = (n) => String(n).padStart(2, "0");
  const render = (target, scroll = false) => {
    index = (target + cards.length) % cards.length;
    const id = cards[index].dataset.detail;
    picks.forEach((pick) => pick.setAttribute("aria-current", String(pick.dataset.pick === id)));
    const half = Math.floor(cards.length / 2);
    cards.forEach((card, i) => {
      const on = i === index;
      // Shortest way round the drum, so the first card sits next to the last.
      const off = ((i - index + cards.length + half) % cards.length) - half;
      const distance = Math.abs(off);
      card.style.setProperty("--ty", `${off * -17}px`);
      card.style.setProperty("--rx", `${off * 4.5}deg`);
      card.style.setProperty("--sc", String(Math.max(0.9, 1 - distance * 0.012)));
      card.style.setProperty("--op", on ? "1" : String(Math.max(0, 0.92 - (distance - 1) * 0.22)));
      card.style.setProperty("--z", String(50 - distance));
      card.classList.toggle("is-current", on);
      card.toggleAttribute("inert", !on);
      card.setAttribute("aria-hidden", String(!on));
    });
    if (count) count.textContent = `${pad(index + 1)} / ${pad(cards.length)}`;
    if (scroll && window.innerWidth < 860 && stage) {
      stage.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
    }
  };
  picks.forEach((pick) => pick.addEventListener("click", () => render(picks.indexOf(pick), true)));
  const prev = finder.querySelector("[data-rolex-prev]");
  const next = finder.querySelector("[data-rolex-next]");
  if (prev) prev.addEventListener("click", () => render(index - 1));
  if (next) next.addEventListener("click", () => render(index + 1));
  if (stage) stage.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") { event.preventDefault(); render(index + 1); }
    if (event.key === "ArrowLeft") { event.preventDefault(); render(index - 1); }
  });
  const search = finder.querySelector("[data-filter]");
  if (search) search.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const first = picks.find((pick) => !pick.closest("li").hidden);
    if (first) render(picks.indexOf(first), true);
  });
  render(0);
})();

(function marquees() {
  if (reduceMotion) return;
  document.querySelectorAll("[data-marquee]").forEach((track) => {
    const list = track.querySelector("ul");
    if (!list || track.dataset.running) return;
    // One copy of the items makes the loop seamless; the copy is hidden from screen readers.
    Array.from(list.children).forEach((item) => {
      const copy = item.cloneNode(true);
      copy.setAttribute("aria-hidden", "true");
      copy.querySelectorAll("img").forEach((img) => { img.alt = ""; });
      copy.querySelectorAll("a").forEach((link) => { link.tabIndex = -1; });
      list.appendChild(copy);
    });
    track.style.setProperty("--marquee-time", `${list.children.length * 2.4}s`);
    track.classList.add("is-running");
    track.dataset.running = "yes";
  });
})();

(function paperGallery() {
  const gallery = document.querySelector("[data-gallery]");
  if (!gallery) return;
  const controls = document.querySelector("[data-gallery-controls]");
  const step = () => (gallery.querySelector("li")?.getBoundingClientRect().width || 300) + 26;
  if (controls) {
    controls.hidden = false;
    document.querySelector("[data-gallery-prev]").addEventListener("click", () => gallery.scrollBy({ left: -step(), behavior: reduceMotion ? "auto" : "smooth" }));
    document.querySelector("[data-gallery-next]").addEventListener("click", () => gallery.scrollBy({ left: step(), behavior: reduceMotion ? "auto" : "smooth" }));
  }
  // Drag to scroll with a mouse; touch already scrolls natively.
  let startX = 0;
  let startScroll = 0;
  let moved = false;
  gallery.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse") return;
    startX = event.clientX;
    startScroll = gallery.scrollLeft;
    moved = false;
    const onMove = (e) => {
      const dx = e.clientX - startX;
      if (Math.abs(dx) > 4) { moved = true; gallery.classList.add("is-dragging"); }
      gallery.scrollLeft = startScroll - dx;
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      setTimeout(() => gallery.classList.remove("is-dragging"), 0);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });
  gallery.addEventListener("click", (event) => { if (moved) { event.preventDefault(); moved = false; } }, true);
})();

(function reviewRotator() {
  const stage = document.querySelector("[data-rotator-reviews]");
  if (!stage) return;
  const reviews = Array.from(stage.querySelectorAll("[data-review]"));
  const controls = document.querySelector("[data-review-controls]");
  if (reviews.length < 2) return;
  let index = 0;
  const show = (next) => {
    reviews[index].classList.remove("is-current");
    index = (next + reviews.length) % reviews.length;
    reviews[index].classList.add("is-current");
  };
  controls.hidden = false;
  document.querySelector("[data-review-prev]").addEventListener("click", () => show(index - 1));
  document.querySelector("[data-review-next]").addEventListener("click", () => show(index + 1));
  if (!reduceMotion) setInterval(() => { if (!document.hidden && !stage.matches(":hover")) show(index + 1); }, 8000);
})();

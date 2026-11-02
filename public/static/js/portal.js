"use strict";

// Small helpers for the agent portal. Every form still works without them.

document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll("[data-toast]").forEach((toast) => {
  const close = toast.querySelector("[data-toast-close]");
  const hide = () => toast.classList.add("is-gone");
  close.addEventListener("click", hide);
  setTimeout(hide, 6000);
});

document.querySelectorAll("[data-image-field]").forEach((field) => {
  const input = field.querySelector('input[type="file"]');
  const nameLabel = field.querySelector("[data-image-name]");
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (!file) return;
    nameLabel.textContent = file.size > 3 * 1024 * 1024 ? `${file.name} is larger than 3 MB; please choose a smaller image.` : `Selected: ${file.name}. Save to publish it.`;
    const current = field.querySelector("[data-image-preview]");
    const img = document.createElement("img");
    img.alt = "";
    img.setAttribute("data-image-preview", "");
    img.src = URL.createObjectURL(file);
    current.replaceWith(img);
  });
});

document.querySelectorAll("textarea[data-counter]").forEach((area) => {
  const note = document.createElement("p");
  note.className = "field__count";
  note.setAttribute("aria-live", "polite");
  area.insertAdjacentElement("afterend", note);
  const update = () => { note.textContent = `${area.value.length} of ${area.maxLength} characters`; };
  area.addEventListener("input", update);
  update();
});

document.querySelectorAll("[data-preview]").forEach((input) => {
  const target = document.querySelector(`[data-preview-target="${input.dataset.preview}"]`);
  if (!target) return;
  input.addEventListener("input", () => { target.textContent = input.value || "Your headline"; });
});

(function sideMenu() {
  const toggle = document.querySelector(".side__toggle");
  const side = document.querySelector(".side");
  if (!toggle || !side) return;
  toggle.hidden = false;
  toggle.addEventListener("click", () => {
    const open = side.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Close" : "Menu";
  });
})();

// Sticky notes: drag by the dotted corner and the position is saved quietly.
// Without JavaScript the notes stay where they were last saved and every form works.
(function stickyNotes() {
  const board = document.querySelector("[data-note-board]");
  if (!board) return;
  const token = board.dataset.csrf;
  const notes = [...board.querySelectorAll("[data-note]")];
  let topZ = Math.max(0, ...notes.map((note) => Number(note.dataset.z) || 0));

  notes.forEach((note) => {
    const grip = note.querySelector("[data-note-grip]");
    if (!grip) return;
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let baseX = 0;
    let baseY = 0;

    grip.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "touch") return; // notes stack in a column on small screens
      event.preventDefault();
      dragging = true;
      baseX = note.offsetLeft;
      baseY = note.offsetTop;
      startX = event.clientX;
      startY = event.clientY;
      note.classList.add("is-dragging");
      note.style.zIndex = String(++topZ);
      grip.setPointerCapture(event.pointerId);
    });

    grip.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      note.style.left = `${Math.max(0, baseX + event.clientX - startX)}px`;
      note.style.top = `${Math.max(0, baseY + event.clientY - startY)}px`;
    });

    const finish = async () => {
      if (!dragging) return;
      dragging = false;
      note.classList.remove("is-dragging");
      note.dataset.z = String(topZ);
      const body = new URLSearchParams({
        csrf_token: token,
        pos_x: String(note.offsetLeft),
        pos_y: String(note.offsetTop),
        z_index: String(topZ),
      });
      try {
        const response = await fetch(note.dataset.moveUrl, { method: "POST", body });
        if (!response.ok) throw new Error(String(response.status));
        note.classList.remove("is-unsaved");
        note.classList.add("is-saved");
        setTimeout(() => note.classList.remove("is-saved"), 1200);
      } catch (error) {
        note.classList.add("is-unsaved");
      }
    };

    grip.addEventListener("pointerup", finish);
    grip.addEventListener("pointercancel", finish);
  });
})();

// Resource rows: copy the name and address, or press C on a highlighted row.
(function resourceCopy() {
  const rows = document.querySelectorAll("[data-copy-text]");
  if (!rows.length) return;

  const write = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.append(field);
    field.select();
    document.execCommand("copy");
    field.remove();
  };

  rows.forEach((row) => {
    const text = row.dataset.copyText || "";
    const buttons = row.querySelectorAll("[data-copy]");
    const flash = (button) => {
      if (!button) return;
      const label = button.textContent;
      button.textContent = "Copied";
      button.classList.add("is-copied");
      setTimeout(() => { button.textContent = label; button.classList.remove("is-copied"); }, 1400);
    };
    const copy = async (button) => {
      try { await write(text); flash(button); } catch (error) { if (button) button.textContent = "Press ⌘C"; }
    };
    buttons.forEach((button) => button.addEventListener("click", (event) => { event.stopPropagation(); copy(button); }));
    row.addEventListener("keydown", (event) => {
      if (event.target !== row || (event.key !== "c" && event.key !== "C")) return;
      event.preventDefault();
      copy(buttons[0]);
    });
  });
})();

/**
 * Diacritic Typing exercise client-side logic.
 *
 * Renders the on-screen keyboard with accent keys and handles character-by-character
 * input. Communicates with /api/v1/exercises/diacritic-typing/* endpoints.
 */
(function () {
  "use strict";

  function getLanguage() {
    const el = document.getElementById("language-select");
    return el ? el.value : "pt";
  }

  let display = [];
  let cursor = 0;
  let disabledKeys = new Set();

  const BASE_ROWS = [
    "qwertyuiop".split(""),
    "asdfghjkl".split(""),
    "zxcvbnm".split(""),
  ];

  document.addEventListener("DOMContentLoaded", () => {
    const newWordBtn = document.getElementById("btn-new-word");
    if (newWordBtn) newWordBtn.addEventListener("click", newWord);

    const hintSelect = document.getElementById("hint-level-select");
    if (hintSelect) hintSelect.addEventListener("change", newWord);

    document.addEventListener("keydown", handleKeydown);
  });

  async function newWord() {
    const hintSelect = document.getElementById("hint-level-select");
    const hintLevel = hintSelect ? hintSelect.value : "off";

    const resp = await fetch("/api/v1/exercises/diacritic-typing/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: getLanguage(), hint_level: hintLevel }),
    });
    const data = await resp.json();

    if (data.data && data.data.display) {
      display = data.data.display;
      cursor = display.indexOf("_");
      disabledKeys = new Set();
      renderDisplay();
      renderKeyboard(["á", "à", "â", "ã", "é", "ê", "í", "ó", "ô", "õ", "ú", "ç"]);
      hideMessage();

      const trans = document.getElementById("word-translation");
      if (trans) trans.textContent = data.data.translation || "";
    } else {
      const wordDisplay = document.getElementById("word-display");
      if (wordDisplay) {
        wordDisplay.innerHTML = '<span class="has-text-grey">No accented words available.</span>';
      }
    }
  }

  function renderDisplay() {
    const el = document.getElementById("word-display");
    if (!el) return;

    el.innerHTML = display
      .map((ch, i) => {
        const cls = i === cursor ? "has-text-primary" : ch === "_" ? "has-text-grey-light" : "";
        return `<span class="${cls}">${ch}</span>`;
      })
      .join(" ");
  }

  function renderKeyboard(accentKeys) {
    const accentKb = document.getElementById("accent-keyboard");
    if (accentKb) {
      accentKb.innerHTML = "";
      accentKeys.forEach((key) => {
        const btn = document.createElement("button");
        btn.className = "button is-medium is-family-monospace";
        if (disabledKeys.has(key)) btn.classList.add("is-static");
        btn.textContent = key;
        btn.addEventListener("click", () => handleKey(key));
        accentKb.appendChild(btn);
      });
    }

    const baseKb = document.getElementById("base-keyboard");
    if (baseKb) {
      baseKb.innerHTML = "";
      BASE_ROWS.forEach((row) => {
        const rowDiv = document.createElement("div");
        rowDiv.className = "buttons is-centered mb-1";
        row.forEach((key) => {
          const btn = document.createElement("button");
          btn.className = "button is-small is-family-monospace";
          if (disabledKeys.has(key)) btn.classList.add("is-static");
          btn.textContent = key;
          btn.addEventListener("click", () => handleKey(key));
          rowDiv.appendChild(btn);
        });
        baseKb.appendChild(rowDiv);
      });
    }
  }

  function handleKeydown(e) {
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      handleKey(e.key.toLowerCase());
    }
  }

  async function handleKey(key) {
    if (disabledKeys.has(key)) return;

    const resp = await fetch("/api/v1/exercises/diacritic-typing/keystroke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: key }),
    });
    const data = await resp.json();

    if (data.data) {
      display = data.data.display || display;
      cursor = display.indexOf("_");
      renderDisplay();

      if (data.data.finished) {
        const errors = data.data.errors || 0;
        if (errors === 0) {
          showMessage("Perfect! No errors.", "is-success");
        } else {
          showMessage(`Done with ${errors} error(s).`, "is-warning");
        }
      } else if (!data.data.correct_so_far) {
        disabledKeys.add(key);
        renderKeyboard(["á", "à", "â", "ã", "é", "ê", "í", "ó", "ô", "õ", "ú", "ç"]);
      }
    }
  }

  function showMessage(text, cls) {
    const msg = document.getElementById("diacritic-message");
    if (!msg) return;
    msg.textContent = text;
    msg.className = "notification " + cls;
  }

  function hideMessage() {
    const msg = document.getElementById("diacritic-message");
    if (msg) msg.className = "notification is-hidden";
  }
})();

/**
 * Pair Matching exercise client-side logic.
 *
 * Manages the matching interaction between left (words) and right (translations)
 * columns. Communicates with /api/v1/exercises/pair-matching/* endpoints.
 */
(function () {
  "use strict";

  function getLanguage() {
    const el = document.getElementById("language-select");
    return el ? el.value : "pt";
  }

  let selectedLeft = null;
  let selectedRight = null;

  document.addEventListener("DOMContentLoaded", () => {
    const startBtn = document.getElementById("btn-start");
    if (startBtn) {
      startBtn.addEventListener("click", startRound);
    }
  });

  async function startRound() {
    const resp = await fetch("/api/v1/exercises/pair-matching/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: getLanguage(), target_language: "en", num_words: 5 }),
    });
    const data = await resp.json();
    renderRound(data.data);
  }

  function renderRound(data) {
    const leftCol = document.getElementById("left-column");
    const rightCol = document.getElementById("right-column");
    if (!leftCol || !rightCol) return;

    leftCol.innerHTML = "";
    rightCol.innerHTML = "";

    if (data.left_words && data.left_words.length > 0) {
      data.left_words.forEach((word) => {
        const btn = document.createElement("button");
        btn.className = "button is-outlined is-fullwidth mb-2";
        btn.textContent = word;
        btn.addEventListener("click", () => selectLeft(btn, word));
        leftCol.appendChild(btn);
      });

      data.right_words.forEach((word) => {
        const btn = document.createElement("button");
        btn.className = "button is-outlined is-fullwidth mb-2";
        btn.textContent = word;
        btn.addEventListener("click", () => selectRight(btn, word));
        rightCol.appendChild(btn);
      });
    } else {
      leftCol.innerHTML = '<p class="has-text-grey">No words available. Add words via ingestion first.</p>';
    }
  }

  function selectLeft(btn, word) {
    document.querySelectorAll("#left-column .button").forEach((b) => b.classList.remove("is-info"));
    btn.classList.add("is-info");
    selectedLeft = word;
    tryMatch();
  }

  function selectRight(btn, word) {
    document.querySelectorAll("#right-column .button").forEach((b) => b.classList.remove("is-info"));
    btn.classList.add("is-info");
    selectedRight = word;
    tryMatch();
  }

  async function tryMatch() {
    if (selectedLeft && selectedRight) {
      const resp = await fetch("/api/v1/exercises/pair-matching/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ left: selectedLeft, right: selectedRight }),
      });
      const data = await resp.json();
      const d = data.data;

      if (d.correct) {
        // Remove matched buttons
        document.querySelectorAll("#left-column .button.is-info").forEach((b) => {
          b.classList.remove("is-info", "is-outlined");
          b.classList.add("is-success");
          b.disabled = true;
        });
        document.querySelectorAll("#right-column .button.is-info").forEach((b) => {
          b.classList.remove("is-info", "is-outlined");
          b.classList.add("is-success");
          b.disabled = true;
        });
        showFeedback("Correct match!", "is-success");
      } else {
        document.querySelectorAll(".button.is-info").forEach((b) => b.classList.remove("is-info"));
        showFeedback("Not a match. Try again.", "is-danger");
      }

      selectedLeft = null;
      selectedRight = null;
    }
  }

  function showFeedback(message, cls) {
    const fb = document.getElementById("feedback");
    if (!fb) return;
    fb.textContent = message;
    fb.className = "notification mt-4 " + cls;
  }
})();

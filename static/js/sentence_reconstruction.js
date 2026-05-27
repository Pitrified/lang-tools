/**
 * Sentence Reconstruction exercise client-side logic.
 *
 * Renders shuffled word portions as clickable buttons. The user taps them in order
 * to rebuild the sentence. Communicates with
 * /api/v1/exercises/sentence-reconstruction/* endpoints.
 */
(function () {
  "use strict";

  function getLanguage() {
    const el = document.getElementById("language-select");
    return el ? el.value : "pt";
  }

  let orderedPortions = [];
  let selectedPortions = [];
  let availablePortions = [];

  document.addEventListener("DOMContentLoaded", () => {
    const newBtn = document.getElementById("btn-new-sentence");
    if (newBtn) newBtn.addEventListener("click", newSentence);
  });

  async function newSentence() {
    const resp = await fetch("/api/v1/exercises/sentence-reconstruction/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: getLanguage() }),
    });
    const data = await resp.json();

    if (data.data && data.data.translation) {
      document.getElementById("translation-text").textContent = data.data.translation;
      availablePortions = [...data.data.portions];
      selectedPortions = [];
      renderPortions();
      renderReconstructed();
      hideFeedback();
    } else {
      document.getElementById("translation-text").innerHTML =
        '<span class="has-text-grey">Not yet connected to content.</span>';
    }
  }

  function renderPortions() {
    const container = document.getElementById("portions");
    if (!container) return;
    container.innerHTML = "";

    availablePortions.forEach((portion, idx) => {
      const btn = document.createElement("button");
      btn.className = "button is-info is-outlined is-medium";
      btn.textContent = portion;
      btn.addEventListener("click", () => selectPortion(idx));
      container.appendChild(btn);
    });
  }

  function renderReconstructed() {
    const container = document.getElementById("reconstructed");
    if (!container) return;

    if (selectedPortions.length === 0) {
      container.innerHTML = '<p class="is-size-5 is-family-monospace">&nbsp;</p>';
    } else {
      container.innerHTML =
        '<p class="is-size-5 is-family-monospace">' +
        selectedPortions.join(" ") +
        "</p>";
    }
  }

  function selectPortion(idx) {
    const portion = availablePortions.splice(idx, 1)[0];
    selectedPortions.push(portion);
    renderPortions();
    renderReconstructed();

    if (availablePortions.length === 0) {
      submitReconstruction();
    }
  }

  async function submitReconstruction() {
    const resp = await fetch("/api/v1/exercises/sentence-reconstruction/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_portions: selectedPortions }),
    });
    const data = await resp.json();
    const d = data.data;

    const fb = document.getElementById("reconstruction-feedback");
    if (fb) {
      if (d.correct) {
        fb.textContent = "Correct! Well done!";
        fb.className = "notification mt-4 is-success";
      } else {
        fb.textContent = `Not quite. The correct sentence was: ${d.answer || ""}`;
        fb.className = "notification mt-4 is-warning";
      }
    }
  }

  function hideFeedback() {
    const fb = document.getElementById("reconstruction-feedback");
    if (fb) fb.className = "notification is-hidden mt-4";
  }
})();

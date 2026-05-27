/**
 * Conversational Tutor exercise client-side logic.
 *
 * Manages the chat interface between the user and the AI tutor.
 * Communicates with /api/v1/exercises/conversational-tutor/* endpoints.
 */
(function () {
  "use strict";

  let history = [];

  function getLanguage() {
    const sel = document.getElementById("language-select");
    return sel ? sel.value : "pt";
  }

  document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("btn-send");
    const input = document.getElementById("user-input");
    const suggestBtn = document.getElementById("btn-suggest-topic");

    if (sendBtn) sendBtn.addEventListener("click", sendMessage);
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
      });
    }
    if (suggestBtn) suggestBtn.addEventListener("click", suggestTopic);
  });

  async function sendMessage() {
    const input = document.getElementById("user-input");
    const topicInput = document.getElementById("topic-input");
    if (!input || !input.value.trim()) return;

    const text = input.value.trim();
    const topic = topicInput ? topicInput.value.trim() : "";
    input.value = "";

    appendMessage("user", text);

    const resp = await fetch("/api/v1/exercises/conversational-tutor/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, topic, language: getLanguage() }),
    });
    const data = await resp.json();

    if (data.data && data.data.response) {
      if (data.data.response.errors && data.data.response.errors.length > 0) {
        appendCorrection(data.data.response.correction, data.data.response.errors);
      }
      if (data.data.response.content) {
        appendMessage("tutor", data.data.response.content, data.data.response.translation);
      }
    } else {
      appendMessage("tutor", data.data.message || "Tutor not yet connected to LLM.");
    }
  }

  function appendCorrection(correctionText, errors) {
    const chatHistory = document.getElementById("chat-history");
    if (!chatHistory) return;
    removePlaceholder(chatHistory);

    const msg = document.createElement("div");
    msg.className = "mb-3 notification is-warning is-light py-2 px-3";
    let html = '<p class="is-size-7 has-text-weight-semibold mb-1">✏️ Correction</p>';
    if (correctionText) {
      html += "<p class=\"mb-2\">" + escapeHtml(correctionText) + "</p>";
    }
    for (const err of errors) {
      html += '<div class="ml-3 mb-1 is-size-7">';
      html += '<span class="has-text-danger"><s>' + escapeHtml(err.original) + "</s></span>";
      html += ' → <span class="has-text-success-dark">' + escapeHtml(err.corrected) + "</span>";
      if (err.explanation) {
        html += '<br><span class="has-text-grey-dark">' + escapeHtml(err.explanation) + "</span>";
      }
      html += "</div>";
    }
    msg.innerHTML = html;
    chatHistory.appendChild(msg);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }

  function appendMessage(role, content, translation) {
    const chatHistory = document.getElementById("chat-history");
    if (!chatHistory) return;
    removePlaceholder(chatHistory);

    const msg = document.createElement("div");
    msg.className = "mb-3";

    if (role === "user") {
      msg.innerHTML =
        '<p class="has-text-right"><span class="tag is-info is-medium">' +
        escapeHtml(content) +
        "</span></p>";
    } else {
      let html =
        '<p><span class="tag is-success is-medium is-light">' +
        escapeHtml(content) +
        "</span></p>";
      if (translation) {
        html += '<p class="is-size-7 has-text-grey ml-1">' + escapeHtml(translation) + "</p>";
      }
      msg.innerHTML = html;
    }

    chatHistory.appendChild(msg);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    history.push({ role, content });
  }

  function removePlaceholder(chatHistory) {
    const placeholder = chatHistory.querySelector(".has-text-grey.has-text-centered");
    if (placeholder) placeholder.remove();
  }

  async function suggestTopic() {
    const topicInput = document.getElementById("topic-input");
    if (topicInput) {
      topicInput.value = "Cultura e Vida Cotidiana no Brasil";
    }
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
})();

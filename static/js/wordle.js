/**
 * Wordle exercise client-side logic.
 *
 * Renders the grid and on-screen keyboard. Communicates with
 * /api/v1/exercises/wordle/* endpoints.
 */
(function () {
  "use strict";

  function getLanguage() {
    const el = document.getElementById("language-select");
    return el ? el.value : "pt";
  }

  let wordLength = 5;
  let maxAttempts = 6;
  let currentRow = 0;
  let currentCol = 0;
  let gameActive = false;
  let guesses = [];

  const KEYBOARD_ROWS = [
    "qwertyuiop".split(""),
    "asdfghjkl".split(""),
    ["Enter", ..."zxcvbnm".split(""), "Backspace"],
  ];

  document.addEventListener("DOMContentLoaded", () => {
    const newGameBtn = document.getElementById("btn-new-game");
    if (newGameBtn) newGameBtn.addEventListener("click", newGame);

    document.addEventListener("keydown", handleKeydown);
  });

  async function newGame() {
    const select = document.getElementById("word-length-select");
    wordLength = select ? parseInt(select.value, 10) : 5;
    maxAttempts = wordLength + 1;
    currentRow = 0;
    currentCol = 0;
    guesses = [];
    gameActive = true;

    hideMessage();

    const resp = await fetch("/api/v1/exercises/wordle/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: getLanguage(), word_length: wordLength }),
    });
    const result = await resp.json();
    if (result.data) {
      maxAttempts = result.data.max_attempts || maxAttempts;
    }

    renderBoard();
    renderKeyboard();
  }

  function renderBoard() {
    const board = document.getElementById("wordle-board");
    if (!board) return;
    board.innerHTML = "";

    for (let r = 0; r < maxAttempts; r++) {
      const row = document.createElement("div");
      row.className = "wordle-row";
      for (let c = 0; c < wordLength; c++) {
        const tile = document.createElement("div");
        tile.className = "wordle-tile";
        tile.id = `tile-${r}-${c}`;
        row.appendChild(tile);
      }
      board.appendChild(row);
    }
  }

  function renderKeyboard() {
    const kb = document.getElementById("wordle-keyboard");
    if (!kb) return;
    kb.innerHTML = "";

    KEYBOARD_ROWS.forEach((row) => {
      const rowDiv = document.createElement("div");
      rowDiv.className = "wordle-kb-row";
      row.forEach((key) => {
        const btn = document.createElement("button");
        btn.className = "wordle-key";
        btn.textContent = key === "Backspace" ? "⌫" : key;
        btn.dataset.key = key;
        btn.addEventListener("click", () => handleKey(key));
        rowDiv.appendChild(btn);
      });
      kb.appendChild(rowDiv);
    });
  }

  function handleKeydown(e) {
    if (!gameActive) return;
    if (e.key === "Enter") handleKey("Enter");
    else if (e.key === "Backspace") handleKey("Backspace");
    else if (/^[a-zA-Z]$/.test(e.key)) handleKey(e.key.toLowerCase());
  }

  function handleKey(key) {
    if (!gameActive) return;

    if (key === "Backspace") {
      if (currentCol > 0) {
        currentCol--;
        setTile(currentRow, currentCol, "");
      }
    } else if (key === "Enter") {
      if (currentCol === wordLength) submitGuess();
    } else if (currentCol < wordLength) {
      setTile(currentRow, currentCol, key);
      currentCol++;
    }
  }

  function setTile(row, col, letter) {
    const tile = document.getElementById(`tile-${row}-${col}`);
    if (tile) tile.textContent = letter;
  }

  async function submitGuess() {
    const guess = [];
    for (let c = 0; c < wordLength; c++) {
      const tile = document.getElementById(`tile-${currentRow}-${c}`);
      guess.push(tile ? tile.textContent : "");
    }
    const guessStr = guess.join("");
    guesses.push(guessStr);

    const resp = await fetch("/api/v1/exercises/wordle/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guess: guessStr }),
    });
    const result = await resp.json();
    const d = result.data;

    // Color tiles based on server evaluation
    d.letters.forEach((lr, c) => {
      const tile = document.getElementById(`tile-${currentRow}-${c}`);
      if (!tile) return;
      tile.classList.add(`wordle-tile-${lr.state}`);
    });

    // Update keyboard colors
    if (d.keyboard_state) {
      Object.entries(d.keyboard_state).forEach(([key, state]) => {
        const btn = document.querySelector(`.wordle-key[data-key="${key}"]`);
        if (btn) {
          btn.className = `wordle-key wordle-key-${state}`;
        }
      });
    }

    currentRow++;
    currentCol = 0;

    if (d.finished) {
      gameActive = false;
      if (d.correct) {
        showMessage("Correct! Well done!", "is-success");
      } else {
        showMessage(`Game over! The word was: ${d.answer}`, "is-warning");
      }
    }
  }

  function showMessage(text, cls) {
    const msg = document.getElementById("wordle-message");
    if (!msg) return;
    msg.textContent = text;
    msg.className = "notification " + cls;
  }

  function hideMessage() {
    const msg = document.getElementById("wordle-message");
    if (msg) msg.className = "notification is-hidden";
  }
})();

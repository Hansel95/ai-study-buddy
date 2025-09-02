const $ = (sel) => document.querySelector(sel);
const cardsEl = $("#cards");
const notesEl = $("#notes");
const userIdEl = $("#userId");
const generateBtn = $("#generateBtn");

function cardTemplate(q, a) {
  return `
    <div class="card">
      <div class="card-inner">
        <div class="face front">
          <div class="q">Q:</div>
          <div>${q}</div>
        </div>
        <div class="face back">
          <div class="q">A:</div>
          <div class="a">${a}</div>
        </div>
      </div>
    </div>
  `;
}

function render(cards) {
  if (!cards || !cards.length) {
    cardsEl.innerHTML = `<div class="empty">No flashcards yet. Generate some!</div>`;
    return;
  }
  cardsEl.innerHTML = cards.map(c => cardTemplate(c.question, c.answer)).join("");
  document.querySelectorAll(".card").forEach((el) => {
    el.addEventListener("click", () => el.classList.toggle("flipped"));
  });
}

async function fetchExisting() {
  const user = encodeURIComponent(userIdEl.value || "");
  const url = user ? `/api/flashcards?user_id=${user}` : `/api/flashcards`;
  const r = await fetch(url);
  const data = await r.json();
  render(data.flashcards || []);
}

generateBtn.addEventListener("click", async () => {
  const notes = notesEl.value.trim();
  if (!notes) return alert("Please paste some notes.");
  generateBtn.disabled = true;
  generateBtn.textContent = "Generating...";
  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ notes, user_id: userIdEl.value || null })
    });
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    render(data.flashcards || []);
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate 5 Flashcards";
  }
});

userIdEl.addEventListener("change", fetchExisting);
window.addEventListener("load", fetchExisting);
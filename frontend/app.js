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
  // For demo purposes, load from localStorage
  const stored = localStorage.getItem('flashcards');
  const cards = stored ? JSON.parse(stored) : [];
  render(cards);
}

generateBtn.addEventListener("click", async () => {
  const notes = notesEl.value.trim();
  if (!notes) return alert("Please paste some notes.");
  generateBtn.disabled = true;
  generateBtn.textContent = "Generating...";
  try {
    // Generate flashcards locally for demo
    const flashcards = generateFlashcardsFromNotes(notes);
    
    // Store in localStorage
    const existing = JSON.parse(localStorage.getItem('flashcards') || '[]');
    const updated = [...flashcards, ...existing];
    localStorage.setItem('flashcards', JSON.stringify(updated));
    
    render(flashcards);
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate 5 Flashcards";
  }
});

userIdEl.addEventListener("change", fetchExisting);
window.addEventListener("load", fetchExisting);

function generateFlashcardsFromNotes(notes) {
  // Simple local flashcard generator
  const sentences = notes.split(/[.!?]+/).filter(s => s.trim().length > 10);
  const flashcards = [];
  
  for (let i = 0; i < Math.min(5, sentences.length); i++) {
    const sentence = sentences[i].trim();
    const words = sentence.split(' ').filter(w => w.length > 3);
    const keyWord = words[Math.floor(Math.random() * words.length)] || 'concept';
    
    flashcards.push({
      question: `What is the main point about ${keyWord.toLowerCase()}?`,
      answer: sentence,
      created_at: new Date().toISOString(),
      user_id: userIdEl.value || 'demo'
    });
  }
  
  // If we don't have enough sentences, create some generic questions
  while (flashcards.length < 5) {
    const topics = ['key concepts', 'main ideas', 'important details', 'core principles', 'essential facts'];
    const topic = topics[flashcards.length % topics.length];
    
    flashcards.push({
      question: `What are the ${topic} from these notes?`,
      answer: notes.substring(0, 200) + (notes.length > 200 ? '...' : ''),
      created_at: new Date().toISOString(),
      user_id: userIdEl.value || 'demo'
    });
  }
  
  return flashcards;
}
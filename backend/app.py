import os
import re
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import requests
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

HF_MODEL_CANDIDATES = [
	"google/flan-t5-base",
	"google/flan-t5-small",
	"bigscience/mt0-small",
	"bigscience/T0pp",
]

def hf_headers():
	token = os.getenv("HF_API_TOKEN", "")
	return {"Authorization": f"Bearer {token}"} if token else {}

SYSTEM_PROMPT = (
	"You are a study assistant. Given raw study notes, generate exactly 5 concise quiz flashcards. "
	"Return a valid JSON array. Each item must have 'question' and 'answer' fields. Keep answers 1-3 sentences."
)

def call_hf(model: str, prompt: str):
	endpoint = f"https://api-inference.huggingface.co/models/{model}?wait_for_model=true"
	payload = {"inputs": prompt, "parameters": {"max_new_tokens": 512, "temperature": 0.3}}
	print("HF endpoint:", endpoint)
	r = requests.post(endpoint, headers=hf_headers(), json=payload, timeout=60)
	if r.status_code != 200:
		print("HF error:", r.status_code, r.text[:300])
	r.raise_for_status()
	return r.json()

def try_hf_generate(notes: str):
	prompt = f"""{SYSTEM_PROMPT}

Notes:
\"\"\"{notes}\"\"\"

Return only JSON, e.g.:
[
  {{ "question": "Q1?", "answer": "A1" }},
  ...
]
"""
	last_err = None
	data = None
	for model in HF_MODEL_CANDIDATES:
		try:
			data = call_hf(model, prompt)
			break
		except requests.HTTPError as e:
			if e.response is not None and e.response.status_code in (401, 403, 404, 429, 500, 502, 503, 524):
				last_err = e
				continue
			last_err = e
			break
		except Exception as e:
			last_err = e
			continue
	if data is None:
		raise RuntimeError(f"All HF models failed. Last error: {last_err}")

	# Normalize text from HF response
	if isinstance(data, list) and data and isinstance(data[0], dict):
		text = data[0].get("generated_text") or data[0].get("summary_text") or json.dumps(data)
	elif isinstance(data, dict):
		text = data.get("generated_text") or data.get("summary_text") or json.dumps(data)
	else:
		text = str(data)

	# Extract JSON array
	match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
	if not match:
		lines = [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip()]
		pairs = []
		for ln in lines:
			if ":" in ln:
				q, a = ln.split(":", 1)
				if q.lower().startswith("q"):
					pairs.append({"question": a.strip() or q.strip(), "answer": a.strip()})
		if pairs:
			return pairs[:5]
		raise ValueError("AI did not return a JSON array of flashcards.")
	arr_text = match.group(0)
	return json.loads(arr_text)

def generate_fallback_flashcards(notes: str):
	# Simple local generator: split sentences and build 5 Q/A pairs
	txt = re.sub(r"\s+", " ", notes).strip()
	sentences = re.split(r"(?<=[.!?])\s+", txt)
	sentences = [s for s in sentences if len(s.split()) >= 5]
	if not sentences:
		sentences = [txt] if txt else ["These are sample notes about a topic."]
	topics = []
	for s in sentences[:10]:
		words = [w for w in re.findall(r"[A-Za-z\u0600-\u06FF]+", s) if len(w) > 3]
		topics.append(words[0] if words else "the topic")
	cards = []
	for i in range(5):
		source = sentences[i % len(sentences)]
		topic = topics[i % len(topics)] if topics else "the topic"
		q = f"What is the main idea of this statement about {topic}?"
		a = source
		cards.append({"question": q, "answer": a})
	return cards

def generate_flashcards_from_notes(notes: str):
	try:
		return try_hf_generate(notes)
	except Exception as e:
		print("HF generation failed, using local fallback. Reason:", str(e))
		return generate_fallback_flashcards(notes)

@app.route("/")
def root():
	return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
	full_path = Path(app.static_folder) / path
	if full_path.exists():
		return send_from_directory(app.static_folder, path)
	return send_from_directory(app.static_folder, "index.html")

@app.post("/api/generate")
def generate():
	data = request.get_json(force=True)
	notes = data.get("notes", "")
	user_id = data.get("user_id")
	if not notes.strip():
		return jsonify({"error": "notes is required"}), 400

	try:
		cards = generate_flashcards_from_notes(notes)
	except Exception as e:
		return jsonify({"error": str(e)}), 500

	rows = []
	for c in cards:
		row = {
			"user_id": user_id,
			"question": c.get("question", "").strip(),
			"answer": c.get("answer", "").strip(),
			"source_notes": notes[:4000],
		}
		rows.append(row)
	try:
		supabase.table("flashcards").insert(rows).execute()
	except Exception as e:
		print("Supabase insert error:", e)

	return jsonify({"flashcards": rows})

@app.get("/api/flashcards")
def list_cards():
	user_id = request.args.get("user_id")
	query = supabase.table("flashcards").select("*").order("created_at", desc=True)
	if user_id:
		query = query.eq("user_id", user_id)
	res = query.limit(50).execute()
	return jsonify({"flashcards": res.data or []})

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
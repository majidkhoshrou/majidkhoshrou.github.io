import os
import json
from pathlib import Path
from typing import List, Dict

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

from libs.search import get_faiss_index, load_metadata_pickle, query_index
from libs.analytics import log_visit, load_analytics_data, summarize_analytics

# ------------------------------
# 🔐 Load environment and OpenAI
# ------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

models = client.models.list()
print([m.id for m in models.data if "embedding" in m.id])

# ------------------------------
# ⚙️ Flask + CORS setup
# ------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.jinja_env.globals.update(request=request)

# CORS(app)

# ------------------------------
# 📂 Load FAISS index & metadata
# ------------------------------
data_dir = Path(__file__).resolve().parent / "data"
faiss_index_path = data_dir / "faiss.index"
chunks_path = data_dir / "metadata.pkl"

index = get_faiss_index(faiss_index_path)
metadata = load_metadata_pickle(chunks_path)
print(f"✅ FAISS index loaded with {index.ntotal} vectors")

# ------------------------------
# 🌐 Frontend Page Routes
# ------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/cv")
def cv():
    return render_template("cv.html")

@app.route("/projects")
def projects():
    return render_template("projects.html")

@app.route("/research")
def research():
    return render_template("research.html")

@app.route("/talks")
def talks():
    return render_template("talks.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/ask-mr-m")
def ask_mr_m():
    return render_template("ask-mr-m.html")

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

# ------------------------------
# 🤖 Mr. M Chat Endpoint
# ------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required."}), 400

    try:
        relevant_chunks = query_index(message, index, metadata, top_k=5)
        context = "\n\n".join([f"Source: {c['source_path']}\n{c['text']}" for c in relevant_chunks])


        messages = [
            {
                "role": "system",
                "content": (
                    "Hello! I am Mr. M — Majid's professional AI assistant. "
                    "I specialize in answering questions about Majid's background, research, work experience, and publications. "
                    "You may only answer using the provided CONTEXT. "
                    "If the context does not include the answer, politely say you don't know. Never make assumptions."
                )
            },
            { "role": "system", "content": f"CONTEXT:\n{context}" },
            { "role": "user", "content": message }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "An error occurred while generating a response."}), 500

# ------------------------------
# 📊 Analytics API Endpoints
# ------------------------------
@app.route("/api/log-visit", methods=["POST"])
def api_log_visit():
    log_visit()
    return {"status": "logged"}

@app.route("/api/analytics-data", methods=["GET"])
def api_analytics_data():
    return load_analytics_data()

@app.route("/api/analytics-summary", methods=["GET"])
def api_analytics_summary():
    return jsonify(summarize_analytics())

# ------------------------------
# 🚀 Launch
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

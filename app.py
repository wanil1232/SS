import requests
from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# 🔹 Load OpenAI API Key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("⚠ Missing OpenAI API Key. Set 'OPENAI_API_KEY' in environment variables.")

# 🔹 Database Path (Store in /tmp/ for cloud hosting)
DB_PATH = "/tmp/chat_history.db"

# 🔹 Ensure Database Exists
def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat (session_id TEXT, role TEXT, content TEXT)")
    conn.commit()
    conn.close()

initialize_database()  # ✅ Ensure database is initialized

# 🔹 Function to Save Messages in Database
def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

# 🔹 Function to Retrieve Previous Messages
def get_previous_messages(session_id, limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat WHERE session_id=? ORDER BY rowid DESC LIMIT ?", (session_id, limit))
    messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
    conn.close()
    return messages[::-1]  # Reverse order so messages are in correct sequence

# 🔹 API Route to Handle GPT-4 Turbo Requests
@app.route("/ask_gpt", methods=["POST"])
def ask_gpt():
    try:
        data = request.json
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "")

        # Save the user's message
        save_message(session_id, "user", user_message)

        # Retrieve conversation history
        history = get_previous_messages(session_id)

        # Construct OpenAI message payload
        messages = [{"role": "system", "content": "You are a helpful assistant that remembers previous messages."}] + history + [{"role": "user", "content": user_message}]

        # 🔹 Send Request to OpenAI API
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-turbo",
            "messages": messages
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

        # ✅ Debugging: Print OpenAI API response
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        # ✅ Handle API errors
        if response.status_code != 200:
            return jsonify({"error": f"OpenAI API error: {response.text}"}), 500

        response_data = response.json()

        # Check if a valid response was received
        if "choices" in response_data:
            reply = response_data["choices"][0]["message"]["content"]
        else:
            reply = "Error retrieving response from the model."

        # Save GPT's response
        save_message(session_id, "assistant", reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Add a Home Route to Prevent 404 Errors
@app.route("/")
def home():
    return "🚀 API is running!", 200

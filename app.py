import requests
from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# 🔹 OpenAI API Key (Stored in Environment Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# 🔹 Function to Save Messages in SQLite Database
def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat (session_id TEXT, role TEXT, content TEXT)")
    cursor.execute("INSERT INTO chat VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

# 🔹 Function to Retrieve Previous Messages
def get_previous_messages(session_id, limit=5):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat WHERE session_id=? ORDER BY rowid DESC LIMIT ?", (session_id, limit))
    messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
    conn.close()
    return messages[::-1]  # Reverse order so messages are in the correct sequence

# 🔹 API Route to Handle GPT-4 Turbo Requests
@app.route("/ask_gpt", methods=["POST"])
def ask_gpt():
    try:
        data = request.json
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "")

        # Save the user's message
        save_message(session_id, "user", user_message)

        # Retrieve the last few messages from the conversation
        history = get_previous_messages(session_id)

        # Construct the message payload for GPT-4 Turbo
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
        response_data = response.json()

        # Check if a valid response was received
        if "choices" in response_data:
            reply = response_data["choices"][0]["message"]["content"]
        else:
            reply = "Error retrieving response from the model."

        # Save GPT's response to the database
        save_message(session_id, "assistant", reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

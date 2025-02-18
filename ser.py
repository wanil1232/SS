
import requests
from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# 🔹 הגדרת מפתח API מהסביבה (עדיף מאשר בקובץ)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# 🔹 פונקציה לשמירת הודעות במסד נתונים
def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat (session_id TEXT, role TEXT, content TEXT)")
    cursor.execute("INSERT INTO chat VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

# 🔹 פונקציה לשליפת הודעות קודמות
def get_previous_messages(session_id, limit=5):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat WHERE session_id=? ORDER BY rowid DESC LIMIT ?", (session_id, limit))
    messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
    conn.close()
    return messages[::-1]  # הופך את הסדר כדי שהתשובות יגיעו בצורה נכונה

# 🔹 API שמבצע שליחה ל-GPT-4 Turbo באמצעות requests
@app.route("/ask_gpt", methods=["POST"])
def ask_gpt():
    try:
        data = request.json
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "")

        # שמירת הודעת המשתמש
        save_message(session_id, "user", user_message)

        # שליפת היסטוריה אחרונה
        history = get_previous_messages(session_id)

        # יצירת ההודעה למודל
        messages = [{"role": "system", "content": "אתה עוזר אישי חכם שמבוסס על שיחות קודמות."}] + history + [{"role": "user", "content": user_message}]

        # ✅ שליחת הבקשה ל-OpenAI API באמצעות requests
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

        # בדיקה אם התשובה התקבלה בהצלחה
        if "choices" in response_data:
            reply = response_data["choices"][0]["message"]["content"]
        else:
            reply = "שגיאה בקבלת תשובה מהמודל."

        # שמירת תשובת ה-GPT במסד הנתונים
        save_message(session_id, "assistant", reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

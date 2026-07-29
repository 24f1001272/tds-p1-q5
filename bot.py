import os
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from flask import Flask, send_file, jsonify
from agent import run_data_agent

load_dotenv()

# --- Flask Web Server Setup ---
server = Flask(__name__)

@server.route('/')
def home():
    return jsonify({"status": "Bot is running", "message": "Access /run.jsonl for logs."})

@server.route('/run.jsonl')
def serve_log():
    if not os.path.exists('run.jsonl'):
        return ""
    return send_file('run.jsonl', mimetype='application/jsonlines')

def run_server():
    # Render assigns a PORT dynamically. Default to 8080 for local testing.
    port = int(os.environ.get('PORT', 8080))
    server.run(host="0.0.0.0", port=port)

# --- Telegram Bot Setup ---
user_histories = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append(text)

    try:
        response_json = run_data_agent(user_histories[user_id])
        await update.message.reply_text(response_json)
    except Exception as e:
        await update.message.reply_text(f'{{"error": "{str(e)}"}}')

def main():
    # Start the Flask web server in a separate background thread
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    
    # Initialize the bot
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running. Web server on port", os.environ.get('PORT', 8080))
    app.run_polling()

if __name__ == '__main__':
    main()
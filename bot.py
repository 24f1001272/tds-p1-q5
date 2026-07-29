import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from agent import run_data_agent

load_dotenv()

# Simple memory dictionary: { user_id: [list of messages] }
user_histories = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # 1. Update this user's conversation history
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append(text)

    # 2. Pass the whole history to the agent to get the final JSON
    try:
        response_json = run_data_agent(user_histories[user_id])
        
        # 3. Reply with ONLY the JSON string. No formatting, no markdown.
        await update.message.reply_text(response_json)
        
    except Exception as e:
        # Fallback in case of a crash to keep the bot alive
        await update.message.reply_text(f'{{"error": "{str(e)}"}')

def main():
    # Initialize the bot
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Listen for any text message that isn't a command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
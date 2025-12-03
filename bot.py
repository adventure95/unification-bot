# bot.py
import logging
from telegram import Update
from telegram.ext import Application, ChatMemberHandler, MessageHandler, filters

# --- CONFIG ---
# 👇 PASTE YOUR NEW BOT TOKEN HERE (between the quotes)
BOT_TOKEN = "YOUR_NEW_TOKEN_HERE"

WELCOME_MSG = (
    "🎉 Welcome to *Unification Zone*!\n\n"
    "📚 A peer-learning hub for Grade 11 Natural Science.\n"
    "📌 Please:\n"
    "• Post in the correct *subject topic*\n"
    "• Be kind & helpful\n"
    "• No ads, links, or spam\n\n"
    "Let’s grow smarter together! 💡"
)

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- HANDLERS ---
async def welcome(update: Update, context):
    if update.chat_member:
        new_status = update.chat_member.new_chat_member.status
        if new_status == "member":  # New user joined
            chat_id = update.chat_member.chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=WELCOME_MSG,
                parse_mode="Markdown"
            )

async def auto_delete_spam(update: Update, context):
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.lower()
    spam_triggers = ["http", "t.me/", "join", "free", "gift", "click", "subscribe", ".com"]
    if any(word in text for word in spam_triggers):
        try:
            await msg.delete()
            await msg.reply_text("❌ Off-topic or spam message removed.")
        except Exception as e:
            logging.warning(f"Couldn’t delete message: {e}")

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT, auto_delete_spam))
    app.run_polling()

if __name__ == "__main__":
    main()
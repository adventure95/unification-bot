# bot.py
import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_LOG_CHAT_ID = int(os.getenv("ADMIN_LOG_CHAT_ID"))
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID"))  # Your Telegram user ID

if not BOT_MODE:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

# === HANDLERS ===

async def log_new_member(update: Update, context):
    """Triggered when someone joins the main group"""
    if not update.chat_member:
        return

    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status
    if old_status == "left" and new_status == "member":
        user = update.chat_member.new_chat_member.user
        join_time = update.chat_member.date

        # Try to send private verification message
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "👋 Welcome to *Unification Zone*!\n\n"
                    "To keep our study group secure and organized, please verify:\n\n"
                    "👉 Send this command in this chat:\n"
                    "`/verify <room_number> <roll_number>`\n\n"
                    "Example: `/verify 4 5`\n\n"
                    "💡 Your room & roll number are from your class attendance list."
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.warning(f"Could not DM {user.full_name} ({user.id}): {e}")

        # Log join to admin group
        log_msg = (
            f"🆕 *New Member Joined*\n"
            f"👤 {user.full_name} (`{user.id}`)\n"
            f"🕒 {join_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"📩 *Sent verification request*"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_LOG_CHAT_ID,
                text=log_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Failed to log to admin group: {e}")

        # Save to pending list
        context.bot_data.setdefault("pending", {})[user.id] = {
            "name": user.full_name,
            "join_time": join_time,
            "verified": False
        }

async def handle_verify(update: Update, context):
    """Handle /verify command in private chat"""
    user = update.effective_user
    args = context.args

    if len(args) != 2:
        await update.message.reply_text(
            "UsageId: `/verify <room> <roll>`\nExample: `/verify 4 5`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    room, roll = args[0], args[1]

    if not (room.isdigit() and roll.isdigit()):
        await update.message.reply_text("❌ Room and roll must be numbers (e.g., 4 and 5).")
        return

    # Mark as verified
    pending = context.bot_data.get("pending", {})
    if user.id in pending:
        pending[user.id]["verified"] = True
        pending[user.id]["room"] = room
        pending[user.id]["roll"] = roll

    # Notify admin
    await context.bot.send_message(
        chat_id=ADMIN_LOG_CHAT_ID,
        text=(
            f"✅ *Verification Complete*\n"
            f"👤 {user.full_name} (`{user.id}`)\n"
            f"🏠 Room: {room} • 📋 Roll: #{roll}\n\n"
            f"🔔 *Action:* Promote as restricted admin with title `Room {room} • #{roll}`"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

    await update.message.reply_text(
        f"✅ Verified! Welcome to Unification Zone, {user.first_name}!\n\n"
        f"An admin will assign your role shortly."
    )

async def handle_spam(update: Update, context):
    """Delete obvious spam in the main group"""
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.lower()
    spam_triggers = ["http", "t.me/", "join", "free", "gift", "click", "subscribe", ".com", "https"]
    if any(trigger in text for trigger in spam_triggers):
        try:
            await msg.delete()
            await msg.reply_text("❌ Off-topic or spam message removed.", quote=False)
        except Exception as e:
            logging.warning(f"Failed to delete spam: {e}")

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(ChatMemberHandler(log_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("verify", handle_verify))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spam))

    logging.info("Bot starting...")
    app.run_polling()

if __name __ == "__main__":
    main()

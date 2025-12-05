# bot.py
# Final version: guided verification + role-based commands — 2025-12-05

import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
from telegram.constants import ParseMode

# === CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_LOG_CHAT_ID = os.getenv("ADMIN_LOG_CHAT_ID")
OWNER_USER_ID = os.getenv("OWNER_USER_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Missing BOT_TOKEN in environment variables!")
if not ADMIN_LOG_CHAT_ID:
    raise ValueError("❌ Missing ADMIN_LOG_CHAT_ID in environment variables!")

try:
    ADMIN_LOG_CHAT_ID = int(ADMIN_LOG_CHAT_ID)
except ValueError:
    raise ValueError("❌ ADMIN_LOG_CHAT_ID must be a valid integer (e.g., -1001234567890)")

# === ROLES ===
OWNER_ID = int(OWNER_USER_ID) if OWNER_USER_ID else None
# Add trusted admin IDs here later: {123456789, 987654321}
ADMIN_IDS = set()

def is_owner(user_id: int) -> bool:
    return OWNER_ID is not None and user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    return is_owner(user_id) or user_id in ADMIN_IDS

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === CONVERSATION STATES ===
ROOM, ROLL = range(2)

# === HANDLERS ===

async def log_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when someone joins the main group"""
    if not update.chat_member:
        return

    old_status = update.chat_member.old_chat_member.status
    new_status = update.chat_member.new_chat_member.status
    if old_status == "left" and new_status == "member":
        user = update.chat_member.new_chat_member.user
        chat = update.chat_member.chat
        join_time = update.chat_member.date

        # Try sending private DM
        dm_status = "✅ DM sent"
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "👋 Welcome!\n\n"
                    "To verify your class info, please start a chat with me:\n"
                    "1. Tap this link → @ROTL_Ini420kY\n"
                    "2. Press **Start**\n"
                    "3. Follow the steps!"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.warning(f"Could not DM {user.full_name} ({user.id}): {e}")
            dm_status = "❌ DM failed"

        # Public welcome in group with mention
        welcome_text = (
            f"👋 Welcome, {user.mention_html()}!\n\n"
            "Please verify your class info:\n"
            "1️⃣ Tap → @ROTL_Ini420kY\n"
            "2️⃣ Press **Start**\n"
            "3️⃣ Follow the steps!"
        )
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Failed to send public welcome: {e}")

        # Log to admin group
        username = f"@{user.username}" if user.username else user.full_name
        log_msg = (
            f"🆕 *New Member Joined*\n"
            f"👤 {username} (`{user.id}`)\n"
            f"📅 Joined: {join_time.strftime('%Y-%m-%d at %H:%M')}\n"
            f"📩 {dm_status}"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_LOG_CHAT_ID,
                text=log_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Failed to log to admin group: {e}")

        # Save to pending
        context.bot_data.setdefault("pending", {})[user.id] = {
            "name": user.full_name,
            "join_time": join_time,
            "verified": False
        }

# === CONVERSATION: START → ROOM → ROLL ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "Let’s verify your class info step by step.\n\n"
        "➡️ What’s your *room number*? (e.g., 4)"
    )
    return ROOM

async def get_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room = update.message.text.strip()
    if not room.isdigit():
        await update.message.reply_text("❌ Please enter a *number* (e.g., 4).")
        return ROOM
    context.user_data["room"] = room
    await update.message.reply_text(
        f"✅ Room {room} recorded!\n\n"
        "➡️ Now, what’s your *roll number* from your attendance list? (e.g., 5)"
    )
    return ROLL

async def get_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roll = update.message.text.strip()
    if not roll.isdigit():
        await update.message.reply_text("❌ Please enter a *number* (e.g., 5).")
        return ROLL

    room = context.user_data["room"]
    user = update.effective_user

    # Mark as verified
    context.bot_data.setdefault("pending", {})[user.id] = {
        "name": user.full_name,
        "room": room,
        "roll": roll,
        "verified": True,
        "join_time": context.bot_data.get("pending", {}).get(user.id, {}).get("join_time", datetime.now())
    }

    # Notify admin group
    username = f"@{user.username}" if user.username else user.full_name
    await context.bot.send_message(
        chat_id=ADMIN_LOG_CHAT_ID,
        text=(
            f"✅ *Verification Complete*\n"
            f"👤 {username} (`{user.id}`)\n"
            f"🏠 Room: {room} • 📋 Roll: #{roll}\n"
            f"📅 Joined: {context.bot_data['pending'][user.id]['join_time'].strftime('%Y-%m-%d at %H:%M')}\n\n"
            f"🔔 *Action:* Promote as restricted admin with title `Room {room} • #{roll}`"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

    await update.message.reply_text(
        f"✅ Verified! You’re **Room {room} • #{roll}**.\n\n"
        "An admin will assign your role shortly. Thank you for helping keep our group organized! 🙌"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Verification cancelled. Send /start to try again.")
    return ConversationHandler.END

# === ROLE-BASED COMMANDS ===

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_owner(user.id):
        await update.message.reply_text(
            "ℹ️ This command is restricted to the owner.",
            quote=False
        )
        return

    pending_count = len([
        u for u in context.bot_data.get("pending", {}).values() 
        if not u.get("verified")
    ])
    chat = update.effective_chat
    message = (
        "🔐 *Owner Status*\n"
        f"🟢 Bot: Active\n"
        f"👥 Pending verifications: {pending_count}\n"
        f"🏘️ Group: {chat.title if chat.title else 'Unknown'}"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, quote=False)

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🔒 Admin-only command.", quote=False)
        return

    pending = context.bot_data.get("pending", {})
    unverified = [
        f"• {data['name']} (joined {data['join_time'].strftime('%m-%d')})" 
        for uid, data in pending.items() if not data.get("verified")
    ]
    
    if not unverified:
        await update.message.reply_text("✅ All members verified!", quote=False)
    else:
        await update.message.reply_text(
            "📋 *Unverified Members*\n" + "\n".join(unverified),
            parse_mode=ParseMode.MARKDOWN,
            quote=False
        )

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room)],
            ROLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_roll)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(ChatMemberHandler(log_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("list_pending", list_pending))

    logging.info("🤖 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()


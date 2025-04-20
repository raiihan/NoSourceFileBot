import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# ------------------- CONFIG -------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-render-url.com/webhook
STORE_CHANNEL_ID = -1002676143465  # Store Room 🏬
OWNER_ID = 1615680044  # You
# ----------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- START / DEEP LINK DOWNLOAD ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    if update.message:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

    if not args:
        await context.bot.send_message(chat_id, "Welcome! Please use a valid download link.")
        return

    msg_id = args[0]
    loading = await context.bot.send_message(chat_id, "⏳ Preparing your file, please wait...")

    try:
        msg = await context.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=STORE_CHANNEL_ID,
            message_id=int(msg_id),
            disable_notification=True,
        )
        await context.bot.delete_message(chat_id, loading.message_id)

        caption = "✅ Your file is ready!\n\n"
        if msg.document:
            name = msg.document.file_name
            size = round(msg.document.file_size / 1024 / 1024, 2)
            typ = msg.document.mime_type
            caption += f"📄 Name: {name}\n📦 Size: {size} MB\n🧾 Type: {typ}"
        elif msg.video:
            caption += "🎥 A video file has been prepared."
        else:
            caption += "📁 Your file has been prepared."

        btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬇ Download Now", url=msg.link if msg.link else "")]])
        await context.bot.send_message(chat_id, caption, reply_markup=btn)

    except Exception as e:
        await context.bot.delete_message(chat_id, loading.message_id)
        logger.error(f"Failed to fetch file: {e}")
        await context.bot.send_message(chat_id, "❌ File not found or expired.")

# ---------- ADMIN STATS ----------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text("✅ Bot is running smoothly!")

# ---------- FILE UPLOADER ----------
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    # Check if admin of store room
    try:
        member = await context.bot.get_chat_member(STORE_CHANNEL_ID, user_id)
        if member.status not in ("administrator", "creator"):
            return  # silently ignore
    except Exception as e:
        logger.warning(f"Upload access denied: {e}")
        return

    if not message.document and not message.video and not message.audio:
        return  # Only allow file uploads

    # Forward to Store Room
    try:
        forwarded = await message.forward(chat_id=STORE_CHANNEL_ID)

        # Generate deep link
        deep_link = f"https://t.me/{context.bot.username}?start={forwarded.message_id}"

        # Confirmation message with buttons
        caption = (
            f"✅ File uploaded successfully!\n"
            f"🔗 Deep Link: `{deep_link}`"
        )
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📥 Get File Link", url=deep_link)]]
        )
        await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

        # Auto-delete original message
        await message.delete()
    except Exception as e:
        logger.error(f"Upload failed: {e}")

# ---------- MAIN ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set webhook cleanly
    await app.bot.delete_webhook()
    await app.bot.set_webhook(url=WEBHOOK_URL)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_upload))

    print("Uploader+Downloader bot running with webhook...")
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

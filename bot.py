import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORE_CHANNEL_ID = -1002676143465  # Your private store channel ID
ADMIN_ID = 1615680044  # Your Telegram user ID (for /stats)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# START command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.effective_chat.id

    # Delete previous messages (clean UI)
    if update.message:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)

    # Check if there's a message ID in deep link
    if not args:
        await context.bot.send_message(chat_id, "Welcome! Please use a valid download link from our channel.")
        return

    msg_id = args[0]

    # Show loading message
    loading = await context.bot.send_message(chat_id, "⏳ Preparing your file, please wait...")

    try:
        # Fetch message from store channel
        msg = await context.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=STORE_CHANNEL_ID,
            message_id=int(msg_id),
            disable_notification=True,
        )

        # Delete loading message
        await context.bot.delete_message(chat_id, loading.message_id)

        # Optional: Edit caption with file details
        caption = f"✅ Your file is ready!\n\n"
        if msg.document:
            file_name = msg.document.file_name
            file_size = round(msg.document.file_size / 1024 / 1024, 2)
            file_type = msg.document.mime_type
            caption += f"📄 Name: {file_name}\n📦 Size: {file_size} MB\n🧾 Type: {file_type}"
        elif msg.video:
            caption += f"🎥 A video file has been prepared."
        else:
            caption += f"📁 Your file has been prepared."

        # Send caption with button
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬇ Download Now", url=msg.link if msg.link else "")]])
        await context.bot.send_message(chat_id, caption, reply_markup=btn)

    except Exception as e:
        await context.bot.delete_message(chat_id, loading.message_id)
        logger.error(f"Failed to fetch file: {e}")
        await context.bot.send_message(chat_id, "❌ File not found or link expired. Please try again later.")

# ADMIN STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return

    user = update.effective_user
    await update.message.reply_text(f"Hello {user.first_name}, your bot is running smoothly!")

# MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Remove the existing webhook (if set)
    app.bot.delete_webhook()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    # Use polling after removing webhook
    app.run_polling()

if __name__ == "__main__":
    main()

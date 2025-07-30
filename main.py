import os
import subprocess
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import pysubs2

TOKEN = "7974990873:AAHzyxu2Csca6RX6J6gWu0Y4rWAAdtzQu50"

WORKDIR = "workdir"
os.makedirs(WORKDIR, exist_ok=True)
AUTHORIZED_USERS = set()

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📁 وضعیت", callback_data="status")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        [InlineKeyboardButton("👤 پشتیبانی", url="https://t.me/YourSupportUsername")],
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        update.message.reply_text("❌ دسترسی ندارید.")
        return
    update.message.reply_text(
        "سلام!\nفایل ویدیو یا زیرنویس بفرستید تا پردازش شود.",
        reply_markup=main_keyboard(),
    )

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("🔹 ویدیو (mkv, mp4) یا زیرنویس (ass, ssa, sub, srt) بفرست تا تبدیل یا استخراج شود.")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == "status":
        query.edit_message_text("⏳ ربات فعاله. منتظر فایل شماست.")
    elif query.data == "help":
        query.edit_message_text("برای تبدیل فایل زیرنویس یا استخراج، فایل رو بفرست.")

def send_progress_message(update, context, text):
    return update.message.reply_text(text)

def update_progress_message(msg, text):
    try:
        msg.edit_text(text)
    except:
        pass

def extract_subtitles(video_path, out_path):
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-map", "0:s:0", out_path],
        capture_output=True,
        text=True,
    )

def convert_sub_to_srt(in_path, out_path):
    subs = pysubs2.load(in_path)
    subs.save(out_path)

def process_file(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
        update.message.reply_text("❌ اجازه دسترسی ندارید.")
        return

    message = update.message
    file = None
    filename = None
    ext = None

    if message.document:
        file = message.document.get_file()
        filename = message.document.file_name
        ext = os.path.splitext(filename)[1].lower()
    elif message.video:
        file = message.video.get_file()
        filename = message.video.file_name or f"video_{int(time.time())}.mp4"
        ext = os.path.splitext(filename)[1].lower()
    else:
        update.message.reply_text("فقط فایل ویدیویی یا زیرنویس پشتیبانی می‌شود.")
        return

    update.message.reply_text("📥 فایل دریافت شد، در حال پردازش...")

    local_input = os.path.join(WORKDIR, f"{user_id}_{int(time.time())}{ext}")
    file.download(custom_path=local_input)
    out_srt = local_input.rsplit(".", 1)[0] + ".srt"

    def job():
        try:
            if ext in [".mkv", ".mp4", ".avi"]:
                progress = update.message.reply_text("🎞 استخراج زیرنویس در حال انجامه...")
                extract_subtitles(local_input, out_srt)
                update_progress_message(progress, "✅ استخراج کامل شد")
                update.message.reply_document(open(out_srt, "rb"), filename=os.path.basename(out_srt))
            elif ext in [".ass", ".ssa", ".sub", ".srt"]:
                progress = update.message.reply_text("📝 در حال تبدیل زیرنویس به srt...")
                convert_sub_to_srt(local_input, out_srt)
                update_progress_message(progress, "✅ تبدیل به srt کامل شد")
                update.message.reply_document(open(out_srt, "rb"), filename=os.path.basename(out_srt))
            else:
                update.message.reply_text("❌ فرمت فایل پشتیبانی نمی‌شود.")
        except Exception as e:
            update.message.reply_text(f"خطا:\n{e}")
        try:
            os.remove(local_input)
            if os.path.exists(out_srt): os.remove(out_srt)
        except: pass

    threading.Thread(target=job).start()

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.document | Filters.video, process_file))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
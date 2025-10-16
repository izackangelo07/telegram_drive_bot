import os
import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("7974385333:AAFeoZyV5CxcfZAp503KZSpRGA6ZDGhmmog")
APPS_SCRIPT_URL = os.getenv("https://script.google.com/macros/s/AKfycby8kUKAEm4GfUNTy4q__gT6PJZGToZxMCu7yZFNM9KP1c6Ans5tP5Ckklfe_Ds3cjGxmw/exec")

async def get_file_bytes(update: Update):
    if update.message.document:
        file = await update.message.document.get_file()
        filename = update.message.document.file_name
        mime = update.message.document.mime_type or "application/octet-stream"
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        filename = "photo.jpg"
        mime = "image/jpeg"
    else:
        return None, None, None

    file_bytes = await file.download_as_bytearray()
    return file_bytes, filename, mime

async def upload_to_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.caption or ""
    folder_name = ""
    if text.startswith("/pasta "):
        folder_name = text[7:].strip()

    file_bytes, filename, mime = await get_file_bytes(update)
    if not file_bytes:
        await update.message.reply_text("Envie um documento ou foto.")
        return

    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
    data = {
        "file": file_b64,
        "filename": filename,
        "mimeType": mime,
        "folder": folder_name
    }

    try:
        r = requests.post(APPS_SCRIPT_URL, data=data)
        await update.message.reply_text(r.text)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao enviar: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, upload_to_drive))

print("🤖 Bot rodando... Envie arquivos ou fotos com /pasta NomeDaSubpasta!")
app.run_polling()

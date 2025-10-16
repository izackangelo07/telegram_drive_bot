from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
PORT = int(os.environ.get('PORT', 8443))

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie um arquivo ou imagem para salvar no Google Drive!")

app.add_handler(CommandHandler("start", start))

# Recebe documentos e fotos
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None

    if update.message.document:
        file = await update.message.document.get_file()
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()

    if file:
        # Baixa para memória
        file_bytes = await file.download_as_bytearray()

        # Envia para o Apps Script
        files = {"file": ("file", file_bytes)}
        response = requests.post(APPS_SCRIPT_URL, files=files)
        response_text = response.text

        # Verifica se foi enviado corretamente
        if "✅" in response_text:
            await update.message.reply_text(f"✅ Enviado com sucesso!\n{response_text}")
        else:
            await update.message.reply_text(f"❌ Falha ao enviar para o Drive:\n{response_text}")
    else:
        await update.message.reply_text("Envie um arquivo ou foto, por favor.")

app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, upload))

# Webhook para Render
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="",
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
    )

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
PORT = int(os.environ.get('PORT', 8443))

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Exemplo de comando
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie um arquivo ou imagem para salvar no Google Drive!")

app.add_handler(CommandHandler("start", start))

# Recebe documentos e fotos
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    file_name = None

    if update.message.document:
        file = update.message.document.get_file()
        file_name = update.message.document.file_name
    elif update.message.photo:
        file = update.message.photo[-1].get_file()
        file_name = "photo.jpg"

    if file:
        file_path = f"/tmp/{file_name}"
        await file.download_to_drive(file_path)
        
        with open(file_path, "rb") as f:
            response = requests.post(APPS_SCRIPT_URL, files={"file": f})
        
        await update.message.reply_text("✅ Enviado com sucesso para o Drive!")
    else:
        await update.message.reply_text("Envie um arquivo ou foto, por favor.")

app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, upload))

# Webhook — necessário para Render
if __name__ == "__main__":
    import asyncio

    async def main():
        await app.bot.set_webhook(f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/")
        await app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="",
            webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
        )

    asyncio.run(main())

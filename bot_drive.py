from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
PORT = int(os.environ.get('PORT', 8443))

# Subpastas por chat
chat_folders = {}

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envie um arquivo ou imagem para salvar no Google Drive!\n"
        "Use /setfolder NomeDaPasta para definir uma subpasta opcional."
    )

# Comando /setfolder
async def setfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.args:
        folder_name = " ".join(context.args)
        chat_folders[chat_id] = folder_name
        await update.message.reply_text(f"📂 Subpasta definida: {folder_name}")
    else:
        await update.message.reply_text("Use: /setfolder NomeDaPasta")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setfolder", setfolder))

# Recebe documentos e fotos
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    file = None
    file_name = None
    mime_type = None

    if update.message.document:
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        mime_type = update.message.document.mime_type
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_name = "photo.jpg"
        mime_type = "image/jpeg"

    if file:
        try:
            # Baixa para memória
            file_bytes = await file.download_as_bytearray()

            # Prepara dados para Apps Script
            files = {"file": (file_name, file_bytes, mime_type)}
            data = {}
            if chat_id in chat_folders:
                data["folder"] = chat_folders[chat_id]

            # Envia para o Apps Script
            response = requests.post(APPS_SCRIPT_URL, files=files, data=data)
            response_text = response.text

            # Resposta detalhada
            if "✅" in response_text:
                await update.message.reply_text(f"✅ Enviado com sucesso!\n{response_text}")
            else:
                await update.message.reply_text(
                    f"❌ Falha ao enviar para o Drive.\n"
                    f"Status HTTP: {response.status_code}\n"
                    f"Nome do arquivo: {file_name}\n"
                    f"Tipo MIME: {mime_type}\n"
                    f"Resposta do servidor: {response_text}"
                )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Erro inesperado ao processar o arquivo.\nDetalhes: {str(e)}"
            )
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

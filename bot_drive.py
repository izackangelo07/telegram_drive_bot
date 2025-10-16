from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests
import base64

BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
PORT = int(os.environ.get('PORT', 8443))

# Guarda subpasta definida por chat
chat_folders = {}

app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bem-vindo!*\n\n"
        "Envie um arquivo para salvar no Google Drive.\n\n"
        "📁 *Comandos úteis:*\n"
        "• `/setfolder NomeDaPasta` — define uma subpasta.\n"
        "• `/setfolder Clientes/2025/Faturas` — cria o caminho da pasta, ou leva até uma pasta existente.\n"
        "• `/myfolder` — mostra a pasta atual.\n"
        "• `/listfolders` — lista pastas já existentes no Drive.\n"
        "• `/setfolder` sem nome — volta para a pasta raiz.",
        parse_mode="Markdown"
    )

# /setfolder
async def setfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.args:
        folder_name = " ".join(context.args)
        chat_folders[chat_id] = folder_name
        await update.message.reply_text(f"📂 Subpasta definida: `{folder_name}`", parse_mode="Markdown")
    else:
        if chat_id in chat_folders:
            del chat_folders[chat_id]
        await update.message.reply_text("📁 Agora os arquivos serão enviados para a **pasta raiz**.", parse_mode="Markdown")

# /myfolder
async def myfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    folder = chat_folders.get(chat_id)
    if folder:
        await update.message.reply_text(f"📂 Pasta atual: `{folder}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("📁 Você está enviando para a **pasta raiz**.", parse_mode="Markdown")

# /listfolders
async def listfolders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(APPS_SCRIPT_URL + "?action=list")
        folders = response.json()

        if not folders:
            await update.message.reply_text("📁 Nenhuma pasta encontrada ainda.")
            return

        message = "📂 *Pastas disponíveis no Drive:*\n\n"
        for f in folders:
            name = f["name"]
            folder_id = f["id"]
            link = f"https://drive.google.com/drive/folders/{folder_id}"
            message += f"• [{name}]({link})\n"

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao listar pastas: {str(e)}")


# Upload de arquivos/fotos
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

    if not file:
        await update.message.reply_text("📎 Envie um arquivo ou foto, por favor.")
        return

    try:
        file_bytes = await file.download_as_bytearray()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")

        data = {
            "file": encoded_file,
            "filename": file_name,
            "mimeType": mime_type,
        }
        if chat_id in chat_folders:
            data["folder"] = chat_folders[chat_id]

        response = requests.post(APPS_SCRIPT_URL, data=data)
        response_text = response.text

        if "✅" in response_text:
            await update.message.reply_text(f"✅ Enviado com sucesso!\n{response_text}")
        else:
            await update.message.reply_text(
                f"❌ Falha ao enviar para o Drive.\n\n"
                f"📄 Nome: {file_name}\n"
                f"📁 Pasta: {chat_folders.get(chat_id, 'Pasta raiz')}\n"
                f"Status HTTP: {response.status_code}\n"
                f"Resposta do servidor:\n{response_text}"
            )

    except Exception as e:
        await update.message.reply_text(f"💥 Erro inesperado: {str(e)}")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setfolder", setfolder))
app.add_handler(CommandHandler("myfolder", myfolder))
app.add_handler(CommandHandler("listfolders", listfolders))
app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, upload))

# Webhook (Render)
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="",
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
    )

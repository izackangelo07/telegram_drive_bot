from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import requests
import base64
from collections import defaultdict

# ========================
# Configurações
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
PORT = int(os.environ.get("PORT", 8443))

# Guarda subpasta definida por chat
chat_folders = {}

# Inicializa o bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

# ========================
# Funções auxiliares para listagem hierárquica com links
# ========================
def build_tree(folders):
    tree = lambda: defaultdict(tree)
    root = tree()
    id_map = {}
    for f in folders:
        parts = f["name"].split("/")
        current = root
        path_so_far = ""
        for i, part in enumerate(parts):
            current = current[part]
            path_so_far = f"{path_so_far}/{part}" if path_so_far else part
            if path_so_far not in id_map:
                id_map[path_so_far] = f["id"] if i == len(parts)-1 else None
    return root, id_map

def format_tree_clickable(d, id_map, prefix="", path_so_far=""):
    lines = []
    for k, v in d.items():
        current_path = f"{path_so_far}/{k}" if path_so_far else k
        folder_id = id_map.get(current_path)
        if folder_id:
            link_text = f"[{k}](https://drive.google.com/drive/folders/{folder_id})"
        else:
            link_text = k
        lines.append(f"{prefix}• {link_text}")
        if v:
            lines.extend(format_tree_clickable(v, id_map, prefix + "    ", current_path))
    return lines

# ========================
# Comandos do bot
# ========================
# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bem-vindo!\n\n"
        "Envie um arquivo para salvar no Google Drive.\n\n"
        "📁 Comandos úteis:\n"
        "• `/setfolder NomeDaPasta` — define uma subpasta.\n"
        "• `/setfolder Clientes/2025/Faturas` — cria o caminho da pasta, ou leva até uma pasta existente.\n"
        "• `/myfolder` — mostra a pasta atual.\n"
        "• `/listfolders` — lista pastas já existentes no Drive.\n"
        "• `/setfolder` sem nome — volta para a pasta raiz."
    )

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

async def myfolder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    folder = chat_folders.get(chat_id)
    if folder:
        await update.message.reply_text(f"📂 Pasta atual: `{folder}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("📁 Você está enviando para a **pasta raiz**.", parse_mode="Markdown")

async def listfolders(update, context):
    try:
        response = requests.get(APPS_SCRIPT_URL + "?action=list")
        folders = response.json()
        if not folders:
            await update.message.reply_text("📁 Nenhuma pasta encontrada ainda.")
            return
        tree, id_map = build_tree(folders)
        lines = format_tree_clickable(tree, id_map)
        message = "📂 Pastas disponíveis no Drive:\n\n" + "\n".join(lines)
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao listar pastas: {str(e)}")

# ========================
# Upload interativo
# ========================
ASK_FILENAME = 1

async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.document:
        file = await update.message.document.get_file()
        context.user_data["original_name"] = update.message.document.file_name
        context.user_data["mime_type"] = update.message.document.mime_type
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        context.user_data["original_name"] = "photo.jpg"
        context.user_data["mime_type"] = "image/jpeg"
    else:
        await update.message.reply_text("📎 Envie um arquivo ou foto, por favor.")
        return ConversationHandler.END

    context.user_data["file"] = file
    await update.message.reply_text(
        f"Você quer definir um nome para este arquivo antes de enviar?\n"
        f"Responda com o novo nome ou digite /skip para manter: `{context.user_data['original_name']}`",
        parse_mode="Markdown"
    )
    return ASK_FILENAME

async def ask_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    filename = user_input.strip() if user_input.strip() != "/skip" else context.user_data["original_name"]

    file = context.user_data["file"]
    file_bytes = await file.download_as_bytearray()
    encoded_file = base64.b64encode(file_bytes).decode("utf-8")

    chat_id = update.effective_chat.id
    data = {
        "file": encoded_file,
        "filename": filename,
        "mimeType": context.user_data["mime_type"],
    }
    if chat_id in chat_folders:
        data["folder"] = chat_folders[chat_id]

    response = requests.post(APPS_SCRIPT_URL, data=data)
    await update.message.reply_text(response.text)
    context.user_data.clear()
    return ConversationHandler.END

upload_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Document.ALL | filters.PHOTO, upload_start)],
    states={ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)]},
    fallbacks=[CommandHandler("skip", ask_filename)]
)

# ========================
# Registro dos handlers
# ========================
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setfolder", setfolder))
app.add_handler(CommandHandler("myfolder", myfolder))
app.add_handler(CommandHandler("listfolders", listfolders))
app.add_handler(upload_handler)

# ========================
# Webhook (Render)
# ========================
if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="",
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/",
    )

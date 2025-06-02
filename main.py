import random
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, AIORateLimiter
)

BOT_TOKEN = "8118178449:AAHULZHoHfUl9mXXj5uCvZ-viJaeMapGMNo"
APP_URL = "https://safe-predictor-bot.onrender.com"  # 🔁 Replace with your Render URL

app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()
user_data = {}

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"step": "awaiting_seed"}
    await update.message.reply_text("🔑 Please enter Server Seed:")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data:
        await update.message.reply_text("Type /start to begin.")
        return

    step = user_data[user_id].get("step")

    if step == "awaiting_seed":
        user_data[user_id]["server_seed"] = text
        user_data[user_id]["step"] = "awaiting_mines"
        await update.message.reply_text("💣 Enter number of mines (e.g., 3):")

    elif step == "awaiting_mines":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Enter a valid number of mines.")
            return
        user_data[user_id]["mines"] = int(text)
        user_data[user_id]["step"] = "awaiting_bet"
        await update.message.reply_text("💰 Enter bet amount:")

    elif step == "awaiting_bet":
        user_data[user_id]["bet_amount"] = text
        await send_prediction(update, context, user_id)

def generate_safe_positions(seed: str):
    random.seed(seed)
    positions = [(i, j) for i in range(5) for j in range(5)]
    return random.sample(positions, k=random.randint(4, 5))

def format_grid(safe_spots):
    return "\n".join("".join("✅" if (i, j) in safe_spots else "❌" for j in range(5)) for i in range(5))

async def send_prediction(update, context, user_id):
    seed = user_data[user_id]["server_seed"]
    mines = user_data[user_id]["mines"]
    amount = user_data[user_id]["bet_amount"]

    safe_spots = generate_safe_positions(seed)
    result = format_grid(safe_spots)

    text = f"{result}\nSeed - `{seed}`\nMine - `{mines}`\nBet Amount - `{amount}`"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Predict Again", callback_data="predict_again")]
    ])

    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    user_data[user_id]["step"] = "done"

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "predict_again":
        user_data[user_id] = {"step": "awaiting_seed"}
        await query.message.reply_text("🔁 Enter Server Seed:")

# Add handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
bot_app.add_handler(CallbackQueryHandler(handle_callback))

# On startup
@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.bot.set_webhook(url=f"{APP_URL}/")

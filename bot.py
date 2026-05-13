import os
import logging
import random
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)
import openpyxl
import database as db
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
RANDOMIZER_POOL = int(os.getenv('RANDOMIZER_POOL', '10'))

CB_KNOW = 'know'
CB_DONT_KNOW = 'dont_know'
CB_START_QUIZ = 'start_quiz'


def quiz_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Знаю", callback_data=CB_KNOW),
        InlineKeyboardButton("❌ Не знаю", callback_data=CB_DONT_KNOW),
    ]])


def start_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Почати", callback_data=CB_START_QUIZ),
    ]])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = db.get_word_count(user_id)

    if count == 0:
        await update.message.reply_text(
            "👋 Привіт! Надішли мені Excel файл (.xlsx) з двома колонками:\n"
            "• Колонка A: Слово англійською\n"
            "• Колонка B: Переклад українською\n\n"
            "Після цього натисни Почати і вчи слова!"
        )
    else:
        await update.message.reply_text(
            f"👋 З поверненням! У словнику {count} слів.\n"
            "Можеш надіслати новий файл щоб додати ще.",
            reply_markup=start_keyboard(),
        )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    s = db.get_stats(user_id)

    if s['total'] == 0:
        await update.message.reply_text("Словник порожній. Надішли Excel файл!")
        return

    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"• Всього слів: {s['total']}\n"
        f"• Добре знаєш (≥5 разів): {s['well_known']}\n"
        f"• Вчиш (1–4 рази): {s['learning']}\n"
        f"• Нові (0 разів): {s['new']}"
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document

    if not doc.file_name.lower().endswith(('.xlsx', '.xls')):
        await update.message.reply_text("⚠️ Потрібен файл формату .xlsx або .xls")
        return

    await update.message.reply_text("⏳ Обробляю файл...")

    try:
        tg_file = await doc.get_file()
        raw = await tg_file.download_as_bytearray()
        wb = openpyxl.load_workbook(io.BytesIO(bytes(raw)))
        sheet = wb.active

        words = []
        for row in sheet.iter_rows(min_row=1, values_only=True):
            if row and len(row) >= 2 and row[0] and row[1]:
                en = str(row[0]).strip()
                uk = str(row[1]).strip()
                if en and uk:
                    words.append((en, uk))

        if not words:
            await update.message.reply_text(
                "⚠️ Файл порожній або неправильний формат.\n"
                "Перевір: колонка A — англійське слово, колонка B — переклад."
            )
            return

        added = db.add_words(user_id, words)
        total = db.get_word_count(user_id)

        await update.message.reply_text(
            f"✅ Додано {added} нових слів! (дублікати пропущено)\n"
            f"Всього у словнику: {total} слів.",
            reply_markup=start_keyboard(),
        )

    except Exception as e:
        logger.error(f"File processing error for user {user_id}: {e}")
        await update.message.reply_text("❌ Помилка при обробці файлу. Спробуй ще раз.")


def pick_next_word(user_id: int, exclude_id: int = None):
    words = db.get_least_known_words(user_id, RANDOMIZER_POOL, exclude_id)
    if not words:
        return None
    return random.choice(words)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if data == CB_START_QUIZ:
        word = pick_next_word(user_id)
        if not word:
            await query.message.reply_text("⚠️ Немає слів для вивчення! Надішли Excel файл.")
            return
        db.set_current_word(user_id, word['id'])
        await query.message.reply_text(word['english'], reply_markup=quiz_keyboard())
        return

    current = db.get_current_word(user_id)
    if not current:
        await query.message.reply_text("⚠️ Сесія не активна. Натисни /start.")
        return

    if data == CB_KNOW:
        db.increment_know_count(current['id'])
        next_word = pick_next_word(user_id)
        db.set_current_word(user_id, next_word['id'])
        await query.message.reply_text(next_word['english'], reply_markup=quiz_keyboard())

    elif data == CB_DONT_KNOW:
        # exclude current word to avoid showing it twice in a row; fallback if only 1 word
        next_word = pick_next_word(user_id, exclude_id=current['id']) or pick_next_word(user_id)
        translation = f"📖 {current['english']} — {current['ukrainian']}"
        db.set_current_word(user_id, next_word['id'])
        await query.message.reply_text(
            f"{translation}\n\n{next_word['english']}",
            reply_markup=quiz_keyboard(),
        )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не знайдено в .env файлі")

    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

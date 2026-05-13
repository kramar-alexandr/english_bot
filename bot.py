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
CB_CHANGE_LANG = 'change_lang'


# --- language helpers (stored in context.user_data, not DB) ---

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get('lang', 'en')


def toggle_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = 'uk' if get_lang(context) == 'en' else 'en'
    context.user_data['lang'] = lang
    return lang


def lang_label(lang: str) -> str:
    return "🇬🇧 EN→UA" if lang == 'en' else "🇺🇦 UA→EN"


# --- keyboards ---

def quiz_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Знаю", callback_data=CB_KNOW),
            InlineKeyboardButton("❌ Не знаю", callback_data=CB_DONT_KNOW),
        ],
        [InlineKeyboardButton("🔄 Змінити мову", callback_data=CB_CHANGE_LANG)],
    ])


def start_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Почати", callback_data=CB_START_QUIZ),
    ]])


# --- word display helpers ---

def word_question(word: dict, lang: str) -> str:
    return word['english'] if lang == 'en' else word['ukrainian']


def word_answer(word: dict, lang: str) -> str:
    if lang == 'en':
        return f"📖 {word['english']} — {word['ukrainian']}"
    return f"📖 {word['ukrainian']} — {word['english']}"


# --- commands ---

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
        f"• Добре знаєш EN→UA (≥5): {s['well_known']}\n"
        f"• Вчиш EN→UA (1–4): {s['learning']}\n"
        f"• Нові EN→UA (0): {s['new']}"
    )


# --- file upload ---

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


# --- quiz logic ---

def pick_next_word(user_id: int, lang: str, exclude_id: int = None) -> dict:
    words = db.get_least_known_words(user_id, RANDOMIZER_POOL, exclude_id, lang)
    if not words and exclude_id:
        words = db.get_least_known_words(user_id, RANDOMIZER_POOL, lang=lang)
    return random.choice(words) if words else None


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data
    lang = get_lang(context)

    if data == CB_START_QUIZ:
        word = pick_next_word(user_id, lang)
        if not word:
            await query.message.reply_text("⚠️ Немає слів для вивчення! Надішли Excel файл.")
            return
        db.set_current_word(user_id, word['id'])
        await query.message.reply_text(
            f"{lang_label(lang)}\n{word_question(word, lang)}",
            reply_markup=quiz_keyboard(),
        )
        return

    current = db.get_current_word(user_id)
    if not current:
        await query.message.reply_text("⚠️ Сесія не активна. Натисни /start.")
        return

    if data == CB_KNOW:
        db.increment_know_count(current['id'], lang)
        next_word = pick_next_word(user_id, lang)
        db.set_current_word(user_id, next_word['id'])
        await query.message.reply_text(
            f"{lang_label(lang)}\n{word_question(next_word, lang)}",
            reply_markup=quiz_keyboard(),
        )

    elif data == CB_DONT_KNOW:
        next_word = pick_next_word(user_id, lang, exclude_id=current['id'])
        db.set_current_word(user_id, next_word['id'])
        await query.message.reply_text(
            f"{word_answer(current, lang)}\n\n{lang_label(lang)}\n{word_question(next_word, lang)}",
            reply_markup=quiz_keyboard(),
        )

    elif data == CB_CHANGE_LANG:
        lang = toggle_lang(context)
        next_word = pick_next_word(user_id, lang)
        if not next_word:
            await query.message.reply_text(f"⚠️ Немає слів. Надішли Excel файл.")
            return
        db.set_current_word(user_id, next_word['id'])
        await query.message.reply_text(
            f"{lang_label(lang)}\n{word_question(next_word, lang)}",
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

import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ===================== SOZLAMALAR =====================
BOT_TOKEN = "8993176197:AAHyj1v4Iwgag_6Q5xR9cW7OfCS3kYQ9UdY"
JIKAN_API = "https://api.jikan.moe/v4"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation state
WAITING_SEARCH = 1

# ===================== TILLAR =====================
LANGS = {
    "uz": {
        "flag": "🇺🇿",
        "name": "O'zbek",
        "welcome": (
            "🎌 <b>Anime Bot ga xush kelibsiz!</b>\n\n"
            "Men sizga anime haqida ma'lumot topib beraman.\n"
            "Quyidagi tillardan birini tanlang:"
        ),
        "choose_lang": "🌐 Tilni tanlang:",
        "lang_set": "✅ Til o'zbekchaga o'zgartirildi!",
        "ask_search": "🔍 Qidirishni xohlagan anime nomini yozing:",
        "searching": "⏳ Qidirilmoqda...",
        "not_found": "❌ Anime topilmadi. Boshqa nom kiriting.",
        "result_title": "🎌 Anime topildi!",
        "score": "⭐ Reyting",
        "episodes": "📺 Qismlar",
        "status": "📌 Holat",
        "genres": "🏷 Janrlar",
        "year": "📅 Yil",
        "synopsis": "📖 Tavsif",
        "no_synopsis": "Tavsif mavjud emas.",
        "more_results": "📋 Boshqa natijalar",
        "new_search": "🔍 Yangi qidiruv",
        "back_menu": "🏠 Bosh menyu",
        "result_num": "Natija",
        "of": "dan",
        "next": "▶️ Keyingisi",
        "prev": "◀️ Oldingisi",
        "help": (
            "ℹ️ <b>Yordam</b>\n\n"
            "/start — Botni boshlash\n"
            "/search — Anime qidirish\n"
            "/lang — Tilni o'zgartirish\n"
            "/help — Yordam\n\n"
            "Faqat anime nomini yozing va men topib beraman! 🎌"
        ),
        "unknown": "❓ Tushunmadim. /help ni bosing.",
    },
    "ru": {
        "flag": "🇷🇺",
        "name": "Русский",
        "welcome": (
            "🎌 <b>Добро пожаловать в Anime Bot!</b>\n\n"
            "Я помогу найти информацию об аниме.\n"
            "Выберите язык:"
        ),
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык изменён на русский!",
        "ask_search": "🔍 Введите название аниме для поиска:",
        "searching": "⏳ Идёт поиск...",
        "not_found": "❌ Аниме не найдено. Попробуйте другое название.",
        "result_title": "🎌 Аниме найдено!",
        "score": "⭐ Рейтинг",
        "episodes": "📺 Эпизоды",
        "status": "📌 Статус",
        "genres": "🏷 Жанры",
        "year": "📅 Год",
        "synopsis": "📖 Описание",
        "no_synopsis": "Описание отсутствует.",
        "more_results": "📋 Другие результаты",
        "new_search": "🔍 Новый поиск",
        "back_menu": "🏠 Главное меню",
        "result_num": "Результат",
        "of": "из",
        "next": "▶️ Следующий",
        "prev": "◀️ Предыдущий",
        "help": (
            "ℹ️ <b>Помощь</b>\n\n"
            "/start — Запустить бота\n"
            "/search — Поиск аниме\n"
            "/lang — Сменить язык\n"
            "/help — Помощь\n\n"
            "Просто напишите название аниме и я найду! 🎌"
        ),
        "unknown": "❓ Не понял. Нажмите /help.",
    },
    "en": {
        "flag": "🇬🇧",
        "name": "English",
        "welcome": (
            "🎌 <b>Welcome to Anime Bot!</b>\n\n"
            "I'll help you find information about anime.\n"
            "Choose your language:"
        ),
        "choose_lang": "🌐 Choose language:",
        "lang_set": "✅ Language set to English!",
        "ask_search": "🔍 Enter the anime name to search:",
        "searching": "⏳ Searching...",
        "not_found": "❌ Anime not found. Try another name.",
        "result_title": "🎌 Anime found!",
        "score": "⭐ Score",
        "episodes": "📺 Episodes",
        "status": "📌 Status",
        "genres": "🏷 Genres",
        "year": "📅 Year",
        "synopsis": "📖 Synopsis",
        "no_synopsis": "No synopsis available.",
        "more_results": "📋 More results",
        "new_search": "🔍 New search",
        "back_menu": "🏠 Main menu",
        "result_num": "Result",
        "of": "of",
        "next": "▶️ Next",
        "prev": "◀️ Previous",
        "help": (
            "ℹ️ <b>Help</b>\n\n"
            "/start — Start the bot\n"
            "/search — Search anime\n"
            "/lang — Change language\n"
            "/help — Help\n\n"
            "Just type any anime name and I'll find it! 🎌"
        ),
        "unknown": "❓ Didn't understand. Press /help.",
    },
}

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "uz")

def t(context, key):
    return LANGS[get_lang(context)][key]

# ===================== TIL TANLASH KLAVIATURASI =====================
def lang_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ])

def main_menu_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 " + ("Anime qidirish" if get_lang(context)=="uz" else "Поиск аниме" if get_lang(context)=="ru" else "Search Anime"), callback_data="do_search")],
        [InlineKeyboardButton("🌐 " + ("Tilni o'zgartirish" if get_lang(context)=="uz" else "Сменить язык" if get_lang(context)=="ru" else "Change Language"), callback_data="change_lang")],
        [InlineKeyboardButton("ℹ️ " + ("Yordam" if get_lang(context)=="uz" else "Помощь" if get_lang(context)=="ru" else "Help"), callback_data="show_help")],
    ])

# ===================== JIKAN API =====================
def search_anime(query: str) -> list:
    try:
        url = f"{JIKAN_API}/anime"
        params = {"q": query, "limit": 5, "sfw": True}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
    except Exception as e:
        logger.error(f"Jikan API xatosi: {e}")
    return []

def format_anime(anime: dict, context) -> str:
    title = anime.get("title", "—")
    title_en = anime.get("title_english") or ""
    score = anime.get("score") or "—"
    episodes = anime.get("episodes") or "—"
    status = anime.get("status") or "—"
    year = anime.get("year") or (anime.get("aired", {}).get("prop", {}).get("from", {}).get("year")) or "—"
    genres = ", ".join([g["name"] for g in anime.get("genres", [])]) or "—"
    synopsis_full = anime.get("synopsis") or t(context, "no_synopsis")
    synopsis = synopsis_full[:300] + ("..." if len(synopsis_full) > 300 else "")

    title_line = f"<b>{title}</b>"
    if title_en and title_en != title:
        title_line += f"\n<i>{title_en}</i>"

    return (
        f"🎌 {title_line}\n\n"
        f"{t(context, 'score')}: <b>{score}</b>\n"
        f"{t(context, 'episodes')}: <b>{episodes}</b>\n"
        f"{t(context, 'status')}: {status}\n"
        f"{t(context, 'year')}: {year}\n"
        f"{t(context, 'genres')}: {genres}\n\n"
        f"{t(context, 'synopsis')}:\n{synopsis}"
    )

# ===================== HANDLERLAR =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(
        LANGS[lang]["welcome"],
        parse_mode="HTML",
        reply_markup=lang_keyboard()
    )

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(
        LANGS[lang]["choose_lang"],
        reply_markup=lang_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(context, "help"), parse_mode="HTML")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(context, "ask_search"))
    return WAITING_SEARCH

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    msg = await update.message.reply_text(t(context, "searching"))

    results = search_anime(query)

    if not results:
        await msg.edit_text(t(context, "not_found"))
        return ConversationHandler.END

    context.user_data["results"] = results
    context.user_data["result_index"] = 0

    await msg.delete()
    await send_anime_result(update, context, is_new=True)
    return ConversationHandler.END

async def send_anime_result(update, context, is_new=False, query_msg=None):
    results = context.user_data.get("results", [])
    idx = context.user_data.get("result_index", 0)
    anime = results[idx]

    text = format_anime(anime, context)
    total = len(results)
    nav = f"\n\n{t(context, 'result_num')} {idx+1} {t(context, 'of')} {total}"
    text += nav

    # Navigatsiya tugmalari
    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton(t(context, "prev"), callback_data="prev_result"))
    if idx < total - 1:
        nav_buttons.append(InlineKeyboardButton(t(context, "next"), callback_data="next_result"))

    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)

    # MyAnimeList linki
    mal_url = anime.get("url")
    if mal_url:
        keyboard.append([InlineKeyboardButton("🔗 MyAnimeList", url=mal_url)])

    keyboard.append([
        InlineKeyboardButton(t(context, "new_search"), callback_data="do_search"),
        InlineKeyboardButton(t(context, "back_menu"), callback_data="back_menu"),
    ])

    image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url")

    if is_new:
        if image_url:
            await update.message.reply_photo(
                photo=image_url,
                caption=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        # Callback orqali yangilash
        query = update.callback_query
        if image_url:
            try:
                await query.edit_message_media(
                    media=__import__("telegram").InputMediaPhoto(
                        media=image_url, caption=text, parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                await query.edit_message_caption(
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            try:
                await query.edit_message_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        context.user_data["lang"] = lang
        await query.edit_message_text(
            LANGS[lang]["lang_set"] + "\n\n" + LANGS[lang]["welcome"],
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(context)
        )

    elif data == "change_lang":
        await query.edit_message_text(
            t(context, "choose_lang"),
            reply_markup=lang_keyboard()
        )

    elif data == "back_menu":
        lang = get_lang(context)
        await query.edit_message_text(
            LANGS[lang]["welcome"],
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(context)
        )

    elif data == "do_search":
        await query.message.reply_text(t(context, "ask_search"))
        context.user_data["waiting_search"] = True

    elif data == "show_help":
        await query.edit_message_text(
            t(context, "help"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t(context, "back_menu"), callback_data="back_menu")
            ]])
        )

    elif data == "next_result":
        context.user_data["result_index"] += 1
        await send_anime_result(update, context, is_new=False)

    elif data == "prev_result":
        context.user_data["result_index"] -= 1
        await send_anime_result(update, context, is_new=False)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_search"):
        context.user_data["waiting_search"] = False
        query_text = update.message.text.strip()
        msg = await update.message.reply_text(t(context, "searching"))

        results = search_anime(query_text)

        if not results:
            await msg.edit_text(t(context, "not_found"))
            return

        context.user_data["results"] = results
        context.user_data["result_index"] = 0
        await msg.delete()
        await send_anime_result(update, context, is_new=True)
    else:
        await update.message.reply_text(t(context, "unknown"))

# ===================== MAIN =====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            WAITING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Anime Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

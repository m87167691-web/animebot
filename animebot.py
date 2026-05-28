import sqlite3
import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ===================== TOKEN =====================
TOKEN = "8993176197:AAHyj1v4Iwgag_6Q5xR9cW7OfCS3kYQ9UdY
"

# ===================== KANAL IDlar =====================
CHANNEL_UZ = -1004294479649
CHANNEL_RU = -1003891594546
CHANNEL_EN = -1003771352275

# ===================== BAZA =====================
conn = sqlite3.connect('animes.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        file_id TEXT,
        lang TEXT
    )
''')
conn.commit()

users_language = {}

# ===================== ANILIST API =====================
def search_anime_anilist(query: str) -> list:
    url = "https://graphql.anilist.co"
    graphql = '''
    query ($search: String) {
        Page(page: 1, perPage: 5) {
            media(search: $search, type: ANIME) {
                id
                title { romaji english native }
                episodes
                status
                averageScore
                startDate { year }
                genres
                description(asHtml: false)
                coverImage { large }
                siteUrl
            }
        }
    }
    '''
    try:
        resp = requests.post(url, json={"query": graphql, "variables": {"search": query}}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("Page", {}).get("media", [])
    except Exception as e:
        print(f"AniList xato: {e}")
    return []

def format_anime(anime, lang, idx, total):
    title = anime.get("title", {})
    name = title.get("english") or title.get("romaji") or "—"
    name_jp = title.get("native") or ""
    score = anime.get("averageScore") or "—"
    if score != "—":
        score = f"{score}/100"
    episodes = anime.get("episodes") or "—"
    status = anime.get("status") or "—"
    year = anime.get("startDate", {}).get("year") or "—"
    genres = ", ".join(anime.get("genres", [])[:4]) or "—"
    desc = (anime.get("description") or "")[:250]
    if len(anime.get("description") or "") > 250:
        desc += "..."
    url = anime.get("siteUrl") or ""

    nav = {
        "uz": f"\n\n📄 Natija: {idx+1}/{total}",
        "en": f"\n\n📄 Result: {idx+1}/{total}",
        "ru": f"\n\n📄 Результат: {idx+1}/{total}"
    }

    if lang == "uz":
        return (
            f"🎌 <b>{name}</b>\n"
            + (f"<i>{name_jp}</i>\n" if name_jp else "")
            + f"\n⭐ Reyting: <b>{score}</b>\n"
            f"📺 Qismlar: <b>{episodes}</b>\n"
            f"📌 Holat: {status}\n"
            f"📅 Yil: {year}\n"
            f"🏷 Janr: {genres}\n\n"
            f"📖 {desc}\n"
            f"🔗 <a href='{url}'>AniList</a>"
            + nav["uz"]
        )
    elif lang == "en":
        return (
            f"🎌 <b>{name}</b>\n"
            + (f"<i>{name_jp}</i>\n" if name_jp else "")
            + f"\n⭐ Score: <b>{score}</b>\n"
            f"📺 Episodes: <b>{episodes}</b>\n"
            f"📌 Status: {status}\n"
            f"📅 Year: {year}\n"
            f"🏷 Genres: {genres}\n\n"
            f"📖 {desc}\n"
            f"🔗 <a href='{url}'>AniList</a>"
            + nav["en"]
        )
    else:
        return (
            f"🎌 <b>{name}</b>\n"
            + (f"<i>{name_jp}</i>\n" if name_jp else "")
            + f"\n⭐ Рейтинг: <b>{score}</b>\n"
            f"📺 Эпизоды: <b>{episodes}</b>\n"
            f"📌 Статус: {status}\n"
            f"📅 Год: {year}\n"
            f"🏷 Жанры: {genres}\n\n"
            f"📖 {desc}\n"
            f"🔗 <a href='{url}'>AniList</a>"
            + nav["ru"]
        )

def nav_keyboard(idx, total, lang):
    buttons = []
    row = []
    if idx > 0:
        row.append(InlineKeyboardButton("◀️", callback_data=f"nav_{idx-1}"))
    if idx < total - 1:
        row.append(InlineKeyboardButton("▶️", callback_data=f"nav_{idx+1}"))
    if row:
        buttons.append(row)
    new_search = {"uz": "🔍 Yangi qidiruv", "en": "🔍 New search", "ru": "🔍 Новый поиск"}
    buttons.append([InlineKeyboardButton(new_search[lang], callback_data="new_search")])
    return InlineKeyboardMarkup(buttons)

# ===================== KANALDAN AVTOSAQLASH =====================
# Forward va to'g'ridan to'g'ri yuklangan videolarni ham saqlaydi
async def auto_save_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    # Video yoki forward qilingan video
    video = post.video
    if not video:
        return

    chat_id = post.chat.id
    video_id = video.file_id
    caption = post.caption or post.text or "Nomsiz qism"
    # Caption dan faqat birinchi qatorni olish (nom sifatida)
    caption = caption.split('\n')[0].strip()

    if chat_id == CHANNEL_UZ:
        lang = "uz"
    elif chat_id == CHANNEL_RU:
        lang = "ru"
    elif chat_id == CHANNEL_EN:
        lang = "en"
    else:
        return

    # Bazada mavjudligini tekshirish
    cursor.execute("SELECT id FROM movies WHERE file_id = ?", (video_id,))
    if cursor.fetchone():
        print(f"⚠️ Allaqachon bor: {caption}")
        return

    cursor.execute("INSERT INTO movies (name, file_id, lang) VALUES (?, ?, ?)", (caption.lower(), video_id, lang))
    conn.commit()
    print(f"✅ Saqlandi: [{lang.upper()}] {caption}")

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇺🇸 English", "🇷🇺 Русский"]]
    await update.message.reply_text(
        "🎌 <b>Anime Bot ga xush kelibsiz!</b>\n\nTilni tanlang 👇",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===================== HELP =====================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = users_language.get(update.message.from_user.id, "uz")
    texts = {
        "uz": "ℹ️ <b>Yordam</b>\n\n/start — Botni boshlash\n/lang — Tilni o'zgartirish\n/help — Yordam\n\n🎌 Anime nomini yozing — men topib beraman!",
        "en": "ℹ️ <b>Help</b>\n\n/start — Start bot\n/lang — Change language\n/help — Help\n\n🎌 Type anime name — I'll find it!",
        "ru": "ℹ️ <b>Помощь</b>\n\n/start — Запуск\n/lang — Язык\n/help — Помощь\n\n🎌 Напишите название аниме — найду!"
    }
    await update.message.reply_text(texts[lang], parse_mode="HTML")

# ===================== LANG =====================
async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇺🇸 English", "🇷🇺 Русский"]]
    await update.message.reply_text(
        "🌐 Tilni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===================== XABARLARNI QAYTA ISHLASH =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text in ["🇺🇿 Uzbek", "🇺🇸 English", "🇷🇺 Русский"]:
        if text == "🇺🇿 Uzbek":
            users_language[user_id] = "uz"
            await update.message.reply_text("✅ Til: O'zbek\n\n🎌 Anime nomini yuboring:")
        elif text == "🇺🇸 English":
            users_language[user_id] = "en"
            await update.message.reply_text("✅ Language: English\n\n🎌 Send anime name:")
        else:
            users_language[user_id] = "ru"
            await update.message.reply_text("✅ Язык: Русский\n\n🎌 Отправьте название аниме:")
        return

    language = users_language.get(user_id, "uz")
    msgs = {"uz": "🔍 Qidirilmoqda...", "en": "🔍 Searching...", "ru": "🔍 Поиск..."}
    searching_msg = await update.message.reply_text(msgs[language])
    query = text.lower().strip()

    # 1. Tanlangan tilda bazadan qidirish
    cursor.execute("SELECT file_id, name FROM movies WHERE name LIKE ? AND lang = ?", ('%' + query + '%', language))
    results = cursor.fetchall()
    if results:
        await searching_msg.delete()
        found = {"uz": "✅ O'zbekcha topildi!", "en": "✅ Found!", "ru": "✅ Найдено!"}
        for file_id, name in results[:3]:
            await update.message.reply_video(video=file_id, caption=f"🎌 {name}\n{found[language]}")
        return

    # 2. Boshqa tillarda qidirish
    lang_names = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Ruscha", "en": "🇬🇧 Inglizcha"}
    for other_lang in [l for l in ["uz", "ru", "en"] if l != language]:
        cursor.execute("SELECT file_id, name FROM movies WHERE name LIKE ? AND lang = ?", ('%' + query + '%', other_lang))
        other_results = cursor.fetchall()
        if other_results:
            await searching_msg.delete()
            warn = {
                "uz": f"⚠️ O'zbekcha topilmadi. {lang_names[other_lang]} versiyasi:",
                "en": f"⚠️ Not found. {lang_names[other_lang]} version:",
                "ru": f"⚠️ Не найдено. Версия {lang_names[other_lang]}:"
            }
            await update.message.reply_text(warn[language])
            for file_id, name in other_results[:3]:
                await update.message.reply_video(video=file_id, caption=f"🎌 {name}")
            return

    # 3. AniList API
    animes = search_anime_anilist(text)
    if not animes:
        not_found = {"uz": "❌ Anime topilmadi.", "en": "❌ Not found.", "ru": "❌ Не найдено."}
        await searching_msg.edit_text(not_found[language])
        return

    await searching_msg.delete()
    context.user_data["animes"] = animes
    context.user_data["anime_idx"] = 0
    context.user_data["lang"] = language

    no_video = {
        "uz": "📭 Video hali yuklanmagan. Anime ma'lumoti:",
        "en": "📭 No video yet. Anime info:",
        "ru": "📭 Видео нет. Информация:"
    }
    await update.message.reply_text(no_video[language])

    anime = animes[0]
    caption = format_anime(anime, language, 0, len(animes))
    image_url = anime.get("coverImage", {}).get("large")
    keyboard = nav_keyboard(0, len(animes), language)

    try:
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="HTML", reply_markup=keyboard)
        else:
            await update.message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)

# ===================== INLINE KNOPKALAR =====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "new_search":
        lang = context.user_data.get("lang", "uz")
        msgs = {"uz": "🔍 Anime nomini yuboring:", "en": "🔍 Send anime name:", "ru": "🔍 Отправьте название:"}
        await query.message.reply_text(msgs[lang])
        return

    if data.startswith("nav_"):
        idx = int(data.split("_")[1])
        animes = context.user_data.get("animes", [])
        language = context.user_data.get("lang", "uz")
        if not animes:
            return
        context.user_data["anime_idx"] = idx
        anime = animes[idx]
        caption = format_anime(anime, language, idx, len(animes))
        image_url = anime.get("coverImage", {}).get("large")
        keyboard = nav_keyboard(idx, len(animes), language)
        try:
            if image_url:
                from telegram import InputMediaPhoto
                await query.edit_message_media(
                    media=InputMediaPhoto(media=image_url, caption=caption, parse_mode="HTML"),
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text(caption, parse_mode="HTML", reply_markup=keyboard)
        except Exception:
            try:
                await query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                pass

# ===================== MAIN =====================
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.VIDEO, auto_save_to_db))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Anime Bot ishlayapti...")
    app.run_polling()

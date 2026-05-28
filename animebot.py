import sqlite3
import requests
import httpx
from bs4 import BeautifulSoup
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
TOKEN = "8993176197:AAHyj1v4Iwgag_6Q5xR9cW7OfCS3kYQ9UdY"

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

# ===================== 🇷🇺 JUTSU PARSER (RUSCHA UCHUN) =====================
async def get_jutsu_anime_video(anime_query: str):
    formatted_name = anime_query.lower().strip().replace(" ", "-")
    url = f"https://jut.su/{formatted_name}/episode-1.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                video_tag = soup.find("video")
                if video_tag:
                    sources = video_tag.find_all("source")
                    if sources:
                        return sources[-1].get("src")
    except Exception as e:
        print(f"Jutsu Parser xato: {e}")
    return None

# ===================== 🇬🇧 GOGOANIME PARSER (INGLIZCHA UCHUN) =====================
async def get_gogo_anime_video(anime_query: str):
    formatted_name = anime_query.lower().strip().replace(" ", "-")
    url = f"https://gogoanime3.co/{formatted_name}-episode-1"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                iframe = soup.find("iframe")
                if iframe:
                    return "https:" + iframe.get("src") if not iframe.get("src").startswith("http") else iframe.get("src")
    except Exception as e:
        print(f"Gogoanime Parser xato: {e}")
    return None

# ===================== 🇯🇵 JAPANESE SOURCE (YAPONCHA ORIGINAL UCHUN) =====================
async def get_japanese_anime_info(anime_query: str):
    formatted_name = anime_query.lower().strip().replace(" ", "-")
    url = f"https://www.anime-planet.com/anime/{formatted_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return f"https://embed.anime-planet.com/anime/{formatted_name}/episode/1"
    except Exception as e:
        print(f"Japanese Parser xato: {e}")
    return None

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
    if score != "—": score = f"{score}/100"
    episodes = anime.get("episodes") or "—"
    status = anime.get("status") or "—"
    year = anime.get("startDate", {}).get("year") or "—"
    genres = ", ".join(anime.get("genres", [])[:4]) or "—"
    desc = (anime.get("description") or "")[:250]
    if len(anime.get("description") or "") > 250: desc += "..."
    url = anime.get("siteUrl") or ""

    nav = {
        "uz": f"\n\n📄 Natija: {idx+1}/{total}",
        "en": f"\n\n📄 Result: {idx+1}/{total}",
        "ru": f"\n\n📄 Результат: {idx+1}/{total}",
        "ja": f"\n\n📄 結果: {idx+1}/{total}"
    }

    if lang == "uz":
        return f"🎌 <b>{name}</b>\n" + (f"<i>{name_jp}</i>\n" if name_jp else "") + f"\n⭐ Reyting: <b>{score}</b>\n📺 Qismlar: <b>{episodes}</b>\n📌 Holat: {status}\n📅 Yil: {year}\n🏷 Janr: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["uz"]
    elif lang == "en":
        return f"🎌 <b>{name}</b>\n" + (f"<i>{name_jp}</i>\n" if name_jp else "") + f"\n⭐ Score: <b>{score}</b>\n📺 Episodes: <b>{episodes}</b>\n📌 Status: {status}\n📅 Year: {year}\n🏷 Genres: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["en"]
    elif lang == "ja":
        return f"🎌 <b>{name}</b>\n" + (f"<i>{name_jp}</i>\n" if name_jp else "") + f"\n⭐ スコア: <b>{score}</b>\n📺 エピソード: <b>{episodes}</b>\n📌 ステータス: {status}\n📅 年: {year}\n🏷 ジャンル: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["ja"]
    else:
        return f"🎌 <b>{name}</b>\n" + (f"<i>{name_jp}</i>\n" if name_jp else "") + f"\n⭐ Рейтинг: <b>{score}</b>\n📺 Эпизоды: <b>{episodes}</b>\n📌 Статус: {status}\n📅 Год: {year}\n🏷 Жанры: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["ru"]

def nav_keyboard(idx, total, lang):
    buttons = []
    row = []
    if idx > 0: row.append(InlineKeyboardButton("◀️", callback_data=f"nav_{idx-1}"))
    if idx < total - 1: row.append(InlineKeyboardButton("▶️", callback_data=f"nav_{idx+1}"))
    if row: buttons.append(row)
    new_search = {"uz": "🔍 Yangi qidiruv", "en": "🔍 New search", "ru": "🔍 Новый поиск", "ja": "🔍 新しい検索"}
    buttons.append([InlineKeyboardButton(new_search.get(lang, "🔍 Yangi qidiruv"), callback_data="new_search")])
    return InlineKeyboardMarkup(buttons)

# ===================== KANALDAN AVTOSAQLASH =====================
async def auto_save_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post: return
    video = post.video
    if not video: return

    chat_id = post.chat.id
    video_id = video.file_id
    caption = post.caption or post.text or "Nomsiz qism"
    caption = caption.split('\n')[0].strip()

    if chat_id == CHANNEL_UZ: lang = "uz"
    elif chat_id == CHANNEL_RU: lang = "ru"
    elif chat_id == CHANNEL_EN: lang = "en"
    else: return

    cursor.execute("SELECT id FROM movies WHERE file_id = ?", (video_id,))
    if cursor.fetchone(): return

    cursor.execute("INSERT INTO movies (name, file_id, lang) VALUES (?, ?, ?)", (caption.lower(), video_id, lang))
    conn.commit()

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
    await update.message.reply_text(
        "🎌 <b>Anime Bot ga xush kelibsiz! / Welcome to Anime Bot!</b>\n\nTilni tanlang / Choose language 👇",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===================== HELP =====================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = users_language.get(update.message.from_user.id, "uz")
    texts = {
        "uz": "ℹ️ <b>Yordam</b>\n\n/start — Botni boshlash\n/lang — Tilni o'zgartirish\n\n🎌 Anime nomini yozing — men topib beraman!",
        "en": "ℹ️ <b>Help</b>\n\n/start — Start bot\n/lang — Change language\n\n🎌 Type anime name — I'll find it!",
        "ru": "ℹ️ <b>Помощь</b>\n\n/start — Запуск\n/lang — Язык\n\n🎌 Напишите название аниме — найду!",
        "ja": "ℹ️ <b>ヘルプ</b>\n\n/start — スタート\n/lang — 言語変更\n\n🎌 アニメの名前を入力してください！"
    }
    await update.message.reply_text(texts.get(lang, texts["uz"]), parse_mode="HTML")

# ===================== LANG =====================
async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
    await update.message.reply_text("🌐 Tilni tanlang / Choose language:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ===================== XABARLARNI QAYTA ISHLASH =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # 1. Til tanlash tugmalari bosilganda:
    if text in ["🇺🇿 Uzbek", "🇺🇸 English", "🇷🇺 Русский", "🇯🇵 Japanese"]:
        if text == "🇺🇿 Uzbek":
            users_language[user_id] = "uz"
            await update.message.reply_text("✅ Til: O'zbek\n\n🎌 Anime nomini yuboring:")
        elif text == "🇺🇸 English":
            users_language[user_id] = "en"
            await update.message.reply_text("✅ Language: English\n\n🎌 Send anime name:")
        elif text == "🇯🇵 Japanese":
            users_language[user_id] = "ja"
            await update.message.reply_text("✅ 言語: 日本語\n\n🎌 アニメの名前を送信してください:")
        else:
            users_language[user_id] = "ru"
            await update.message.reply_text("✅ Язык: Русский\n\n🎌 Отправьте название аниме:")
        return

    # 🚨 MAJBURIY TIL TEKSHIRUVI:
    if user_id not in users_language:
        keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
        await update.message.reply_text(
            "🛑 <b>Iltimos, oldin tilni tanlang! / Choose a language! / Выберите язык! / 言語を選択してください！</b> 👇",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    language = users_language[user_id]
    msgs = {"uz": "🔍 Qidirilmoqda...", "en": "🔍 Searching...", "ru": "🔍 Поиск...", "ja": "🔍 検索中..."}
    searching_msg = await update.message.reply_text(msgs.get(language, "🔍"))
    query = text.lower().strip()

    # 1. Shaxsiy SQLite bazasidan qidirish
    cursor.execute("SELECT file_id, name FROM movies WHERE name LIKE ? AND lang = ?", ('%' + query + '%', language))
    results = cursor.fetchall()
    if results:
        await searching_msg.delete()
        found = {"uz": "✅ O'zbekcha topildi!", "en": "✅ Found in local database!", "ru": "✅ Найдено в базе!", "ja": "✅ データベースで見つかりました！"}
        for file_id, name in results[:3]:
            await update.message.reply_video(video=file_id, caption=f"🎌 {name}\n{found.get(language, '✅')}")
        return

    # 2. 🇷🇺 RUS TILI -> JUT.SU PARSER
    if language == "ru":
        await searching_msg.edit_text("🚀 В базе нет. Ищу напрямую на Jut.su...")
        jutsu_video_url = await get_jutsu_anime_video(text)
        if jutsu_video_url:
            await searching_msg.delete()
            await update.message.reply_video(video=jutsu_video_url, caption=f"🎌 <b>{text.title()} (Серия 1)</b>\n🚀 Найдено на Jut.su! ✨", parse_mode="HTML")
            return

    # 3. 🇬🇧 INGLIZ TILI -> GOGOANIME PARSER
    elif language == "en":
        await searching_msg.edit_text("🚀 Not in DB. Searching directly on Gogoanime...")
        gogo_url = await get_gogo_anime_video(text)
        if gogo_url:
            await searching_msg.delete()
            await update.message.reply_text(text=f"🎌 <b>{text.title()} (Episode 1)</b>\n🚀 Found on Gogoanime! Click to stream:\n👉 {gogo_url}", parse_mode="HTML")
            return

    # 4. 🇯🇵 YAPON TILI -> ANIME-PLANET PARSER (YANGI SEKTOR!)
    elif language == "ja":
        await searching_msg.edit_text("🚀 データベースにありません。Anime-Planetで検索中...")
        ja_url = await get_japanese_anime_info(text)
        if ja_url:
            await searching_msg.delete()
            await update.message.reply_text(text=f"🎌 <b>{text.title()} (第1話)</b>\n🚀 Anime-Planet で公式ストリームが見つかりました:\n👉 {ja_url}", parse_mode="HTML")
            return

    # 5. AGAR HECH QAYERDA TOPILMASA -> ANILIST API
    animes = search_anime_anilist(text)
    if not animes:
        not_found = {"uz": "❌ Anime topilmadi.", "en": "❌ Not found anywhere.", "ru": "❌ Не найдено.", "ja": "❌ 見つかりませんでした。"}
        await searching_msg.edit_text(not_found.get(language, "❌"))
        return

    await searching_msg.delete()
    context.user_data["animes"] = animes
    context.user_data["anime_idx"] = 0
    context.user_data["lang"] = language

    no_video = {
        "uz": "📭 Video hali yuklanmagan. Anime ma'lumoti:",
        "en": "📭 No video stream found. Anime Info:",
        "ru": "📭 Видео не найдено. Информация из AniList:",
        "ja": "📭 動画がありません。AniListの情報:"
    }
    await update.message.reply_text(no_video.get(language, "📭"))

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
        msgs = {"uz": "🔍 Anime nomini yuboring:", "en": "🔍 Send anime name:", "ru": "🔍 Отправьте название:", "ja": "🔍 アニメの名前を送信してください:"}
        await query.message.reply_text(msgs.get(lang, "🔍"))
        return

    if data.startswith("nav_"):
        idx = int(data.split("_")[1])
        animes = context.user_data.get("animes", [])
        language = context.user_data.get("lang", "uz")
        if not animes: return
        context.user_data["anime_idx"] = idx
        anime = animes[idx]
        caption = format_anime(anime, language, idx, len(animes))
        image_url = anime.get("coverImage", {}).get("large")
        keyboard = nav_keyboard(idx, len(animes), language)
        try:
            if image_url:
                from telegram import InputMediaPhoto
                await query.edit_message_media(media=InputMediaPhoto(media=image_url, caption=caption, parse_mode="HTML"), reply_markup=keyboard)
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
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.VIDEO, auto_save_to_db))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Anime Bot ishlayapti...")
    app.run_polling()

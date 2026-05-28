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

# ===================== PARSERLAR (JUT.SU, GOGO, JAPANESE) =====================
async def get_jutsu_anime_video(anime_title_en: str):
    formatted_name = anime_title_en.lower().strip().replace(" ", "-")
    url = f"https://jut.su/{formatted_name}/episode-1.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                video_tag = soup.find("video")
                if video_tag and video_tag.find_all("source"):
                    return video_tag.find_all("source")[-1].get("src")
    except Exception as e: print(f"Jutsu xato: {e}")
    return None

async def get_gogo_anime_video(anime_title_en: str):
    formatted_name = anime_title_en.lower().strip().replace(" ", "-")
    url = f"https://gogoanime3.co/{formatted_name}-episode-1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                iframe = soup.find("iframe")
                if iframe: return "https:" + iframe.get("src") if not iframe.get("src").startswith("http") else iframe.get("src")
    except Exception as e: print(f"Gogo xato: {e}")
    return None

async def get_japanese_anime_info(anime_title_en: str):
    formatted_name = anime_title_en.lower().strip().replace(" ", "-")
    return f"https://embed.anime-planet.com/anime/{formatted_name}/episode/1"

# ===================== ANILIST API =====================
def search_anime_anilist(query: str) -> list:
    url = "https://graphql.anilist.co"
    graphql = '''
    query ($search: String) {
        Page(page: 1, perPage: 5) {
            media(search: $search, type: ANIME) {
                id
                title { romaji english native }
                episodes status averageScore
                startDate { year } genres description(asHtml: false)
                coverImage { large } siteUrl
            }
        }
    }
    '''
    try:
        resp = requests.post(url, json={"query": graphql, "variables": {"search": query}}, timeout=10)
        if resp.status_code == 200: return resp.json().get("data", {}).get("Page", {}).get("media", [])
    except Exception as e: print(f"AniList xato: {e}")
    return []

def format_anime(anime, lang, idx, total):
    title = anime.get("title", {})
    name = title.get("english") or title.get("romaji") or "—"
    name_jp = title.get("native") or ""
    score = f"{anime.get('averageScore')}/100" if anime.get('averageScore') else "—"
    episodes = anime.get("episodes") or "—"
    status = anime.get("status") or "—"
    year = anime.get("startDate", {}).get("year") or "—"
    genres = ", ".join(anime.get("genres", [])[:4]) or "—"
    desc = (anime.get("description") or "")[:250] + "..." if len(anime.get("description") or "") > 250 else (anime.get("description") or "")
    url = anime.get("siteUrl") or ""

    nav = {"uz": f"\n\n📄 Natija: {idx+1}/{total}", "en": f"\n\n📄 Result: {idx+1}/{total}", "ru": f"\n\n📄 Результат: {idx+1}/{total}", "ja": f"\n\n📄 結果: {idx+1}/{total}"}

    if lang == "uz":
        return f"🎌 <b>{name}</b>\n<i>{name_jp}</i>\n\n⭐ Reyting: <b>{score}</b>\n📺 Qismlar: <b>{episodes}</b>\n📌 Holat: {status}\n📅 Yil: {year}\n🏷 Janr: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["uz"]
    elif lang == "en":
        return f"🎌 <b>{name}</b>\n<i>{name_jp}</i>\n\n⭐ Score: <b>{score}</b>\n📺 Episodes: <b>{episodes}</b>\n📌 Status: {status}\n📅 Year: {year}\n🏷 Genres: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["en"]
    elif lang == "ja":
        return f"🎌 <b>{name}</b>\n<i>{name_jp}</i>\n\n⭐ スコア: <b>{score}</b>\n📺 エピソード: <b>{episodes}</b>\n📌 ステータス: {status}\n📅 年: {year}\n🏷 ジャンル: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["ja"]
    else:
        return f"🎌 <b>{name}</b>\n<i>{name_jp}</i>\n\n⭐ Рейтинг: <b>{score}</b>\n📺 Эпизоды: <b>{episodes}</b>\n📌 Статус: {status}\n📅 Год: {year}\n🏷 Жанры: {genres}\n\n📖 {desc}\n🔗 <a href='{url}'>AniList</a>" + nav["ru"]

def nav_keyboard(idx, total, lang):
    buttons = []
    row = []
    if idx > 0: row.append(InlineKeyboardButton("◀️", callback_data=f"nav_{idx-1}"))
    if idx < total - 1: row.append(InlineKeyboardButton("▶️", callback_data=f"nav_{idx+1}"))
    if row: buttons.append(row)
    new_search = {"uz": "🔍 Yangi qidiruv", "en": "🔍 New search", "ru": "🔍 Новый поиск", "ja": "🔍 新しい検索"}
    buttons.append([InlineKeyboardButton(new_search.get(lang, "🔍 Yangi qidiruv"), callback_data="new_search")])
    return InlineKeyboardMarkup(buttons)

# ===================== KANALDAN AVTOSAQLASH (QAYTIB KELDI! ⚡) =====================
async def auto_save_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or not post.video: return

    chat_id = post.chat.id
    video_id = post.video.file_id
    caption = (post.caption or post.text or "Nomsiz qism").split('\n')[0].strip()

    if chat_id == CHANNEL_UZ: lang = "uz"
    elif chat_id == CHANNEL_RU: lang = "ru"
    elif chat_id == CHANNEL_EN: lang = "en"
    else: return

    cursor.execute("SELECT id FROM movies WHERE file_id = ?", (video_id,))
    if cursor.fetchone(): return

    cursor.execute("INSERT INTO movies (name, file_id, lang) VALUES (?, ?, ?)", (caption.lower(), video_id, lang))
    conn.commit()

# ===================== START VA LANG DISPETCHERLARI =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
    await update.message.reply_text(
        "🎌 <b>Anime Bot ga xush kelibsiz! / Welcome!</b>\n\nTilni tanlang / Choose language 👇",
        parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
    await update.message.reply_text("🌐 Tilni tanlang / Choose language:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ===================== XABARLARNI QAYTA ISHLASH =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text in ["🇺🇿 Uzbek", "🇺🇸 English", "🇷🇺 Русский", "🇯🇵 Japanese"]:
        if text == "🇺🇿 Uzbek": users_language[user_id] = "uz"
        elif text == "🇺🇸 English": users_language[user_id] = "en"
        elif text == "🇯🇵 Japanese": users_language[user_id] = "ja"
        else: users_language[user_id] = "ru"
        
        msgs = {"uz": "✅ Til tanlandi! Anime nomini yuboring:", "en": "✅ Language selected! Send anime name:", "ru": "✅ Язык выбран! Отправьте название аниме:", "ja": "✅ 言語が選択されました！アニメの名前を送信してください:"}
        await update.message.reply_text(msgs[users_language[user_id]])
        return

    # 🚨 MAJBURIY TIL TEKSHIRUVI (4 TALA TUGMA HAM SHU YERDA):
    if user_id not in users_language:
        keyboard = [["🇺🇿 Uzbek", "🇷🇺 Русский"], ["🇺🇸 English", "🇯🇵 Japanese"]]
        await update.message.reply_text("🛑 Choose language / Выберите язык / 言語を選択してください 👇", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
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
        for file_id, name in results[:3]: await update.message.reply_video(video=file_id, caption=f"🎌 {name}")
        return

    # 2. GLOBAL TRANSLIT (ANILIST API)
    animes = search_anime_anilist(text)
    if not animes:
        not_found = {"uz": "❌ Anime topilmadi.", "en": "❌ Not found.", "ru": "❌ Аниме не найдено.", "ja": "❌ 見つかりませんでした。"}
        await searching_msg.edit_text(not_found.get(language, "❌"))
        return

    anime = animes[0]
    english_title = anime.get("title", {}).get("english") or anime.get("title", {}).get("romaji")

    # 3. SEKTORLAR BO'YICHA PARSERLARGA YUBORISH
    if language == "ru" and english_title:
        await searching_msg.edit_text("🚀 Ищу видео на Jut.su...")
        jutsu_video_url = await get_jutsu_anime_video(english_title)
        if jutsu_video_url:
            await searching_msg.delete()
            await update.message.reply_video(video=jutsu_video_url, caption=f"🎌 <b>{text.title()} (Серия 1)</b>\n🚀 Успешно найдено! ✨", parse_mode="HTML")
            return

    elif language == "en" and english_title:
        await searching_msg.edit_text("🚀 Searching video on Gogoanime...")
        gogo_url = await get_gogo_anime_video(english_title)
        if gogo_url:
            await searching_msg.delete()
            await update.message.reply_text(text=f"🎌 <b>{text.title()} (Episode 1)</b>\n🚀 Found! Stream link:\n👉 {gogo_url}", parse_mode="HTML")
            return

    elif language == "ja" and english_title:
        await searching_msg.edit_text("🚀 Anime-Planetで検索中...")
        ja_url = await get_japanese_anime_info(english_title)
        if ja_url:
            await searching_msg.delete()
            await update.message.reply_text(text=f"🎌 <b>{text.title()} (第1話)</b>\n🚀 Found Stream:\n👉 {ja_url}", parse_mode="HTML")
            return

    # 4. AGAR VIDEO SAYTLARDA topilmasa -> ANILIST MA'LUMOTI
    await searching_msg.delete()
    context.user_data["animes"] = animes
    context.user_data["anime_idx"] = 0
    context.user_data["lang"] = language

    no_video = {"uz": "📭 Video havola topilmadi. Anime ma'lumoti:", "en": "📭 No direct stream link found. Anime Info:", "ru": "📭 Прямое видео не найдено. Информация об аниме:", "ja": "📭 動画リンクがありません。アニメ情報:"}
    await update.message.reply_text(no_video.get(language, "📭"))

    caption = format_anime(anime, language, 0, len(animes))
    image_url = anime.get("coverImage", {}).get("large")
    keyboard = nav_keyboard(0, len(animes), language)

    try:
        if image_url: await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="HTML", reply_markup=keyboard)
        else: await update.message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)
    except Exception: await update.message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)

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
            try: await query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
            except Exception: pass

# ===================== MAIN =====================
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    # 🚨 KANALDAN KELGAN VIDEOLARNI AVTO-SAQLASH HANDLERI HAM JOYIGA QAYTDI! 👇
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.VIDEO, auto_save_to_db))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Anime Bot ishlayapti...")
    app.run_polling()

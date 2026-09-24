import asyncio
import logging
import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7095206192
CHANNEL_ID = -1004417956541
GROUP_ID = -1003993560990  
CHANNEL_LINK = "LoveUgoZapad"  # Для генерации ссылок на посты

# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ===
conn = sqlite3.connect('radar.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS radar 
                  (user_id INTEGER PRIMARY KEY, gender TEXT, hair TEXT, height TEXT, feature TEXT)''')
conn.commit()

# === СЛОВАРЬ ТРИГГЕРОВ (Корни слов для умного поиска) ===
TRIGGERS = {
    "gender": {
        "male": ["парен", "мальчик", "чел", "тип", "пацан", "молод", "мужч", "он"],
        "female": ["девуш", "девоч", "девчон", "тян", "дама", "блондинк", "брюнетк", "она"]
    },
    "hair": {
        "blonde": ["блонд", "светл", "бел", "желт"],
        "dark": ["брюнет", "темн", "черн", "кашт", "шатен"],
        "red": ["рыж", "красн", "огнен"],
        "light_brown": ["рус", "русы"],
        "colored": ["розов", "син", "зелен", "фиолетов", "цветн", "крашен", "пряд"]
    },
    "height": {
        "tall": ["высок", "длинн", "больш", "здоров"],
        "short": ["низк", "маленьк", "невысок", "миниатюрн", "полторашк"]
    },
    "feature": {
        "glasses": ["очк", "очка", "линз"],
        "tattoo": ["тату", "забит", "рукав", "партак", "наколк"],
        "piercing": ["пирсинг", "септум", "прокол", "кольц", "штанга", "губ"],
        "curly": ["кудр", "вьют", "волнист", "дред"],
        "kare": ["каре", "коротк"]
    }
}

# === МАШИНА СОСТОЯНИЙ (Анкета Радара) ===
class RadarForm(StatesGroup):
    gender = State()
    hair = State()
    height = State()
    feature = State()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === АЛГОРИТМ ПОИСКА И РАССЫЛКИ ===
async def notify_radar(text: str, post_id: int):
    if not text:
        return
    text_lower = text.lower()
    matched = {}
    
    # Ищем совпадения корней в тексте поста
    for category, values in TRIGGERS.items():
        for attr, roots in values.items():
            if any(root in text_lower for root in roots):
                matched[category] = attr
                break 

    # Рассылаем, только если совпало хотя бы 2 признака (чтобы избежать спама)
    if len(matched) >= 2:
        query = "SELECT user_id FROM radar WHERE "
        conditions = [f"{cat}='{val}'" for cat, val in matched.items()]
        query += " AND ".join(conditions)
        
        try:
            cursor.execute(query)
            users = cursor.fetchall()
            post_url = f"https://t.me/{CHANNEL_LINK}/{post_id}"
            
            for (uid,) in users:
                try:
                    msg = (
                        "👀 <b>РАДАР СРАБОТАЛ!</b>\n\n"
                        "Похоже, в новом посте ищут кого-то, кто очень подходит под твои приметы.\n\n"
                        f"👉 <a href='{post_url}'>Смотреть пост в канале</a>"
                    )
                    await bot.send_message(uid, msg, parse_mode="HTML")
                    await asyncio.sleep(0.1) # Защита от лимитов телеграма
                except Exception:
                    pass # Если юзер заблокировал бота, пропускаем
        except Exception as e:
            logging.error(f"DB Error: {e}")

# === КНОПКИ ===
def get_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}")
    builder.adjust(2)
    return builder.as_markup()

# === АДМИН ПАНЕЛЬ ===
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin_panel(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Фейкпуб", callback_data="admin_fake")
    builder.button(text="🔒 Закрыть чат", callback_data="admin_close")
    builder.button(text="🔓 Открыть чат", callback_data="admin_open")
    builder.adjust(1)
    await message.answer("🛠 <b>Панель управления каналом:</b>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_close", F.from_user.id == ADMIN_ID)
async def cb_admin_close(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=False))
        await callback.answer("🔒 Комментарии закрыты!", show_alert=True)
    except Exception as e:
        await callback.answer(f"Системная ошибка: {e}", show_alert=True)

@dp.callback_query(F.data == "admin_open", F.from_user.id == ADMIN_ID)
async def cb_admin_open(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True))
        await callback.answer("🔓 Комментарии открыты!", show_alert=True)
    except Exception as e:
        await callback.answer(f"Системная ошибка: {e}", show_alert=True)

# === РЕГИСТРАЦИЯ В РАДАРЕ ===
@dp.message(Command("radar"))
async def cmd_radar(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="👦 Парень", callback_data="rad_gender_male")
    builder.button(text="👧 Девушка", callback_data="rad_gender_female")
    builder.adjust(2)
    await message.answer("🎯 <b>Настройка радара</b>\n\nЯ буду присылать тебе уведомления, если в канале будут искать кого-то с твоими приметами.\n\nШаг 1. Укажи свой пол:", parse_mode="HTML", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.gender)

@dp.callback_query(RadarForm.gender, F.data.startswith("rad_gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[2]
    await state.update_data(gender=gender)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Блонд", callback_data="rad_hair_blonde")
    builder.button(text="Темные", callback_data="rad_hair_dark")
    builder.button(text="Русые", callback_data="rad_hair_light_brown")
    builder.button(text="Рыжие", callback_data="rad_hair_red")
    builder.button(text="Цветные", callback_data="rad_hair_colored")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 2. Какой у тебя цвет волос?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.hair)

@dp.callback_query(RadarForm.hair, F.data.startswith("rad_hair_"))
async def process_hair(callback: types.CallbackQuery, state: FSMContext):
    hair = callback.data.split("_")[2]
    await state.update_data(hair=hair)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Высокий", callback_data="rad_height_tall")
    builder.button(text="Средний", callback_data="rad_height_avg")
    builder.button(text="Невысокий", callback_data="rad_height_short")
    builder.adjust(1)
    await callback.message.edit_text("Шаг 3. Какой у тебя рост?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.height)

@dp.callback_query(RadarForm.height, F.data.startswith("rad_height_"))
async def process_height(callback: types.CallbackQuery, state: FSMContext):
    height = callback.data.split("_")[2]
    await state.update_data(height=height)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👓 Очки", callback_data="rad_feat_glasses")
    builder.button(text="🐉 Тату", callback_data="rad_feat_tattoo")
    builder.button(text="💍 Пирсинг", callback_data="rad_feat_piercing")
    builder.button(text="🌪 Кудряшки", callback_data="rad_feat_curly")
    builder.button(text="💇‍♀️ Каре", callback_data="rad_feat_kare")
    builder.button(text="❌ Нет особых примет", callback_data="rad_feat_none")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 4. Выбери самую яркую примету:", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.feature)

@dp.callback_query(RadarForm.feature, F.data.startswith("rad_feat_"))
async def process_feature(callback: types.CallbackQuery, state: FSMContext):
    feature = callback.data.split("_")[2]
    data = await state.get_data()
    user_id = callback.from_user.id
    
    # Сохраняем в базу данных
    cursor.execute("REPLACE INTO radar (user_id, gender, hair, height, feature) VALUES (?, ?, ?, ?, ?)",
                   (user_id, data['gender'], data['hair'], data['height'], feature))
    conn.commit()
    
    await callback.message.edit_text("✅ <b>Твой профиль сохранен!</b>\n\nТеперь, если в канале опубликуют пост с поиском человека твоей внешности, бот моментально пришлет тебе ссылку в личные сообщения.", parse_mode="HTML")
    await state.clear()

# === СТАРТ И ПРЕДЛОЖКА ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎙 <b>Привет! Это предложка канала Признания Юго-Западная.</b>\n\n"
        "Скидывай сюда:\n"
        "• Текст или фото с историей\n"
        "• 🎙 Голосовое сообщение\n"
        "• 📹 Видеокружок\n"
        "• Валентинку через команду /love [текст]\n\n"
        "🎯 <b>Новинка!</b> Жми /radar, чтобы настроить уведомления, если будут искать тебя!",
        parse_mode="HTML"
    )

@dp.message(Command("love"))
async def send_valentine(message: types.Message):
    user_text = message.text or message.caption or ""
    clean_text = user_text.replace("/love", "").strip()
    if not clean_text and not message.photo:
        await message.answer("Напиши текст валентинки после команды.")
        return
    valentine_text = f"💌 <b>АНОНИМНАЯ ВАЛЕНТИНКА</b> 💌\n\n<i>{clean_text}</i>\n\n<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>"
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=valentine_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=valentine_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Твоя валентинка улетела на модерацию! ❤️")
    except Exception:
        pass

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    if message.voice.duration > 90:
        await message.answer("⚠️ Запиши историю короче (до 1.5 минут).")
        return
    voice_caption = "🎙 <b>АНОНИМНОЕ ГОЛОСОВОЕ</b> 🎙\n\n<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>"
    await bot.send_voice(chat_id=ADMIN_ID, voice=message.voice.file_id, caption=voice_caption, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
    await message.answer("🎙 Твое голосовое отправлено на модерацию!")

@dp.message(F.video_note)
async def handle_video_note(message: types.Message):
    await bot.send_video_note(chat_id=ADMIN_ID, video_note=message.video_note.file_id, reply_markup=get_admin_kb(message.chat.id))
    await bot.send_message(chat_id=ADMIN_ID, text="<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>", parse_mode="HTML")
    await message.answer("📹 Твой кружок отправлен на модерацию!")

@dp.message(F.content_type.in_({'text', 'photo'}))
async def handle_suggestion(message: types.Message):
    # Игнорируем сообщения, если юзер находится в процессе регистрации радара
    if message.text and message.text.startswith('/'):
        return
        
    signature = "\n\n<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>"
    user_text = message.html_text or ""
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=user_text + signature, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=user_text + signature, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Твое сообщение улетело на модерацию!")
    except Exception:
        pass

# === ПУБЛИКАЦИЯ И АКТИВАЦИЯ РАДАРА ===
@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, user_id = callback.data.split("_")
    try:
        # Публикуем пост
        published_msg = await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=callback.message.message_id, reply_markup=None)
        
        # Меняем кнопку админу
        kb = InlineKeyboardBuilder()
        kb.button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await bot.send_message(chat_id=int(user_id), text="Твой пост опубликован в канале!")
        
        # Запускаем радар (сканируем текст)
        post_text = callback.message.text or callback.message.caption or ""
        asyncio.create_task(notify_radar(post_text, published_msg.message_id))
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Отклонено ❌", callback_data="done")
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
    await callback.answer("Сообщение отклонено.")

@dp.callback_query(F.data == "done")
async def cb_done(callback: types.CallbackQuery):
    await callback.answer()

# === БАЗА ФЕЙКОВЫХ ПОСТОВ ===
FAKE_POSTS = [
    "ищу парня который сегодня в столовой на 3 этаже уронил вилку и смешно выругался. ты был в сером свитшоте найдись",
    "девочка с каре и красными прядями стояла возле автоматов с кофе на первом этаже около 14:00. ты очень красивая дай инст",
    "сегодня утром на выходе из метро кто-то из наших помогал бабушке поднять сумку. высокий с темными волосами. респект тебе",
    # ... сюда добавь свои 100 постов ...
]

@dp.callback_query(F.data == "admin_fake", F.from_user.id == ADMIN_ID)
async def cb_admin_fake(callback: types.CallbackQuery):
    if not FAKE_POSTS:
        await callback.answer("❌ База фейков полностью исчерпана!", show_alert=True)
        return
        
    fake_text = random.choice(FAKE_POSTS)
    FAKE_POSTS.remove(fake_text)
    signature = "\n\n<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>"
    
    try:
        msg = await bot.send_message(chat_id=CHANNEL_ID, text=fake_text + signature, parse_mode="HTML")
        await callback.answer(f"✅ Опубликовано! Осталось: {len(FAKE_POSTS)}", show_alert=True)
        
        # Запускаем радар и для фейковых постов!
        asyncio.create_task(notify_radar(fake_text, msg.message_id))
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import os
import random
import shutil
import sqlite3
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, ChatPermissions, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID = 7095206192
CHANNEL_ID = -1004417956541
GROUP_ID = -1003993560990  
CHANNEL_LINK = "LoveUgoZapad"

# === ИНИЦИАЛИЗАЦИЯ И СПАСЕНИЕ БАЗЫ ДАННЫХ ===
DATA_DIR = "/app/data"
DB_PATH = f"{DATA_DIR}/radar.db"

if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        DB_PATH = "radar.db" 

if os.path.exists("radar.db") and DB_PATH != "radar.db" and not os.path.exists(DB_PATH):
    try:
        shutil.copy2("radar.db", DB_PATH)
        logging.info("База успешно скопирована в защищенную папку!")
    except Exception as e:
        logging.error(f"Ошибка копирования базы: {e}")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS radar 
                  (user_id INTEGER PRIMARY KEY, gender TEXT, hair TEXT, height TEXT, feature TEXT)''')
try:
    cursor.execute("ALTER TABLE radar ADD COLUMN university TEXT")
except sqlite3.OperationalError:
    pass
try:
    cursor.execute("ALTER TABLE radar ADD COLUMN course TEXT")
except sqlite3.OperationalError:
    pass
conn.commit()

# === СЛОВАРИ ===
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
    },
    "university": {
        "ranepa": ["ранхигс", "академ"],
        "mirea": ["мирэа"],
        "mpgu": ["мпгу", "пед"],
        "mgimo": ["мгимо"]
    },
    "course": {
        "c1": ["1 курс", "перваш", "первокурс", "первый"],
        "c2": ["2 курс", "второкурс", "второй"],
        "c3": ["3 курс", "третьекурс", "третий"],
        "c4": ["4 курс", "четверокурс", "четвертый", "выпускн"]
    }
}

TRANSLATE = {
    "male": "Парень", "female": "Девушка",
    "blonde": "Блонд", "dark": "Темные", "light_brown": "Русые", "red": "Рыжие", "colored": "Цветные",
    "tall": "Высокий", "avg": "Средний", "short": "Невысокий",
    "glasses": "Очки", "tattoo": "Тату", "piercing": "Пирсинг", "curly": "Кудряшки", "kare": "Каре", "none": "Нет особых примет",
    "ranepa": "РАНХиГС", "mirea": "МИРЭА", "mpgu": "МПГУ", "mgimo": "МГИМО",
    "c1": "1 курс", "c2": "2 курс", "c3": "3 курс", "c4": "4 курс"
}

class RadarForm(StatesGroup):
    gender = State()
    hair = State()
    height = State()
    feature = State()
    university = State()
    course = State()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === СИСТЕМА ОБЯЗАТЕЛЬНОЙ ПОДПИСКИ (MIDDLEWARE) ===
class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        
        # 1. Админа пускаем всегда без проверок
        if user_id == ADMIN_ID:
            return await handler(event, data)
            
        # 2. Проверяем только в личке (чтобы бот не спамил в группе с комментариями)
        chat_type = None
        if isinstance(event, types.Message):
            chat_type = event.chat.type
        elif isinstance(event, types.CallbackQuery):
            if event.message:
                chat_type = event.message.chat.type
        
        if chat_type != "private":
            return await handler(event, data)

        # 3. Кнопку "Я подписался" пропускаем, чтобы она могла отработать
        if isinstance(event, types.CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)
        
        # 4. Сама проверка подписки
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ['left', 'kicked']:
                raise Exception("Not subscribed")
        except Exception:
            # Если не подписан — выдаем заглушку
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_LINK}")],
                [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
            ])
            text = "❗️ <b>Обязательное условие</b>\n\nЧтобы пользоваться ботом, настраивать радар и отправлять признания, тебе нужно быть подписанным на наш основной канал!"
            
            if isinstance(event, types.Message):
                await event.answer(text, parse_mode="HTML", reply_markup=markup)
            elif isinstance(event, types.CallbackQuery):
                await event.message.answer(text, parse_mode="HTML", reply_markup=markup)
                await event.answer()
            return # Блокируем дальнейшее выполнение команды
        
        return await handler(event, data)

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Настроить радар"), KeyboardButton(text="💌 Валентинка")]
        ],
        resize_keyboard=True
    )

async def notify_radar(text: str, post_id: int):
    if not text:
        return
    text_lower = text.lower()
    matched = {}
    for category, values in TRIGGERS.items():
        for attr, roots in values.items():
            if any(root in text_lower for root in roots):
                matched[category] = attr
                break 

    if len(matched) >= 2:
        query = "SELECT user_id FROM radar WHERE "
        conditions = [f"{cat}='{val}'" for cat, val in matched.items()]
        query += " AND ".join(conditions)
        try:
            cursor.execute(query)
            users = cursor.fetchall()
            post_url = f"https://t.me/{CHANNEL_LINK}/{post_id}"
            notified_count = 0
            for (uid,) in users:
                try:
                    msg = (
                        "👀 <b>РАДАР СРАБОТАЛ!</b>\n\n"
                        "Похоже, в новом посте ищут кого-то, кто очень подходит под твои приметы.\n\n"
                        f"👉 <a href='{post_url}'>Смотреть пост в канале</a>"
                    )
                    await bot.send_message(uid, msg, parse_mode="HTML")
                    notified_count += 1
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
            if notified_count > 0:
                matched_str = ", ".join([f"{TRANSLATE.get(v, v)}" for k, v in matched.items()])
                admin_report = (
                    "📊 <b>Отчет Радара</b>\n\n"
                    f"Пост ID {post_id} активировал радар!\n"
                    f"🎯 Совпавшие критерии: <code>{matched_str}</code>\n"
                    f"👥 Уведомления отправлены: <b>{notified_count} чел.</b>"
                )
                await bot.send_message(ADMIN_ID, admin_report, parse_mode="HTML")
        except Exception as e:
            logging.error(f"DB Error: {e}")

def get_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}")
    builder.adjust(2)
    return builder.as_markup()

# === ОБРАБОТЧИК КНОПКИ "Я ПОДПИСАЛСЯ" ===
@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: types.CallbackQuery):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
        if member.status not in ['left', 'kicked']:
            await callback.message.delete()
            await callback.message.answer("✅ <b>Подписка подтверждена!</b>\n\nТеперь тебе доступны все функции. Жми /start для вызова меню.", parse_mode="HTML")
        else:
            await callback.answer("❌ Ты еще не подписался! Нажми кнопку 'Подписаться', а затем возвращайся сюда.", show_alert=True)
    except Exception:
        await callback.answer("❌ Ошибка проверки. Убедись, что канал существует.", show_alert=True)

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_admin_panel(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Фейкпуб", callback_data="admin_fake")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🔒 Закрыть чат", callback_data="admin_close")
    builder.button(text="🔓 Открыть чат", callback_data="admin_open")
    builder.adjust(2, 1, 2)
    await message.answer(
        "🛠 <b>Панель управления каналом:</b>\n\n"
        "<i>Скрытые команды:</i>\n"
        "<code>/get_db</code> - скачать базу файлом\n"
        "<code>/whois ID</code> - пробить профиль (например: /whois 123456)", 
        parse_mode="HTML", 
        reply_markup=builder.as_markup()
    )

@dp.message(Command("get_db"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_get_db(message: types.Message):
    try:
        db_file = FSInputFile(DB_PATH)
        await message.answer_document(db_file, caption="📁 Твоя защищенная база данных радара")
    except Exception as e:
        await message.answer(f"Ошибка выгрузки: {e}")

@dp.message(Command("whois"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_whois(message: types.Message):
    try:
        target_id = int(message.text.split()[1])
        user_info = await bot.get_chat(target_id)
        username = f"@{user_info.username}" if user_info.username else "Отсутствует"
        name = user_info.first_name or "Без имени"
        await message.answer(
            f"👤 <b>Имя:</b> <a href='tg://user?id={target_id}'>{name}</a>\n"
            f"🔗 <b>Юзернейм:</b> {username}\n"
            f"🆔 <b>ID:</b> <code>{target_id}</code>", 
            parse_mode="HTML"
        )
    except IndexError:
        await message.answer("❌ Напиши команду и ID через пробел. Пример: <code>/whois 123456789</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка (возможно, бот не видел этого пользователя): {e}")

@dp.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def cb_admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT gender, hair, height, feature, university, course FROM radar ORDER BY user_id DESC LIMIT 30")
    users = cursor.fetchall()
    if not users:
        await callback.answer("В базе пока нет анкет.", show_alert=True)
        return
    text = "📊 <b>Последние анкеты для вдохновения:</b>\n\n"
    for i, u in enumerate(users, 1):
        profile = [TRANSLATE.get(item, str(item)) for item in u if item]
        text += f"👤 <b>Пользователь {i}:</b> {', '.join(profile)}\n\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
async def cb_admin_broadcast(callback: types.CallbackQuery):
    await callback.answer("Рассылка запущена...", show_alert=False)
    cursor.execute("SELECT user_id FROM radar")
    users = cursor.fetchall()
    success_count = 0
    for (uid,) in users:
        try:
            msg = (
                "🤖 <b>Бот обновился!</b>\n\n"
                "Мы добавили новые функции. Пожалуйста, заполни анкету радара заново, чтобы не пропустить, когда тебя будут искать!\n\n"
                "Жми 👉 /radar"
            )
            await bot.send_message(uid, msg, parse_mode="HTML")
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass
    await bot.send_message(ADMIN_ID, f"📢 <b>Рассылка завершена!</b>\nУспешно доставлено: <b>{success_count}</b> пользователям.", parse_mode="HTML")

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

@dp.message(F.text == "🎯 Настроить радар", F.chat.type == "private")
@dp.message(Command("radar"), F.chat.type == "private")
async def start_radar(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="👦 Парень", callback_data="rad_gender_male")
    builder.button(text="👧 Девушка", callback_data="rad_gender_female")
    builder.adjust(2)
    await message.answer("🎯 <b>Настройка радара</b>\n\nШаг 1. Укажи свой пол:", parse_mode="HTML", reply_markup=builder.as_markup())
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
    builder.button(text="❌ Нет примет", callback_data="rad_feat_none")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 4. Выбери самую яркую примету:", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.feature)

@dp.callback_query(RadarForm.feature, F.data.startswith("rad_feat_"))
async def process_feature(callback: types.CallbackQuery, state: FSMContext):
    feature = callback.data.split("_")[2]
    await state.update_data(feature=feature)
    builder = InlineKeyboardBuilder()
    builder.button(text="РАНХиГС", callback_data="rad_uni_ranepa")
    builder.button(text="МИРЭА", callback_data="rad_uni_mirea")
    builder.button(text="МПГУ", callback_data="rad_uni_mpgu")
    builder.button(text="МГИМО", callback_data="rad_uni_mgimo")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 5. В каком ВУЗе ты учишься?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.university)

@dp.callback_query(RadarForm.university, F.data.startswith("rad_uni_"))
async def process_uni(callback: types.CallbackQuery, state: FSMContext):
    university = callback.data.split("_")[2]
    await state.update_data(university=university)
    builder = InlineKeyboardBuilder()
    builder.button(text="1 курс", callback_data="rad_course_c1")
    builder.button(text="2 курс", callback_data="rad_course_c2")
    builder.button(text="3 курс", callback_data="rad_course_c3")
    builder.button(text="4 курс", callback_data="rad_course_c4")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 6. На каком ты курсе?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.course)

@dp.callback_query(RadarForm.course, F.data.startswith("rad_course_"))
async def process_course(callback: types.CallbackQuery, state: FSMContext):
    course = callback.data.split("_")[2]
    data = await state.get_data()
    user_id = callback.from_user.id
    cursor.execute("REPLACE INTO radar (user_id, gender, hair, height, feature, university, course) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_id, data['gender'], data['hair'], data['height'], data['feature'], data['university'], course))
    conn.commit()
    await callback.message.edit_text("✅ <b>Твой профиль сохранен!</b>\n\nТеперь, если в канале опубликуют пост с поиском человека твоей внешности или из твоего ВУЗа, бот моментально пришлет тебе ссылку в личные сообщения.", parse_mode="HTML")
    await state.clear()

@dp.message(F.text == "💌 Валентинка", F.chat.type == "private")
async def info_valentine(message: types.Message):
    await message.answer(
        "💌 <b>Как отправить валентинку?</b>\n\n"
        "Напиши в чат команду <code>/love</code> и текст своего признания.\n\n"
        "<i>Пример:</i>\n<code>/love Девочка в белом пуховике у 2 корпуса, ты супер!</code>",
        parse_mode="HTML"
    )

@dp.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: types.Message):
    await message.answer(
        "🎙 <b>Привет! Это предложка канала Признания Юго-Западная.</b>\n\n"
        "Скидывай сюда текст, фото, голосовые или видеокружки — всё опубликуем анонимно после модерации.\n\n"
        "👇 <b>Используй кнопки меню внизу, чтобы настроить радар примет!</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.message(Command("love"), F.chat.type == "private")
async def send_valentine(message: types.Message):
    user_text = message.text or message.caption or ""
    clean_text = user_text.replace("/love", "").strip()
    if not clean_text and not message.photo:
        await message.answer("Напиши текст валентинки после команды.\nПример: /love Привет!")
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

@dp.message(F.voice, F.chat.type == "private")
async def handle_voice(message: types.Message):
    if message.voice.duration > 90:
        await message.answer("⚠️ Запиши историю короче (до 1.5 минут).")
        return
    voice_caption = "🎙 <b>АНОНИМНОЕ ГОЛОСОВОЕ</b> 🎙\n\n<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>"
    await bot.send_voice(chat_id=ADMIN_ID, voice=message.voice.file_id, caption=voice_caption, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
    await message.answer("🎙 Твое голосовое отправлено на модерацию!")

@dp.message(F.video_note, F.chat.type == "private")
async def handle_video_note(message: types.Message):
    await bot.send_video_note(chat_id=ADMIN_ID, video_note=message.video_note.file_id, reply_markup=get_admin_kb(message.chat.id))
    await bot.send_message(chat_id=ADMIN_ID, text="<a href='https://t.me/LoveUgoZapad'>Признания Юго-Западная</a>", parse_mode="HTML")
    await message.answer("📹 Твой кружок отправлен на модерацию!")

@dp.message(F.content_type.in_({'text', 'photo'}), F.chat.type == "private")
async def handle_suggestion(message: types.Message):
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

@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, user_id = callback.data.split("_")
    try:
        published_msg = await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=callback.message.message_id, reply_markup=None)
        kb = InlineKeyboardBuilder()
        kb.button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await bot.send_message(chat_id=int(user_id), text="Твой пост опубликован в канале!")
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

FAKE_POSTS = [
    "ищу парня который сегодня в столовой на 3 этаже уронил вилку и смешно выругался. ты был в сером свитшоте найдись",
    "девочка с каре и красными прядями стояла возле автоматов с кофе на первом этаже около 14:00. ты очень красивая дай инст",
    "сегодня утром на выходе из метро кто-то из наших помогал бабушке поднять сумку. высокий с темными волосами. респект тебе",
    "понравилась девушка на лекции по праву у перваков (сидела на 3 ряду). ты всё время рисовала в тетрадке отзовись пж",
    "парень с проколотой губой и кольцами на пальцах, курил у 6 корпуса где-то в час дня. найдись",
    "парень сидел сегодня в зоне отдыха в наушниках маршал и черной кожанке. отпиши в коменты",
    "21.09. девчонка в широких джинсах и огромном зеленом худи, мы столкнулись в дверях 2 корпуса. сорри еще раз",
    "парень из 3 группы фнн, который сегодня отвечал у доски, у тебя очень красивый голос"
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
        asyncio.create_task(notify_radar(fake_text, msg.message_id))
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

async def main():
    # Регистрируем наш фильтр подписки (Middleware)
    dp.message.middleware(CheckSubscriptionMiddleware())
    dp.callback_query.middleware(CheckSubscriptionMiddleware())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

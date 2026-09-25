import asyncio
import logging
import os
import random
import shutil
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, KICKED, LEFT
from aiogram.types import InlineKeyboardMarkup, ChatPermissions, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardButton, ChatMemberUpdated
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

# Таблица радара
cursor.execute('''CREATE TABLE IF NOT EXISTS radar 
                  (user_id INTEGER PRIMARY KEY, gender TEXT, hair TEXT, height TEXT, feature TEXT, university TEXT, course TEXT, inviter_id INTEGER)''')
try: cursor.execute("ALTER TABLE radar ADD COLUMN university TEXT")
except: pass
try: cursor.execute("ALTER TABLE radar ADD COLUMN course TEXT")
except: pass
try: cursor.execute("ALTER TABLE radar ADD COLUMN inviter_id INTEGER DEFAULT NULL")
except: pass

# Таблица розыгрышей
cursor.execute('''CREATE TABLE IF NOT EXISTS giveaways 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, photo_id TEXT, end_time TEXT, message_id INTEGER, is_active INTEGER DEFAULT 1)''')
conn.commit()

# === СЛОВАРИ ===
TRIGGERS = {
    "gender": {"male": ["парен", "мальчик", "чел", "тип", "пацан", "молод", "мужч", "он"], "female": ["девуш", "девоч", "девчон", "тян", "дама", "блондинк", "брюнетк", "она"]},
    "hair": {"blonde": ["блонд", "светл", "бел", "желт"], "dark": ["брюнет", "темн", "черн", "кашт", "шатен"], "red": ["рыж", "красн", "огнен"], "light_brown": ["рус", "русы"], "colored": ["розов", "син", "зелен", "фиолетов", "цветн", "крашен", "пряд"]},
    "height": {"tall": ["высок", "длинн", "больш", "здоров"], "short": ["низк", "маленьк", "невысок", "миниатюрн", "полторашк"]},
    "feature": {"glasses": ["очк", "очка", "линз"], "tattoo": ["тату", "забит", "рукав", "партак", "наколк"], "piercing": ["пирсинг", "септум", "прокол", "кольц", "штанга", "губ"], "curly": ["кудр", "вьют", "волнист", "дред"], "kare": ["каре", "коротк"]},
    "university": {"ranepa": ["ранхигс", "академ"], "mirea": ["мирэа"], "mpgu": ["мпгу", "пед"], "mgimo": ["мгимо"]},
    "course": {"c1": ["1 курс", "перваш", "первокурс", "первый"], "c2": ["2 курс", "второкурс", "второй"], "c3": ["3 курс", "третьекурс", "третий"], "c4": ["4 курс", "четверокурс", "четвертый", "выпускн"]}
}

TRANSLATE = {
    "male": "Парень", "female": "Девушка", "blonde": "Блонд", "dark": "Темные", "light_brown": "Русые", "red": "Рыжие", "colored": "Цветные",
    "tall": "Высокий", "avg": "Средний", "short": "Невысокий", "glasses": "Очки", "tattoo": "Тату", "piercing": "Пирсинг", "curly": "Кудряшки", "kare": "Каре", "none": "Нет особых примет",
    "ranepa": "РАНХиГС", "mirea": "МИРЭА", "mpgu": "МПГУ", "mgimo": "МГИМО", "c1": "1 курс", "c2": "2 курс", "c3": "3 курс", "c4": "4 курс"
}

class RadarForm(StatesGroup):
    gender, hair, height, feature, university, course, inviter_id = State(), State(), State(), State(), State(), State(), State()

class GiveawayCreate(StatesGroup):
    photo, title, description, end_time = State(), State(), State(), State()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === СИСТЕМА ОБЯЗАТЕЛЬНОЙ ПОДПИСКИ (MIDDLEWARE) ===
class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        if user_id == ADMIN_ID:
            return await handler(event, data)
            
        chat_type = None
        if isinstance(event, types.Message): chat_type = event.chat.type
        elif isinstance(event, types.CallbackQuery) and event.message: chat_type = event.message.chat.type
        
        if chat_type != "private": return await handler(event, data)
        if isinstance(event, types.CallbackQuery) and event.data == "check_sub": return await handler(event, data)
        
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ['left', 'kicked']: raise Exception()
        except Exception:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_LINK}")],
                [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
            ])
            text = "❗️ <b>Обязательное условие</b>\n\nЧтобы пользоваться ботом, тебе нужно быть подписанным на наш основной канал!"
            if isinstance(event, types.Message): await event.answer(text, parse_mode="HTML", reply_markup=markup)
            elif isinstance(event, types.CallbackQuery): 
                await event.message.answer(text, parse_mode="HTML", reply_markup=markup)
                await event.answer()
            return 
        return await handler(event, data)

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎯 Настроить радар"), KeyboardButton(text="💌 Валентинка")], [KeyboardButton(text="🎁 Розыгрыш")]],
        resize_keyboard=True
    )

# === ОТПИСКА РЕФЕРАЛОВ ===
@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED | LEFT))
async def on_user_leave(event: ChatMemberUpdated):
    if event.chat.id == CHANNEL_ID:
        cursor.execute("SELECT inviter_id FROM radar WHERE user_id = ?", (event.from_user.id,))
        row = cursor.fetchone()
        if row and row[0]:
            cursor.execute("UPDATE radar SET inviter_id = NULL WHERE user_id = ?", (event.from_user.id,))
            conn.commit()
            try: await bot.send_message(row[0], "📉 <b>Один из твоих рефералов отписался!</b>\n\nШанс в розыгрыше сгорел.", parse_mode="HTML")
            except: pass

async def notify_radar(text: str, post_id: int):
    if not text: return
    text_lower = text.lower()
    matched = {}
    for cat, values in TRIGGERS.items():
        for attr, roots in values.items():
            if any(r in text_lower for r in roots):
                matched[cat] = attr
                break 

    if len(matched) >= 2:
        query = "SELECT user_id FROM radar WHERE " + " AND ".join([f"{cat}='{val}'" for cat, val in matched.items()])
        try:
            cursor.execute(query)
            users, notified = cursor.fetchall(), 0
            for (uid,) in users:
                try:
                    await bot.send_message(uid, f"👀 <b>РАДАР СРАБОТАЛ!</b>\n\nПохоже, ищут тебя.\n👉 <a href='https://t.me/{CHANNEL_LINK}/{post_id}'>Смотреть пост</a>", parse_mode="HTML")
                    notified += 1
                    await asyncio.sleep(0.1)
                except: pass
            if notified > 0:
                admin_report = f"📊 <b>Отчет Радара (Пост {post_id})</b>\nКритерии: {', '.join([TRANSLATE.get(v, v) for v in matched.values()])}\nУведомлено: <b>{notified} чел.</b>"
                await bot.send_message(ADMIN_ID, admin_report, parse_mode="HTML")
        except: pass

def get_admin_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data=f"pub_{user_id}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{user_id}")
    return builder.as_markup()

@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: types.CallbackQuery):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
        if member.status not in ['left', 'kicked']:
            await callback.message.delete()
            await callback.message.answer("✅ <b>Подписка подтверждена!</b>", parse_mode="HTML")
        else: await callback.answer("❌ Ты еще не подписался!", show_alert=True)
    except: await callback.answer("❌ Ошибка проверки.", show_alert=True)

# === МЕНЮ РОЗЫГРЫША ДЛЯ ЮЗЕРОВ ===
@dp.message(F.text == "🎁 Розыгрыш", F.chat.type == "private")
async def show_giveaway(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM radar WHERE inviter_id = ?", (message.from_user.id,))
    ref_count = cursor.fetchone()[0]
    bot_info = await bot.get_me()
    
    text = (
        "🎁 <b>Участвуй в розыгрыше!</b>\n\n"
        "<b>1 приглашенный друг = +1 билет в барабане.</b>\n"
        "<i>Друг должен перейти по ссылке, подписаться и настроить радар.</i>\n\n"
        f"👥 Твои активные рефералы (шансы): <b>{ref_count}</b>\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n<code>https://t.me/{bot_info.username}?start={message.from_user.id}</code>"
    )
    await message.answer(text, parse_mode="HTML")

# === СОЗДАНИЕ РОЗЫГРЫША АДМИНОМ ===
@dp.callback_query(F.data == "admin_giveaway_create", F.from_user.id == ADMIN_ID)
async def admin_ga_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправь **КАРТИНКУ** для поста розыгрыша:", parse_mode="Markdown")
    await state.set_state(GiveawayCreate.photo)

@dp.message(GiveawayCreate.photo, F.photo)
async def admin_ga_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("Теперь отправь **НАЗВАНИЕ** розыгрыша (например: Розыгрыш 3-х Premium):", parse_mode="Markdown")
    await state.set_state(GiveawayCreate.title)

@dp.message(GiveawayCreate.title)
async def admin_ga_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Отправь **УСЛОВИЯ** и текст розыгрыша:", parse_mode="Markdown")
    await state.set_state(GiveawayCreate.description)

@dp.message(GiveawayCreate.description)
async def admin_ga_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.html_text)
    await message.answer("Напиши дату и время завершения в формате **ДД.ММ.ГГГГ ЧЧ:ММ**\n*(Например: 31.10.2026 18:00)*", parse_mode="Markdown")
    await state.set_state(GiveawayCreate.end_time)

@dp.message(GiveawayCreate.end_time)
async def admin_ga_end(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        db_time = dt.strftime("%Y-%m-%d %H:%M") # SQLite формат
        
        data = await state.get_data()
        bot_info = await bot.get_me()
        
        ga_text = (
            f"🎉 <b>{data['title']}</b>\n\n"
            f"{data['description']}\n\n"
            f"⏳ <b>Итоги:</b> {message.text.strip()}\n"
            f"👇 Жми кнопку ниже, бери свою ссылку и приглашай друзей! Больше друзей = больше шансов!"
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Участвовать в розыгрыше 🎁", url=f"https://t.me/{bot_info.username}")
        ]])
        
        msg = await bot.send_photo(chat_id=CHANNEL_ID, photo=data['photo_id'], caption=ga_text, parse_mode="HTML", reply_markup=markup)
        
        cursor.execute("INSERT INTO giveaways (title, description, photo_id, end_time, message_id) VALUES (?, ?, ?, ?, ?)",
                       (data['title'], data['description'], data['photo_id'], db_time, msg.message_id))
        conn.commit()
        
        await message.answer(f"✅ Розыгрыш успешно запущен и опубликован в канал! Бот автоматически подведет итоги {message.text}.")
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат! Напиши строго так: <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>", parse_mode="HTML")

# === ФОНОВЫЙ ТРЕКИНГ И АВТОМАТИЧЕСКИЕ ИТОГИ ===
async def giveaway_scheduler():
    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("SELECT id, title, message_id FROM giveaways WHERE is_active = 1 AND end_time <= ?", (now_str,))
        ended = cursor.fetchall()
        
        for gid, title, msg_id in ended:
            # Ищем победителя
            cursor.execute("SELECT inviter_id, COUNT(user_id) FROM radar WHERE inviter_id IS NOT NULL GROUP BY inviter_id")
            rows = cursor.fetchall()
            
            if not rows:
                result_text = f"🏆 <b>Итоги розыгрыша «{title}»</b>\n\nК сожалению, победитель не найден (нет участников с рефералами)."
            else:
                pool = []
                for inviter, count in rows:
                    pool.extend([inviter] * count)
                winner_id = random.choice(pool)
                chances = pool.count(winner_id)
                
                try:
                    user_info = await bot.get_chat(winner_id)
                    username = f"@{user_info.username}" if user_info.username else "Профиль скрыт"
                    name = user_info.first_name or "Без имени"
                    result_text = (
                        f"🏆 <b>Итоги розыгрыша «{title}» подведены!</b>\n\n"
                        f"🎉 <b>Победитель:</b> <a href='tg://user?id={winner_id}'>{name}</a> ({username})\n"
                        f"🎟 <b>Рефералов (шансов):</b> {chances}\n\n"
                        f"Поздравляем! Администрация свяжется с победителем."
                    )
                except Exception:
                    result_text = f"🏆 <b>Итоги розыгрыша «{title}»</b>\n\n🎉 <b>Победитель:</b> ID <code>{winner_id}</code> (Шансов: {chances})"
            
            # Публикуем результат в канал реплаем к основному посту
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=result_text, reply_to_message_id=msg_id, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Не удалось опубликовать итоги: {e}")
            
            # Деактивируем завершенный розыгрыш
            cursor.execute("UPDATE giveaways SET is_active = 0 WHERE id = ?", (gid,))
            conn.commit()
            
        await asyncio.sleep(60) # Проверяем базу каждую минуту

# === АДМИН ПАНЕЛЬ И БАЗОВЫЕ КОМАНДЫ ===
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_admin_panel(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Создать розыгрыш", callback_data="admin_giveaway_create")
    builder.button(text="🎲 Фейкпуб", callback_data="admin_fake")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🔒 Закрыть чат", callback_data="admin_close")
    builder.button(text="🔓 Открыть чат", callback_data="admin_open")
    builder.adjust(1, 2, 1, 2)
    await message.answer("🛠 <b>Панель управления:</b>\n<i>Скрытые: /get_db, /whois ID</i>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.message(Command("get_db"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_get_db(message: types.Message):
    try: await message.answer_document(FSInputFile(DB_PATH))
    except Exception as e: await message.answer(f"Ошибка: {e}")

@dp.message(Command("whois"), F.from_user.id == ADMIN_ID, F.chat.type == "private")
async def cmd_whois(message: types.Message):
    try:
        tid = int(message.text.split()[1])
        u = await bot.get_chat(tid)
        await message.answer(f"👤 <a href='tg://user?id={tid}'>{u.first_name}</a>\n🔗 @{u.username}\n🆔 <code>{tid}</code>", parse_mode="HTML")
    except: await message.answer("❌ Пример: /whois 123456789")

@dp.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def cb_admin_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT gender, hair, height, feature, university, course FROM radar ORDER BY user_id DESC LIMIT 30")
    users = cursor.fetchall()
    if not users: return await callback.answer("Пусто.", show_alert=True)
    text = "📊 <b>Последние анкеты:</b>\n\n"
    for i, u in enumerate(users, 1): text += f"👤 <b>Юзер {i}:</b> {', '.join([TRANSLATE.get(k, str(k)) for k in u if k])}\n\n"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
async def cb_admin_broadcast(callback: types.CallbackQuery):
    await callback.answer("Запущено...", show_alert=False)
    cursor.execute("SELECT user_id FROM radar")
    users = cursor.fetchall()
    success = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, "🤖 <b>Новое меню!</b>\nНажми /start, чтобы участвовать в розыгрышах.", parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.1)
        except: pass
    await bot.send_message(ADMIN_ID, f"📢 <b>Доставлено: {success} чел.</b>", parse_mode="HTML")

@dp.callback_query(F.data == "admin_close", F.from_user.id == ADMIN_ID)
async def cb_admin_close(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=False))
        await callback.answer("🔒 Закрыты!", show_alert=True)
    except: pass

@dp.callback_query(F.data == "admin_open", F.from_user.id == ADMIN_ID)
async def cb_admin_open(callback: types.CallbackQuery):
    try:
        await bot.set_chat_permissions(chat_id=GROUP_ID, permissions=ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True))
        await callback.answer("🔓 Открыты!", show_alert=True)
    except: pass

@dp.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    args = command.args
    if args and args.isdigit():
        inviter_id = int(args)
        if inviter_id != message.from_user.id:
            cursor.execute("SELECT user_id FROM radar WHERE user_id = ?", (message.from_user.id,))
            if not cursor.fetchone():
                await state.update_data(inviter_id=inviter_id)

    await message.answer(
        "🎙 <b>Привет! Это предложка канала.</b>\nСкидывай текст, фото или кружки — всё опубликуем анонимно.\n👇 <b>Используй кнопки меню!</b>",
        parse_mode="HTML", reply_markup=get_main_menu()
    )

@dp.message(F.text == "🎯 Настроить радар", F.chat.type == "private")
@dp.message(Command("radar"), F.chat.type == "private")
async def start_radar(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="👦 Парень", callback_data="rad_gender_male")
    builder.button(text="👧 Девушка", callback_data="rad_gender_female")
    builder.adjust(2)
    await message.answer("🎯 <b>Шаг 1. Укажи пол:</b>", parse_mode="HTML", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.gender)

@dp.callback_query(RadarForm.gender, F.data.startswith("rad_gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(gender=callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for txt, cb in [("Блонд", "blonde"), ("Темные", "dark"), ("Русые", "light_brown"), ("Рыжие", "red"), ("Цветные", "colored")]: builder.button(text=txt, callback_data=f"rad_hair_{cb}")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 2. Цвет волос?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.hair)

@dp.callback_query(RadarForm.hair, F.data.startswith("rad_hair_"))
async def process_hair(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(hair=callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for txt, cb in [("Высокий", "tall"), ("Средний", "avg"), ("Невысокий", "short")]: builder.button(text=txt, callback_data=f"rad_height_{cb}")
    builder.adjust(1)
    await callback.message.edit_text("Шаг 3. Рост?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.height)

@dp.callback_query(RadarForm.height, F.data.startswith("rad_height_"))
async def process_height(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(height=callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for txt, cb in [("👓 Очки", "glasses"), ("🐉 Тату", "tattoo"), ("💍 Пирсинг", "piercing"), ("🌪 Кудряшки", "curly"), ("💇‍♀️ Каре", "kare"), ("❌ Нет", "none")]: builder.button(text=txt, callback_data=f"rad_feat_{cb}")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 4. Особая примета:", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.feature)

@dp.callback_query(RadarForm.feature, F.data.startswith("rad_feat_"))
async def process_feature(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(feature=callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for txt, cb in [("РАНХиГС", "ranepa"), ("МИРЭА", "mirea"), ("МПГУ", "mpgu"), ("МГИМО", "mgimo")]: builder.button(text=txt, callback_data=f"rad_uni_{cb}")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 5. ВУЗ?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.university)

@dp.callback_query(RadarForm.university, F.data.startswith("rad_uni_"))
async def process_uni(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(university=callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for txt, cb in [("1 курс", "c1"), ("2 курс", "c2"), ("3 курс", "c3"), ("4 курс", "c4")]: builder.button(text=txt, callback_data=f"rad_course_{cb}")
    builder.adjust(2)
    await callback.message.edit_text("Шаг 6. Курс?", reply_markup=builder.as_markup())
    await state.set_state(RadarForm.course)

@dp.callback_query(RadarForm.course, F.data.startswith("rad_course_"))
async def process_course(callback: types.CallbackQuery, state: FSMContext):
    course = callback.data.split("_")[2]
    data = await state.get_data()
    uid = callback.from_user.id
    
    cursor.execute("SELECT inviter_id FROM radar WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    exist_inv = row[0] if row else data.get('inviter_id')
    is_new = not row and exist_inv
    
    cursor.execute("REPLACE INTO radar (user_id, gender, hair, height, feature, university, course, inviter_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (uid, data['gender'], data['hair'], data['height'], data['feature'], data['university'], course, exist_inv))
    conn.commit()
    
    if is_new:
        try: await bot.send_message(exist_inv, "🎉 <b>Новый реферал!</b>\n+1 билет в розыгрыше!", parse_mode="HTML")
        except: pass
            
    await callback.message.edit_text("✅ <b>Профиль сохранен!</b>", parse_mode="HTML")
    await state.clear()

@dp.message(F.text == "💌 Валентинка", F.chat.type == "private")
async def info_valentine(message: types.Message):
    await message.answer("💌 Пиши <code>/love текст</code>", parse_mode="HTML")

@dp.message(Command("love"), F.chat.type == "private")
async def send_valentine(message: types.Message):
    clean = (message.text or message.caption or "").replace("/love", "").strip()
    if not clean and not message.photo: return
    v_text = f"💌 <b>АНОНИМНАЯ ВАЛЕНТИНКА</b> 💌\n\n<i>{clean}</i>\n\n<a href='https://t.me/LoveUgoZapad'>Признания</a>"
    try:
        if message.photo: await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=v_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else: await bot.send_message(chat_id=ADMIN_ID, text=v_text, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Улетело на модерацию! ❤️")
    except: pass

@dp.message(F.voice, F.chat.type == "private")
async def handle_voice(message: types.Message):
    await bot.send_voice(chat_id=ADMIN_ID, voice=message.voice.file_id, caption="🎙 <b>ГОЛОСОВОЕ</b>", parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
    await message.answer("Отправлено на модерацию!")

@dp.message(F.video_note, F.chat.type == "private")
async def handle_video_note(message: types.Message):
    await bot.send_video_note(chat_id=ADMIN_ID, video_note=message.video_note.file_id, reply_markup=get_admin_kb(message.chat.id))
    await message.answer("Отправлено на модерацию!")

@dp.message(F.content_type.in_({'text', 'photo'}), F.chat.type == "private")
async def handle_suggestion(message: types.Message):
    if message.text and message.text.startswith('/'): return
    sig = "\n\n<a href='https://t.me/LoveUgoZapad'>Признания</a>"
    utext = message.html_text or ""
    try:
        if message.photo: await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=utext + sig, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        else: await bot.send_message(chat_id=ADMIN_ID, text=utext + sig, parse_mode="HTML", reply_markup=get_admin_kb(message.chat.id))
        await message.answer("Улетело на модерацию!")
    except: pass

@dp.callback_query(F.data.startswith("pub_"))
async def cb_publish(callback: types.CallbackQuery):
    _, uid = callback.data.split("_")
    try:
        pub_msg = await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=callback.message.message_id, reply_markup=None)
        kb = InlineKeyboardBuilder().button(text="Опубликовано ✅", callback_data="done")
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await bot.send_message(chat_id=int(uid), text="Твой пост опубликован!")
        asyncio.create_task(notify_radar(callback.message.text or callback.message.caption or "", pub_msg.message_id))
    except: pass

@dp.callback_query(F.data.startswith("rej_"))
async def cb_reject(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder().button(text="Отклонено ❌", callback_data="done")
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())

@dp.callback_query(F.data == "done")
async def cb_done(callback: types.CallbackQuery): await callback.answer()

FAKE_POSTS = ["ищу парня который сегодня в столовой на 3 этаже уронил вилку..."]

@dp.callback_query(F.data == "admin_fake", F.from_user.id == ADMIN_ID)
async def cb_admin_fake(callback: types.CallbackQuery):
    if not FAKE_POSTS: return await callback.answer("❌ Пусто", show_alert=True)
    fake_text = random.choice(FAKE_POSTS)
    FAKE_POSTS.remove(fake_text)
    try:
        msg = await bot.send_message(chat_id=CHANNEL_ID, text=fake_text + "\n\n<a href='https://t.me/LoveUgoZapad'>Признания</a>", parse_mode="HTML")
        await callback.answer("✅ Опубликовано!", show_alert=True)
        asyncio.create_task(notify_radar(fake_text, msg.message_id))
    except: pass

async def main():
    dp.message.middleware(CheckSubscriptionMiddleware())
    dp.callback_query.middleware(CheckSubscriptionMiddleware())
    
    # Запускаем фоновую задачу рулетки вместе с ботом
    asyncio.create_task(giveaway_scheduler())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

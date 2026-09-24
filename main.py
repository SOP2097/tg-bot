import asyncio
import logging
import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, ChatPermissions, ReplyKeyboardMarkup, KeyboardButton
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

# === ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ===
conn = sqlite3.connect('radar.db', check_same_thread=False)
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

# === СЛОВАРЬ ТРИГГЕРОВ ===
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
                matched_str = ", ".join([f"{k}: {v}" for k, v in matched.items()])
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

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin_panel(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎲 Фейкпуб", callback_data="admin_fake")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🔒 Закрыть чат", callback_data="admin_close")
    builder.button(text="🔓 Открыть чат", callback_data="admin_open")
    builder.adjust(1)
    await message.answer("🛠 <b>Панель управления каналом:</b>", parse_mode="HTML", reply_markup=builder.as_markup())

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
                "Мы добавили новые функции (выбор ВУЗа и курса).\n"
                "Пожалуйста, заполни анкету радара заново, чтобы не пропустить, когда тебя будут искать!\n\n"
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

@dp.message(F.text == "🎯 Настроить радар")
@dp.message(Command("radar"))
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

@dp.message(F.text == "💌 Валентинка")
async def info_valentine(message: types.Message):
    await message.answer(
        "💌 <b>Как отправить валентинку?</b>\n\n"
        "Напиши в чат команду <code>/love</code> и текст своего признания.\n\n"
        "<i>Пример:</i>\n<code>/love Девочка в белом пуховике у 2 корпуса, ты супер!</code>",
        parse_mode="HTML"
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎙 <b>Привет! Это предложка канала Признания Юго-Западная.</b>\n\n"
        "Скидывай сюда текст, фото, голосовые или видеокружки — всё опубликуем анонимно после модерации.\n\n"
        "👇 <b>Используй кнопки меню внизу, чтобы настроить радар примет!</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@dp.message(Command("love"))
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
    "парень из 3 группы фнн, который сегодня отвечал у доски, у тебя очень красивый голос",
    "ищу девочку блондинку с голубыми глазами, были сегодня на одном потоке в 315 ауд. на тебе был еще розовый шарф",
    "ребята с юрфака которые вчера громко обсуждали доту в коридоре 4 этажа, можно с вами как-нибудь сыграть?",
    "парень в бежевом пальто и круглых очках, спускался по лестнице в главном здании часов в 11. выглядишь очень атмосферно",
    "девушка с татуировкой змеи на ключице, стояла в очереди в гардероб, мы переглянулись. найдись",
    "кто потерял черный картхолдер тинькофф возле библиотеки? отдал охраннику",
    "ищу типа который на паре по макре сегодня уснул на задней парте. понимаю тебя",
    "девочка с веснушками в желтом свитере, ты покупала булочку на перемене. у тебя красивая улыбка",
    "парень который вчера около 16:30 стоял на остановке возле уника под зонтом. был в черных конверсах. найдись",
    "понравился мальчик, высокий, светлые волосы, был в синей ветровке. играл в теннис на физре сегодня",
    "девчонки с 1 курса дизайна, вы очень стильно одеваетесь",
    "парень со скейтом, проехал мимо меня у главного входа примерно в 10 утра.",
    "девушка в черном платье и грубых ботинках на шнуровке, сидела на подоконнике на 2 этаже. отзовись если свободна",
    "парень с рюкзаком ванс, ты сегодня споткнулся на лестнице и сделал вид что так и задумано. забавно вышло",
    "ищу девочку в наушниках эпл макс, видела тебя в очереди за кофе. ты была в бежевом тренче",
    "парень из ибда который всегда ходит в костюмах тройках. выглядит очень круто",
    "девочка в розовом шарфе, шли сегодня вместе от метро к универу. ты очень милая",
    "кто тот парень брюнет из 12 группы который постоянно шутит на семинарах?",
    "парень в футболке с принтом евангелиона, стоял у расписания на 1 этаже. давай общаться",
    "девушка со стаканчиком кофе, стояла сегодня возле вкусно и точка на южке примерно в 15:00. была в черной куртке, найдись",
    "парень который сегодня на физре забил трехочковый в самом конце. хорош",
    "ищу парня, глаза карие, волосы немного вьются, был в серой зипке. стоял курил возле курилки с высоким другом",
    "девчонка в белых брюках карго и черном топе, были на совместной лекции по истории. ты постоянно крутила ручку",
    "мальчик с гитарой который сидел на пуфиках в коворкинге, очень красиво играл",
    "девушка с красной помадой и в черном берете, видела тебя в столовой. очень эстетично выглядишь",
    "парни с 4 курса фмб, спасибо что помогли найти нужную аудиторию сегодня первашу",
    "ищу девочку, темные волосы по плечи, была в рубашке в клетку оверсайз. сидели рядом в читальном зале",
    "молодой человек в белых джорданах и кепке, стоял сегодня у банкомата. ты оч стильный",
    "девушка в зеленом кардигане, ты сегодня выронила пропуск на турникетах, я тебе его подал.",
    "парень с пирсингом брови из 8 группы, найдись",
    "девчонка с длинными русыми волосами, была в джинсовке. шла сегодня от авеню в сторону 5 корпуса примерно в 15:30",
    "парень в футболке slipknot найдись, я тоже их слушаю",
    "ищу парня в черном худи с капюшоном, ты сидел на лавочке перед универом и пил энергетик",
    "девочка в черной юбке в складку и белых гольфах. видела тебя на перемене, выглядишь супер",
    "парень который сегодня на паре по вышмату решал судоку в телефоне.",
    "девушка с рыжими кудряшками, мы вместе ехали в лифте на 6 этаж. у тебя классный парфюм",
    "мальчики из 2 корпуса которые сегодня пели макса коржа на весь хор, подняли настроение",
    "ищу парня с тату паутины на локте, видел тебя в курилке.",
    "девчонка в леопардовых штанах, которая сегодня громко разговаривала по телефону возле деканата.",
    "парень с хвостиком на голове, в черной водолазке. стоял у автомата с едой на 2 этаже. отзовись",
    "девушка в очках авиаторах и кожаном плаще, выглядишь очень стильно",
    "ищу парня из команды по волейболу, номер 7 вроде. круто играешь",
    "девочка с розовым рюкзаком канкен, ты забыла тетрадь по инглишу в 412 аудитории, я отнесла на кафедру",
    "парень в сером пальто и белом шарфе, ты сегодня смотрел на меня в метро а потом вышел на станции юго-западная и пошел к универу. найдись",
    "девушка с челкой и в черном чокере, сидела в телефоне возле 3 аудитории.",
    "парень который гоняет на электросамокате в желтой куртке, будь осторожнее, чуть не сбил сегодня",
    "ищу девочку в синем худи с надписью GAP, ты сегодня покупала двойной капучино",
    "парень с кудряшками из 1 курса журналистики. ты очень харизматичный",
    "девчонка в белых кроссах на высокой платформе, выглядит очень необычно",
    "молодой человек в очках, сидел на 1 парте на философии. ты очень интересно спорил с преподавателем",
    "девушка с зеленым шоппером, на котором нарисован лягушонок.",
    "ищу парня который сегодня в гардеробе отдал мне свою куртку без очереди. спасибо тебе",
    "девчонки из танцевальной сборной, вы вчера на репетиции были супер. удачи на выступлении",
    "парень в спортивках адидас и черной панаме, стоял на крыльце 4 корпуса.",
    "девушка в розовом пуховике, мы с тобой столкнулись глазами на эскалаторе.",
    "парень из 5 группы ит, который всегда ходит с термосом.",
    "ищу девочку с короткими светлыми волосами, была в черной водолазке и серебряной цепочке.",
    "мальчик в рубашке с драконами, ты сидел сегодня в коворкинге за ноутом.",
    "девушка с пирсингом септума и в берцах, видела тебя в курилке 2 корпуса.",
    "парень который сегодня читал стихи на литературе. очень красиво",
    "ищу парня с синими прядями в волосах, был в джинсовой куртке с нашивками.",
    "девочка в бежевом тренче и с шелковым платком на шее, очень красиво выглядишь",
    "парень который сегодня переходил проспект вернадского в сторону академии около 9:40. был в черном пальто и с кожаным портфелем. отзовись",
    "девушка с татуировкой бабочки на руке, стояла сегодня в очереди за пиццей в столовой.",
    "парень в черной рубашке расстегнутой на пару пуговиц, ты проходил мимо 210 кабинета примерно в 14:20.",
    "девчонка с дредокудрями, ты сегодня сидела на лавочке в сквере.",
    "парень с сумкой мессенджером через плечо, постоянно вижу тебя в коридорах.",
    "ищу девушку из 2 группы фмп, ты сегодня была в красивом красном платье на парах.",
    "парень в футболке с риком и морти, мы переглянулись возле расписания.",
    "девочка с пучком на голове и в очках для зрения, ты мило морщила нос когда читала конспект",
    "парень из студсовета который сегодня бегал с документами по 1 этажу.",
    "ищу девушку в серых спортивных штанах и белом топе, мы вместе бегали на физре в тропаревском парке сегодня. ты быстро бегаешь",
    "мальчик с веснушками и русыми волосами, ты сегодня покупал воду в автомате",
    "девчонка в черном корсете поверх белой рубашки, очень стильный образ",
    "парень с бородой и в клетчатой рубашке, ты сидел в библиотеке за 3 столом.",
    "девушка с розовым маникюром, мы вместе сидели на задней парте на экономике.",
    "ищу парня который сегодня играл на пианино в актовом зале.",
    "парень который стоял на остановке возле мирэа и ждал автобус. ты был в наушниках и бордовой толстовке. найдись",
    "девочка с сережками в виде вишен, стояла сегодня возле деканата и грустила. не грусти",
    "парень в кожаной куртке и с гитарным чехлом за спиной, ты заходил в 5 корпус в 9 утра.",
    "девушка в синих джинсах клеш и белом кроп топе, видела тебя возле зеркала на 2 этаже.",
    "ищу парня из 7 группы, ты всегда ходишь в наушниках.",
    "девчонка с гетерохромией (разные глаза), видела тебя на лекции потока. очень необычно",
    "парень который сегодня на матане задал смешной вопрос преподу.",
    "девушка в пушистом белом свитере, видела тебя на фудкорте в авеню после пар. ты сидела с подругой",
    "парень с кольцом на большом пальце и татуировкой на шее, стоял курил возле главного входа в 15:40. отзовись",
    "ищу девочку в черной юбке карандаш и красных туфлях, ты сегодня защищала проект на семинаре. выступила отлично",
    "мальчик в белом худи трешер, ты сегодня смеялся над чем-то в телефоне на паре.",
    "девчонка с зелеными стрелками, ты сидела сегодня на подоконнике 3 этажа. красивый макияж",
    "парень который сегодня помогал носить стулья в актовом зале.",
    "ищу девушку с черным рюкзаком со значками, мы ехали вместе в автобусе до универа.",
    "парень в синем спортивном костюме, ты сегодня подтянулся на турнике на физре 20 раз.",
    "девочка которая сегодня плакала на лестнице запасного выхода, надеюсь у тебя все наладилось"
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
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

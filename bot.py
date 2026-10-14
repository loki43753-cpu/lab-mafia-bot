import telebot
from telebot import types
import random
import time
import threading

# Вставте свій токен від @BotFather:
TOKEN = "8896144568:AAF5hdyQKoR-xah6gxrZfK_Phsdn2k5ouXg"

bot = telebot.TeleBot(TOKEN)

# Наші ролі у лабораторному стилі
ROLE_NAMES = {
    "bacteriophage": "🦠 Бактерія (Мафія — здійснює таємне зараження)",
    "antiseptic": "🧪 Антисептик (Лікар — захищає від зараження)",
    "lab_assistant": "🔬 Лаборант (Мирний житель — шукає порушників)",
    "head_researcher": "🕵️ Завідувач лабораторії (Шериф — перевіряє статус інших)",
    "annoying_student": "🏃‍♂️ Бісячий студент (Нейтрал — відволікає)"
}

game_session = None

class GameSession:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = {}  # user_id: {"name": name, "role": role, "alive": True}
        self.state = "waiting"  # waiting, night, day, voting
        self.night_actions = {}  # role_action: target_id
        self.votes = {}  # voter_id: target_id
        self.pending_last_words = None  # user_id гравця, який пише предсмертне слово

GUIDE_TEXT = """
🥼 **ОФІЦІЙНИЙ ГАЙД: НАУКОВА ЛАБОРАТОРІЯ МАФІЇ** 🧪

Вітаємо у лавах дослідників! Цей бот проводить інтерактивну рольову гру «Мафія» в атмосфері біологічної лабораторії.

📋 **ЯК ПОЧАТИ ГРУ:**
1️⃣ **Підготовка:** Кожен гравець має обов'язково написати боту в особисті повідомлення `/start`.
2️⃣ **Запуск:** У груповому чаті введіть команду `/game`.
3️⃣ **Реєстрація:** Натисніть **«🧬 Приєднатися до експерименту»**.
4️⃣ **Старт:** Натисніть **«🚀 Роздати ролі (Старт)»** (від 3 учасників).
"""

@bot.message_handler(commands=['start', 'help'])
def send_help(message):
    bot.reply_to(message, GUIDE_TEXT, parse_mode="Markdown")

@bot.message_handler(commands=['game'])
def start_game(message):
    global game_session
    chat_id = message.chat.id
    
    game_session = GameSession(chat_id)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧬 Приєднатися до експерименту", callback_data="join"))
    markup.add(types.InlineKeyboardButton("🚀 Роздати ролі (Старт)", callback_data="start_night"))
    
    bot.send_message(
        chat_id, 
        "🧪 **Збір учасників до Лабораторії розпочато!**\nХто готовий взяти участь у дослідженні?", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global game_session
    if not game_session:
        bot.answer_callback_query(call.id, "Гра ще не створена!")
        return

    user_id = call.from_user.id
    user_name = call.from_user.first_name

    if call.data == "join":
        if user_id in game_session.players:
            bot.answer_callback_query(call.id, "Ви вже в експерименті!")
        else:
            game_session.players[user_id] = {"name": user_name, "role": None, "alive": True}
            bot.answer_callback_query(call.id, "Ви успішно приєдналися!")
            
            players_list = "\n".join([f"• {p['name']}" for p in game_session.players.values()])
            try:
                bot.edit_message_text(
                    f"🧪 **Збір учасників триває!**\n\nЗареєстровані дослідники:\n{players_list}",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=call.message.reply_markup,
                    parse_mode="Markdown"
                )
            except:
                pass

    elif call.data == "start_night":
        if len(game_session.players) < 3:
            bot.answer_callback_query(call.id, "Потрібно мінімум 3 учасники для експерименту!", show_alert=True)
            return
        
        user_ids = list(game_session.players.keys())
        roles_pool = ["bacteriophage", "antiseptic", "head_researcher"]
        while len(roles_pool) < len(user_ids):
            roles_pool.append("lab_assistant")
        
        random.shuffle(roles_pool)
        
        for i, uid in enumerate(user_ids):
            role_key = roles_pool[i]
            game_session.players[uid]["role"] = role_key
            full_role = ROLE_NAMES[role_key]
            try:
                bot.send_message(uid, f"🥼 Ваша таємна роль у лабораторії:\n\n{full_role}")
            except:
                pass

        try:
            bot.edit_message_text(
                "🚀 **Експеримент розпочато!** Ролі роздано у приватні повідомлення.\n\n🌙 Настає **НІЧ** у лабораторії. Активні ролі отримали інструкції в особистих повідомленнях від бота!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
        except:
            pass
        
        game_session.state = "night"
        start_night_phase()

def start_night_phase():
    for uid, data in game_session.players.items():
        if not data["alive"]:
            continue
        role = data["role"]
        markup = types.InlineKeyboardMarkup()
        for target_id, target_data in game_session.players.items():
            if target_data["alive"]:
                markup.add(types.InlineKeyboardButton(target_data["name"], callback_data=f"night_{role}_{target_id}"))
        
        try:
            if role == "bacteriophage":
                bot.send_message(uid, "🦠 **НІЧНИЙ ХІД:** Виберіть дослідника, якого хочете **заразити**:", reply_markup=markup, parse_mode="Markdown")
            elif role == "antiseptic":
                bot.send_message(uid, "🧪 **НІЧНИЙ ХІД:** Виберіть дослідника, якого хочете **захистити (продезінфікувати)**:", reply_markup=markup, parse_mode="Markdown")
            elif role == "head_researcher":
                bot.send_message(uid, "🕵️ **НІЧНИЙ ХІД:** Виберіть дослідника для **перевірки статусу**:", reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(uid, "🌙 Настала ніч. Ви мирний лаборант, очікуйте ранку та перевіряйте чат.", parse_mode="Markdown")
        except:
            pass

    threading.Thread(target=night_timer).start()

def night_timer():
    time.sleep(30)
    if game_session and game_session.state == "night":
        resolve_night()

@bot.callback_query_handler(func=lambda call: call.data.startswith("night_"))
def handle_night_action(call):
    global game_session
    if not game_session or game_session.state != "night":
        bot.answer_callback_query(call.id, "Зараз не нічний хід!", show_alert=True)
        return
    
    parts = call.data.split("_")
    role = parts[1]
    target_id = int(parts[2])
    
    game_session.night_actions[role] = target_id
    target_name = game_session.players[target_id]["name"]
    
    bot.answer_callback_query(call.id, f"Ви обрали: {target_name}")
    try:
        bot.edit_message_text(f"✅ Ваш вибір прийнято: **{target_name}**.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except:
        pass
        
    if "bacteriophage" in game_session.night_actions and "antiseptic" in game_session.night_actions:
        resolve_night()

def resolve_night():
    global game_session
    if not game_session or game_session.state != "night":
        return
    
    game_session.state = "day"
    chat_id = game_session.chat_id
    
    bact_target = game_session.night_actions.get("bacteriophage")
    anti_target = game_session.night_actions.get("antiseptic")
    sherif_target = game_session.night_actions.get("head_researcher")
    
    if sherif_target:
        for uid, data in game_session.players.items():
            if data["role"] == "head_researcher" and data["alive"]:
                is_bact = (game_session.players[sherif_target]["role"] == "bacteriophage")
                res_text = "🦠 Це Бактерія (шкідник)!" if is_bact else "✨ Це мирний дослідник."
                try:
                    bot.send_message(uid, f"🕵️ Результат перевірки гравця {game_session.players[sherif_target]['name']}:\n{res_text}")
                except:
                    pass

    killed_uid = None
    killed_name = None
    if bact_target:
        if bact_target != anti_target:
            game_session.players[bact_target]["alive"] = False
            killed_uid = bact_target
            killed_name = game_session.players[bact_target]["name"]
    
    report = "☀️ **РАНОК У ЛАБОРАТОРІЇ!** Сонце зійшло, підбиваємо підсумки нічних подій:\n\n"
    if killed_name:
        report += f"💀 Вночі Бактерія атакувала дослідника **{killed_name}**. Врятувати його не вдалося...\n\n"
        game_session.pending_last_words = killed_uid
        report += f"🕯️ **{killed_name}** загинув, але за правилами лабораторії має право на **предсмертне слово**. Напишіть його сюди в чат протягом 25 секунд!\n\n"
    else:
        report += "✨ Ніч минула спокійно: або Антисептик вчасно зробив дезінфекцію, або ніхто не постраждав.\n\n"
    
    alive_list = ", ".join([p["name"] for p in game_session.players.values() if p["alive"]])
    report += f"🟢 **Живі учасники експерименту:** {alive_list}\n\n"
    report += "🗣️ Обговорюйте ситуацію та введіть команду `/vote`, щоб розпочати денний суд."
    
    bot.send_message(chat_id, report, parse_mode="Markdown")
    game_session.night_actions.clear()

@bot.message_handler(commands=['vote'])
def start_voting(message):
    global game_session
    if not game_session or game_session.state != "day":
        bot.reply_to(message, "Зараз не час для голосування!")
        return
    
    game_session.state = "voting"
    markup = types.InlineKeyboardMarkup()
    for uid, data in game_session.players.items():
        if data["alive"]:
            markup.add(types.InlineKeyboardButton(f"Вигнати: {data['name']}", callback_data=f"vote_{uid}"))
            
    bot.send_message(message.chat.id, "🗳️ **ДЕННИЙ СУД ЛАБОРАТОРІЇ!** Хто на вашу думку причетний до інциденту? Оберіть кандидата кнопкою нижче:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    global game_session
    if not game_session or game_session.state != "voting":
        return
    
    voter_id = call.from_user.id
    if voter_id not in game_session.players or not game_session.players[voter_id]["alive"]:
        bot.answer_callback_query(call.id, "Ви не можете голосувати!", show_alert=True)
        return
        
    target_id = int(call.data.split("_")[1])
    game_session.votes[voter_id] = target_id
    
    target_name = game_session.players[target_id]["name"]
    bot.answer_callback_query(call.id, f"Ваш голос проти {target_name} зараховано!")
    
    alive_players = [uid for uid, p in game_session.players.items() if p["alive"]]
    if len(game_session.votes) >= len(alive_players):
        resolve_voting()

def resolve_voting():
    global game_session
    if not game_session:
        return
        
    chat_id = game_session.chat_id
    vote_counts = {}
    for target in game_session.votes.values():
        vote_counts[target] = vote_counts.get(target, 0) + 1
        
    report = "⚖️ **РЕЗУЛЬТАТИ ДЕННОГО ГОЛОСУВАННЯ:**\n\n"
    for uid, count in vote_counts.items():
        name = game_session.players[uid]["name"]
        report += f"• {name} отримав(ла) голосів: {count}\n"
    
    if vote_counts:
        max_votes = max(vote_counts.values())
        candidates = [uid for uid, count in vote_counts.items() if count == max_votes]
        
        if len(candidates) == 1:
            exiled_id = candidates[0]
            game_session.players[exiled_id]["alive"] = False
            exiled_name = game_session.players[exiled_id]["name"]
            
            game_session.pending_last_words = exiled_id
            report += f"\n🚨 Більшістю голосів лабораторія виганяє **{exiled_name}**!\n\n🕯️ У вас є можливість залишити своє **предсмертне слово** в наступному повідомленні."
        else:
            report += "\n🤝 Голоси розділилися порівну, нікого не вигнали."
    
    bot.send_message(chat_id, report, parse_mode="Markdown")
    game_session.votes.clear()
    
    check_win_conditions(chat_id)

@bot.message_handler(func=lambda message: game_session and game_session.pending_last_words == message.from_user.id)
def handle_last_words(message):
    global game_session
    user_name = message.from_user.first_name
    text = message.text
    
    bot.send_message(
        message.chat.id, 
        f"📜 **Предсмертне слово від {user_name}:**\n> *{text}*", 
        parse_mode="Markdown"
    )
    game_session.pending_last_words = None

def check_win_conditions(chat_id):
    global game_session
    alive_bact = sum(1 for p in game_session.players.values() if p["alive"] and p["role"] == "bacteriophage")
    alive_others = sum(1 for p in game_session.players.values() if p["alive"] and p["role"] != "bacteriophage")
    
    if alive_bact == 0:
        bot.send_message(chat_id, "🎉 **ПЕРЕМОГА ЛАБОРАТОРІЇ!** Усі Бактерії ізольовані, комплекс у безпеці! 🧫🏆", parse_mode="Markdown")
        game_session = None
    elif alive_bact >= alive_others:
        bot.send_message(chat_id, "🦠 **ПЕРЕМОГА БАКТЕРІЙ!** Вони захопили більшість і знищили персонал... Експеримент провалено. 🧪💀", parse_mode="Markdown")
        game_session = None
    else:
        bot.send_message(chat_id, "🌙 Сонце сідає. Науковий комплекс занурюється у темряву. Настає **НІЧ**...", parse_mode="Markdown")
        game_session.state = "night"
        start_night_phase()

if __name__ == "__main__":
    print("Бот успішно запущений!")
    bot.infinity_polling()

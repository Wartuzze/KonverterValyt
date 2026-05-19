import telebot
from telebot import types
import requests
import time
import json

TOKEN = "8789610596:AAHCwNKY1SG3QHFVzTxcSkcfeCQJpXJdbHI"
bot = telebot.TeleBot(TOKEN)
user_state = {}

valuts = {"🇺🇸 Доллар":"USD","🇷🇺 Рубль":"RUB","🇺🇿 Сум":"UZS","🇪🇺 Евро":"EUR"}
OWNER = "@LetsGooBroo"
rate_cache = {}
CACHE_TIME = 300

def get_rate(fr, to):
    k = f"{fr}_{to}"
    if k in rate_cache:
        r, t = rate_cache[k]
        if time.time() - t < CACHE_TIME:
            return r
    try:
        d = requests.get(f"https://api.exchangerate-api.com/v4/latest/{fr}", timeout=5).json()
        rate = d['rates'].get(to)
        if rate:
            rate_cache[k] = (rate, time.time())
        return rate
    except:
        return rate_cache[k][0] if k in rate_cache else None

def get_keyboard(step, exclude=None):
    kb = types.InlineKeyboardMarkup(row_width=2)
    for n, c in valuts.items():
        if c != exclude:
            kb.add(types.InlineKeyboardButton(n, callback_data=f"{step}:{c}"))
    kb.add(types.InlineKeyboardButton("🔄 Начать заново", callback_data="restart"))
    kb.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.chat.id] = {'ts': time.time()}
    txt = f"👋 Привет! Я Конвертер Валют.\n💰 Перевожу доллары, рубли, сумы и евро.\n📝 Выбери первую валюту:\n\n👨‍💻 Владелец: {OWNER}"
    bot.send_message(message.chat.id, txt, reply_markup=get_keyboard("from"))

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = call.message.chat.id
    if call.data == "restart":
        user_state[cid] = {'ts': time.time()}
        bot.answer_callback_query(call.id, "Заново!")
        bot.edit_message_text("🚀 Выбери первую валюту:", cid, call.message.message_id, reply_markup=get_keyboard("from"))
        return
    if call.data == "cancel":
        user_state.pop(cid, None)
        bot.answer_callback_query(call.id, "Отменено")
        bot.edit_message_text(f"👋 Отменено. /start — начать заново.\n👨‍💻 {OWNER}", cid, call.message.message_id)
        return
    try:
        step, code = call.data.split(":")
    except:
        return
    if step == "from":
        user_state[cid] = {'from_code': code, 'ts': time.time()}
        name = [n for n, c in valuts.items() if c == code][0]
        bot.answer_callback_query(call.id, f"Выбрано: {name}")
        bot.edit_message_text(f"✅ Валюта: {name}\n📝 Введи сумму:", cid, call.message.message_id)
    elif step == "to":
        if cid not in user_state or 'amount' not in user_state[cid]:
            bot.answer_callback_query(call.id, "Сначала введи сумму!")
            return
        to_code = code
        from_code = user_state[cid]['from_code']
        amount = user_state[cid]['amount']
        to_name = [n for n, c in valuts.items() if c == code][0]
        from_name = [n for n, c in valuts.items() if c == from_code][0]
        rate = get_rate(from_code, to_code)
        if rate:
            res = round(amount * rate, 2)
            txt = f"💱 Результат:\n{amount} {from_name} = {res} {to_name}\n📊 Курс: 1 {from_code} = {round(rate,4)} {to_code}\n👨‍💻 {OWNER}"
        else:
            txt = f"😔 Сервер валют недоступен.\n👨‍💻 {OWNER}"
        user_state.pop(cid, None)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔄 Новый расчёт", callback_data="restart"))
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=kb)

@bot.message_handler(content_types=['text'])
def text_handler(message):
    cid = message.chat.id
    if cid in user_state and 'from_code' in user_state[cid] and 'amount' not in user_state[cid]:
        try:
            t = message.text.replace(',', '.')
            amount = float(t)
            if amount <= 0 or amount > 999999999:
                bot.send_message(cid, "❌ Сумма от 1 до 999999999!")
                return
            user_state[cid]['amount'] = amount
            code = user_state[cid]['from_code']
            name = [n for n, c in valuts.items() if c == code][0]
            bot.send_message(cid, f"✅ Сумма: {amount} {name}\n🎯 Выбери валюту для конвертации:", reply_markup=get_keyboard("to", code))
        except ValueError:
            bot.send_message(cid, "❌ Введи только число!")
    else:
        bot.send_message(cid, f"👋 Используй /start\n👨‍💻 {OWNER}")

print("✅ Конвертер v5 запущен!")
while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except Exception as e:
        print(f"⚠️ Ошибка: {e}. Перезапуск...")
        time.sleep(5)
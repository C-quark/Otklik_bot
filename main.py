import telebot
import sqlite3
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import token_config
from regions import regions
from utils import is_valid_date, format_users
from datetime import date

token = token_config
bot = telebot.TeleBot(token)
database = 'stalkerhalt.db'

date_today = date.today()

command = '\n'.join([
        'Привет, выбери одну из команд:',
        '/reg - выбрать свой регион',
        '/get - получить список возможных компаньонов',
        '/stalk - получить вылазки',
        '/create - создать вылазку',
        '/del - удалить вылазку'])


@bot.message_handler(commands=['start'])
def send_start(message):
    buttons_markup = ReplyKeyboardMarkup(True)
    buttons_markup.row('/reg', '/get', '/stalk', '/create', '/help', '/del')
    bot.send_message(message.from_user.id, command, reply_markup=buttons_markup)


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.from_user.id, command)


@bot.message_handler(commands=['reg'])
def reg(message):
    keyboard = InlineKeyboardMarkup()
    i = 1
    for region in regions:
        button = InlineKeyboardButton(text=f'{region}', callback_data=f'region_{i}')
        i += 1
        keyboard.add(button)
    bot.send_message(message.from_user.id, 'Выберите свой регион', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(callback_query_id=call.id)
    # TODO: Заменить ответ на callback
    username = call.from_user.username
    user_id = call.from_user.id
    params = call.data.split('_')

    if len(params) != 2:
        # TODO: Сделать запись в лог
        bot.send_message(call.from_user.id, 'Неизвестная команда')
        return
    button_type, region_id = params

    if button_type == 'region':
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        query = 'SELECT user_id FROM user_region WHERE user_id = ?'
        cursor.execute(query, (user_id,))
        user_id_sql = cursor.fetchone()
        if user_id_sql is None:
            query = 'INSERT INTO user_region (region_id, user_id, username) VALUES (?, ?, ?)'
            cursor.execute(query, (region_id, user_id, username))
        else:
            query = 'UPDATE user_region SET region_id = ?, username = ? WHERE user_id = ?'
            cursor.execute(query, (region_id, username, user_id))
        connection.commit()
        query = 'SELECT regions FROM region WHERE region_id = ?'
        cursor.execute(query, (region_id,))
        region_sql = cursor.fetchone()
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, 'Регион выбран: ' + region_sql[0])
    # elif button_type == 'city':
    #     pass
    else:
        # TODO: Сделать запись в лог
        bot.send_message(call.from_user.id, 'Неизвестная команда')


@bot.message_handler(commands=['get'])
def get_users_by_region(message):
    connection = sqlite3.connect(database)
    user_id = message.from_user.id
    cursor = connection.cursor()
    query = 'SELECT region_id FROM user_region WHERE user_id = ?'
    cursor.execute(query, (user_id,))
    region_id_sql = cursor.fetchone()
    if region_id_sql is None:
        bot.send_message(user_id, 'Чтобы посмотреть людей из вашей области, нажмите команду /reg и укажите свой регион')
    else:
        query = 'SELECT username FROM user_region WHERE region_id = ? AND user_id != ?'
        cursor.execute(query, (region_id_sql[0], user_id))
        usernames = cursor.fetchall()
        if len(usernames) == 0:
            bot.send_message(user_id, 'Люди в вашем регионе не найдены')
        else:
            bot.send_message(user_id, 'Люди из вашей области: ' + format_users(usernames))


@bot.message_handler(commands=['stalk'])
def get_stalk(message):
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    query = 'SELECT place_date_username FROM stalk WHERE stalk_date >= ?'
    cursor.execute(query, (date_today,))
    place_date_username = cursor.fetchall()
    if len(place_date_username) != 0:
        bot.send_message(message.from_user.id, 'Список вылазок')
        for stalk in place_date_username:
            bot.send_message(message.from_user.id, stalk)
    else:
        bot.send_message(message.from_user.id, 'Вылазки не найдены')


@bot.message_handler(commands=['create'])
def create_stalk(message):
    result = bot.send_message(message.from_user.id, 'Место вылазки и город')
    bot.register_next_step_handler(result, get_place)


def get_place(message):
    stalk_place = message.text
    result = bot.send_message(
        message.from_user.id,
        'Предполагаемая дата. Введите дату в формате yyyy-mm-dd, пример: 2023-01-30'
    )
    bot.register_next_step_handler(result, get_date, stalk_place)


def get_date(message, stalk_place):
    stalk_date = message.text
    if is_valid_date(stalk_date):
        stalk_username = message.from_user.username
        if stalk_username is None:
            result = bot.send_message(message.from_user.id, 'Укажите как с вами можно связаться, так как у вас нет "@username"')
            bot.register_next_step_handler(result, get_username, stalk_place, stalk_date)
        else:
            place_date_username = '\n\n'.join([
                'Дата: ' + stalk_date,
                'Место: ' + stalk_place,
                'Контакт: @' + stalk_username
            ])
            connection = sqlite3.connect(database)
            cursor = connection.cursor()
            query = 'INSERT INTO stalk (stalk_place, stalk_date, stalk_username, place_date_username) VALUES (?, ?, ?, ?)'
            cursor.execute(query, (stalk_place, stalk_date, stalk_username, str(place_date_username)))
            connection.commit()
            bot.send_message(message.from_user.id, 'Вылазка создана')
    else:
        result = bot.send_message(message.from_user.id, 'Некорректная дата, введите заново в формате yyyy-mm-dd, пример: 2023-01-30')
        bot.register_next_step_handler(result, get_date, stalk_place)


def get_username(message, stalk_place, stalk_date):
    stalk_username = message.text
    place_date_username = '\n\n'.join([
        'Дата: ' + stalk_date,
        'Место: ' + stalk_place,
        'Куда писать: ' + str(stalk_username)
    ])
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    query = 'INSERT INTO stalk (stalk_place, stalk_date, stalk_username, place_date_username) VALUES (?, ?, ?, ?)'
    cursor.execute(query, (stalk_place, stalk_date, stalk_username, str(place_date_username)))
    connection.commit()
    bot.send_message(message.from_user.id, 'Вылазка создана')


@bot.message_handler(commands=['del'])
def my_stalk(message):
    stalk_username = message.from_user.username
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    query = 'SELECT stalk_id || "\n\n" || place_date_username FROM stalk WHERE stalk_username = ?'
    cursor.execute(query, (stalk_username,))
    place_date_username = cursor.fetchall()
    if len(place_date_username) != 0:
        bot.send_message(message.from_user.id, 'Введите номер вылазки, которую следует удалить')
        for stalk in place_date_username:
            result = bot.send_message(message.from_user.id, stalk)
            bot.register_next_step_handler(result, del_stalk)
    else:
        bot.send_message(message.from_user.id, 'Вылазки не найдены')


def del_stalk(message):
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    stalk_username = message.from_user.username
    id = int(message.text)
    query = 'SELECT stalk_id FROM stalk WHERE stalk_username = ?'
    cursor.execute(query, (stalk_username,))
    stalk_id = cursor.fetchall()

    found = False
    for i in stalk_id:
        if id in i:
            query = 'DELETE FROM stalk WHERE stalk_id = ?'
            cursor.execute(query, (id,))
            connection.commit()
            bot.send_message(message.from_user.id, 'Вылазка удалена')
            found = True
            break

    if not found:
        bot.send_message(message.from_user.id, 'Нет такой вылазки')

if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)

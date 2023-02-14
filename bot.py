from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, )

# from datetime import datetime
import logging
import os
import time
import threading

from config import BUTTONS, MESSAGES
from logging.handlers import RotatingFileHandler
from models import User


load_dotenv('.env')
with open('about.txt', encoding='utf-8') as f:
    ABOUT = f.read()

bot = TeleBot(os.getenv('TOKEN'))
users = {}


logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'exceptions.log', maxBytes=50000000, backupCount=3)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

err_info = ''


def get_user(message) -> User:
    user_id = message.chat.id
    return users.setdefault(user_id, User(id=user_id))


def name_to_cmd(names):
    return ['/' + name for name in names]


def try_exec_stack(user: User):
    command = user.get_cmd_stack()
    if command and callable(command['cmd']):
        command['cmd'](**command['data'])


def make_base_kbd(buttons_name):
    keyboard = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = [KeyboardButton(name) for name in buttons_name]
    return keyboard.add(*buttons)


def breath_timer(user: User, sec=10):
    user.timer_is_on = True
    time.sleep(sec)
    buttons_name = name_to_cmd([BUTTONS['btn_breath']])
    keyboard = make_base_kbd(buttons_name)
    mess = MESSAGES['mess_hold']
    bot.send_message(user.id, mess, reply_markup=keyboard, )
    user.hold_mark = time.time()
    user.timer_is_on = False


@bot.message_handler(commands=['start'])
def welcome(message):
    user = get_user(message)
    buttons_name = name_to_cmd([BUTTONS['btn_traning']])
    keyboard = make_base_kbd(buttons_name)
    mess = MESSAGES['welcome']
    bot.send_message(user.id, mess, reply_markup=keyboard, )


@bot.message_handler(commands=['подсказка', 'help'])
def about(message):
    user = get_user(message)
    bot.send_message(user.id, ABOUT)


@bot.message_handler(commands=[BUTTONS['btn_traning']])
def start_traning(message):
    user = get_user(message)
    buttons_name = name_to_cmd([BUTTONS['btn_go']])
    keyboard = make_base_kbd(buttons_name)
    mess = MESSAGES['msg_traning']
    bot.send_message(user.id, mess, reply_markup=keyboard)


@bot.message_handler(commands=[BUTTONS['btn_go']])
def breath_interval(message):
    user = get_user(message)
    t2 = threading.Thread(target=breath_timer, args=[user])
    t2.start()
    mess = MESSAGES['msg_breath_int']
    bot.send_message(user.id, mess,)


@bot.message_handler(commands=[BUTTONS['btn_breath']])
def breath(message):
    user = get_user(message)
    if not user.timer_is_on:
        hold_time = time.time() - user.hold_mark
        mess = str(round(hold_time, 0)) + ' с'
        buttons_name = name_to_cmd([BUTTONS['btn_stop']])
        keyboard = make_base_kbd(buttons_name)
        bot.send_message(user.id, mess, reply_markup=keyboard)
        breath_interval(message)


def err_informer(chat_id):
    global err_info
    prev_err = err_info
    while True:
        if err_info == '' or err_info == prev_err:
            time.sleep(60)
            continue
        prev_err = err_info
        try:
            bot.send_message(
                chat_id,
                f'Было выброшено исключение: {err_info}')
        except Exception:
            pass


if __name__ == '__main__':
    develop_id = os.getenv('DEVELOP_ID')
    t1 = threading.Thread(target=err_informer, args=[develop_id])
    t1.start()

    while True:
        try:
            bot.polling(non_stop=True)
        except Exception as error:
            err_info = error.__repr__()
            logger.exception(error)

import telebot
from flask import Flask, request
import time
import requests
import re
import random
import threading
import os
# import sqlite3
import psycopg2
from telebot import types

bot_token = os.getenv("TOKEN")
server = Flask(__name__)
bot = telebot.TeleBot(token=bot_token)

# PostSql info
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_port = 5432

# Creating a database with tables if not exists.
# db = sqlite3.connect("TelegramBot.db") was for local connection
db = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
curs = db.cursor()

# Chats Table
curs.execute("""CREATE TABLE IF NOT EXISTS "chats" (
"chat_id"	bigint NOT NULL UNIQUE,
"rules"	TEXT DEFAULT 'There are no rules yet, please contact an admin to set them.',
"rank_delay"	INTEGER NOT NULL DEFAULT 900,
"ranking_delay"	INTEGER NOT NULL DEFAULT 1800,
"admins_delay"	INTEGER NOT NULL DEFAULT 3600,
"rankuser_delay"	INTEGER NOT NULL DEFAULT 120,
"ranking_time"	bigint DEFAULT 1,
"admins_time"   bigint DEFAULT 1,
"rank_on"   INTEGER NOT NULL DEFAULT 1,
PRIMARY KEY("chat_id")
)""")

# Users Table
curs.execute("""CREATE TABLE IF NOT EXISTS "users" (
"chat_id"	bigint NOT NULL,
"point"	INTEGER DEFAULT 1,
"user_id"	bigint NOT NULL,
"username"	TEXT,
"firstname"	TEXT,
"user_level"	INTEGER,
"experience"	INTEGER,
"invite_by"	INTEGER,
"start_exp"	INTEGER,
"warnings"	INTEGER,
"exp_time"	bigint,
"command_time"	bigint,
"rank_time"	bigint DEFAULT 1,
"rankuser_time"	bigint DEFAULT 1,
"is_admin" boolean DEFAULT FALSE,
PRIMARY KEY("chat_id","user_id"),
FOREIGN KEY("chat_id") REFERENCES "chats"("chat_id") ON DELETE CASCADE
)""")

db.commit()
db.close()
# end of creating a database


@bot.message_handler(commands=["start"])
def send_welcome(message):
    if not message.from_user.username:
        username = message.from_user.username
    else:
        username = message.from_user.first_name

    bot.reply_to(message, "Welcome @{}!".format(username))


@bot.message_handler(content_types=['new_chat_members'])
def new_member(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    chat_id = message.chat.id
    new_members = message.new_chat_members
    # checking new members to add for the level system and congrats
    add_new_user(database, new_members, chat_id, message)
    database.close()


@bot.message_handler(content_types=['left_chat_member'])
def member_left(message):
    user = message.left_chat_member
    if not user.is_bot:
        if user.username:
            bot.send_message(message.chat.id, "@{} aka {} just left us 😒 cya next time"
                             .format(user.username, user.first_name))
        else:
            bot.send_message(message.chat.id, "{} just left us 😒 cya next time".format(user.first_name))
    else:
        chat_id = message.chat.id
        m_id = message.message_id
        username = user.username
        bot.delete_message(chat_id, m_id)
        bot.send_message(chat_id, "~ {} Fuck off ! \nno place for BOTS ~".format(username))


# Commands Section
# Filter for plaintext commands (.help, .rules, etc.)
def filter_command(msg, command):
    return msg.text and msg.text == command and msg.chat.type == "group" or msg.chat.type == "supergroup"


# Filter for commands with parameter (.rank @username, .ban @username, etc.)
def filter_parameter_command(msg, command):
    command_len = len(command.split())
    paramter = command_len == 2
    return msg.text and msg.text.startswith(command) and paramter and \
           msg.chat.type == "group" or msg.chat.type == "supergroup"


# Filter for commands with texts parameter (.google, .config rules, etc.)
def filter_text_parameter_command(msg, command):
    return msg.text and msg.text.startswith(command) and \
           msg.chat.type == "group" or msg.chat.type == "supergroup"


@bot.message_handler(func=lambda msg: filter_command(msg, ".help"))
def help_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        if user_is_admin:
            msg = "\n_---Bot Commands---_\n" \
                  "*.help* - _Show this help 🙃_\n" \
                  "*.admins* - _Pinging the admins in the server to get help_\n" \
                  "*.rank* - _Show your current level and experience_\n" \
                  "*.rank @username* - _Shows mentioned user rank_\n" \
                  "*.ranking* - _Show top 10 players in the server_\n" \
                  "*.rules* - _Show the rules of the server_\n" \
                  "*.google <search text>* - _Ask google please._\n" \
                  "*.rank_point* - _See the top 10 most added users._\n" \
                  "_---Admin Commands---_\n" \
                  "*.warn @username* - _Warning a username, in 3 warning might be kicked!_\n" \
                  "*.ban @username * - _Ban this user from the server_\n" \
                  "*.up_point @username* - _Add a point to the user_\n" \
                  "*.down_point @username * - _Reduce point to user_\n" \
                  "*.unban @username * - _Unban the user_\n" \
                  "*.config* - _Show commands to configure the bot for the server_\n" \
                  "*Support the bot and the developer by donating, pay as you want:* [Paypal](https://paypal.me/Shepurchys)"
        else:
            msg = "\n_---Bot Commands---_\n" \
                  "*.help* - _Show this help 🙃_\n" \
                  "*.admins* - _Pinging the admins in the server to get help_\n" \
                  "*.rank* - _Show your current level and experience_\n" \
                  "*.rank @username* - _Shows mentioned user rank_\n" \
                  "*.ranking* - _Show top 10 players in the server_\n" \
                  "*.rules* - _Show the rules of the server_\n" \
                  "*.google <search text>* - _Ask google please._\n" \
                  "*.rank_point* - _See the top 10 most added users._\n" \
                  "*Support the bot and the developer by donating, pay as you want:* [Paypal](https://paypal.me/Shepurchys)"
        bot_m = bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        t1 = threading.Timer(15, bot.delete_message, args=[chat_id, bot_m.message_id])
        t2 = threading.Timer(15, bot.delete_message, args=[chat_id, message.message_id])
        t1.start()
        t2.start()
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_command(msg, ".admins"))
def admin_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_name = message.chat.title
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        admins_delay = select_query(database, "admins_delay", "chats", "chat_id", chat_id)[0]
        if not (user_is_admin or passed_time(database, user_id, chat_id, "admins_time", admins_delay)):
            return
        answer = "{} Server admins list:\n".format(chat_name)
        for admin in chat_admins:
            if admin.user.is_bot:
                continue
            if admin.user.username:
                admin_name = admin.user.username
            else:
                admin_name = admin.user.first_name
            answer += "@{}\n".format(admin_name)
        answer += "--- Admin Will Be Here Soon ---"
        bot.send_message(chat_id, answer)
        if not user_is_admin:
            set_time(database, user_id, chat_id, "admins_time", "chats")
            set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_command(msg, ".rules"))
def rules_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        rules = select_query(database, "Rules", "Chats", "chat_id", chat_id)[0]
        bot.send_message(chat_id, rules)
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)

# TODO Improve the rank algorithm
@bot.message_handler(func=lambda msg: filter_command(msg, ".rank"))
def rank_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        start_exp = select_query(database, "Start_exp", "Users", "user_id", user_id, "chat_id", chat_id)[0]
        experience = select_query(database, "Experience", "Users", "user_id", user_id, "chat_id", chat_id)[0]
        level = select_query(database, "user_level", "Users", "user_id", user_id, "chat_id", chat_id)[0]

        # calculating experience to the next level
        exp_now = experience
        exp_left = 0
        while not level < int(exp_now ** 0.25):
            exp_left += 5
            exp_now += 5
        # calculating percent and over all exp
        exp_overall = (experience + exp_left) - start_exp
        exp_percent = ((experience - start_exp) / exp_overall) * 100
        tabs = int(exp_percent / 3.3) * "="
        spaces = int(30 - int(exp_percent / 3.3)) * " "
        answer = "\n*You are level:* _{}_\n*Your experience is:* _{} / {}_\n" \
                 "*Experience to next level:* _{}_\n*Progress:* _{}%_ \n|{}{}|" \
            .format((level - 1), int(experience - start_exp), int(exp_overall),
                    exp_left, int(exp_percent), tabs, spaces)

        bot_m = bot.send_message(chat_id, answer, reply_to_message_id=message.message_id, parse_mode="Markdown")
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
        t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
        t2.start()
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_command(msg, ".config"))
def config_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if user_is_admin:
        msg = "_---Config Commands---_\n" \
              "*.config rules <text>* - _Set/change the rules of the server.(max 5000 chars)_\n" \
              "*.config rank <on/off>* - _Disable or enable the rank system of the server (default on)_\n" \
              "*.config rank <seconds>* - _Delay between each command of the user in seconds(default 15 mins)_\n" \
              "*.config rank_user <seconds>* - _Delay between each command of the user in seconds(default 15 mins)_\n" \
              "*.config ranking <seconds>* - _Delay between each command for the server in seconds(default 30 mins)_\n" \
              "*.config admins<seconds>* - _Delay between each command for the server in seconds(default 1 hour)_\n"
        bot.send_message(chat_id, msg, parse_mode="Markdown")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_command(msg, ".ranking"))
def ranking_command(message, ret=False):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_name = message.chat.title
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)

    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
        cursor = database.cursor()
        try:
            results = cursor.execute(
                "SELECT Username,Firstname,user_id,experience FROM Users WHERE chat_id = {} AND is_admin = False"
                " ORDER BY Experience DESC LIMIT 10".format(chat_id))
            results = cursor.fetchall()
        except "Error:" as e:
            results = (["{} There are no users yet".format(e)])

        ranking_msg = "<i>Top 10 Users in {} Server</i> \n<b>Ranking:</b>\n".format(chat_name)
        rank = 1

        for user in results:
            if user[0] != "None":
                username = user[0]
            else:
                username = user[1]
            exp = user[3]
            if rank == 1:
                ranking_msg += "<b>{}. {} |{}| - 🥇</b>\n".format(rank, username, exp)
                rank += 1
            elif rank == 2:
                ranking_msg += "<b>{}. {} |{}| - 🥈</b>\n".format(rank, username, exp)
                rank += 1
            elif rank == 3:
                ranking_msg += "<b>{}. {} |{}| - 🥉</b>\n".format(rank, username, exp)
                rank += 1
            else:
                ranking_msg += "{}. {} |{}| \n".format(rank, username, exp)
                rank += 1
        if ret is False:
            bot.send_message(chat_id, ranking_msg, parse_mode="HTML",
                             reply_markup=ranking_keyboard(), reply_to_message_id=message.message_id)
        else:
            return ranking_msg
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_parameter_command(msg, ".rank"))
def rank_user_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)
    # Anti Spam Mechanism
    rank_user_delay = select_query(database, "Ranking_delay", "Chats", "chat_id", chat_id)[0]
    command_passed = passed_time(database, user_id, chat_id, "Command_time", 3)
    rank_passed = passed_time(database, user_id, chat_id, "RankUser_time", rank_user_delay)
    if command_passed and rank_passed or user_is_admin:
        mentioned_user_id, mentioned_is_admin = get_mentioned(database, message, chat_id, chat_admins)
        if mentioned_user_id:
            username = select_query(database, "username", "users", "chat_id", chat_id, "user_id", mentioned_user_id)
            if username != "None":
                username = select_query(database, "firstname", "users",
                                        "chat_id", chat_id, "user_id", mentioned_user_id)[0]
            else:
                username = username[0]

            start_exp = select_query(database, "Start_exp", "Users",
                                     "user_id", mentioned_user_id, "chat_id", chat_id)[0]
            experience = select_query(database, "Experience", "Users",
                                      "user_id", mentioned_user_id, "chat_id", chat_id)[0]
            level = select_query(database, "user_level", "Users",
                                 "user_id", mentioned_user_id, "chat_id", chat_id)[0]

            # calculating experience to the next level
            exp_now = experience
            exp_left = 0
            while not level < int(exp_now ** 0.25):
                exp_left += 5
                exp_now += 5
            # calculating present and over all exp
            exp_overall = (experience + exp_left) - start_exp
            exp_present = ((experience - start_exp) / exp_overall) * 100
            tabs = int(exp_present / 3.3) * "="
            spaces = int(30 - int(exp_present / 3.3)) * " "
            answer = "\n*{}'s level is:* _{}_\n*{}'s experience is:* _{} / {}_\n" \
                     "*Experience to next level:* _{}_\n*Progress:* _{}%_ \n|{}{}|" \
                .format(username, (level - 1), username, int(experience - start_exp), int(exp_overall),
                        exp_left, int(exp_present), tabs, spaces)

            bot_m = bot.send_message(chat_id, answer, reply_to_message_id=message_id, parse_mode="Markdown")
            t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
            t1.start()
            t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message_id])
            t2.start()
            set_time(database, user_id, chat_id, "RankUser_time")
        else:
            bot_m = bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.",
                                     reply_to_message_id=message_id)
            t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
            t1.start()
            t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message_id])
            t2.start()
        if not user_is_admin:
            set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_parameter_command(msg, ".warn"))
def warn_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)
    # Anti Spam Mechanic
    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        mentioned_user_id, mentioned_is_admin = get_mentioned(database, message, chat_id, chat_admins)
        cursor = database.cursor()
        if mentioned_user_id and not mentioned_is_admin:
            username = select_query(database, "username", "users", "chat_id", chat_id, "user_id", mentioned_user_id)
            if username != "None":
                username = select_query(database, "firstname", "users",
                                        "chat_id", chat_id, "user_id", mentioned_user_id)[0]
            else:
                username = username[0]
            warnings = select_query(database, "Warnings", "Users",
                                    "user_id", mentioned_user_id, "chat_id", chat_id)[0]
            warnings += 1
            cursor.execute("UPDATE Users SET Warnings = {} WHERE chat_id = {} AND user_id = {}"
                           .format(warnings, chat_id, mentioned_user_id))
            database.commit()
            if warnings >= 3:
                msg = "{} you have <b>warned!</b>, you currently have <b>{}</b> warnings." \
                      " ADMINS consider ban this guy\n".format(username, warnings)
                bot.send_message(chat_id, msg, parse_mode="HTML")
            else:
                msg = "{} you have <b>warned!</b>, you currently have <b>{}</b> warnings." \
                    .format(username, warnings)
                bot.send_message(chat_id, msg, parse_mode="HTML")
        elif mentioned_user_id and mentioned_is_admin:
            bot.send_message(chat_id, "You can't warn an admin!",
                             reply_to_message_id=message.message_id)
        else:
            bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.",
                             reply_to_message_id=message.message_id)
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_parameter_command(msg, ".ban"))
def ban_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)
    # Anti Spam Mechanism
    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        mentioned_user_id, mentioned_is_admin = get_mentioned(database, message, chat_id, chat_admins)
        if not user_is_admin:
            bot.delete_message(chat_id, message_id)
        if user_is_admin and mentioned_is_admin:
            bot.send_message(chat_id, "You cant ban an admin :/")
        elif user_is_admin and mentioned_user_id:
            bot.kick_chat_member(chat_id, mentioned_user_id)
            reset_user_ban(message, mentioned_user_id)
        else:
            bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.")
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)


@bot.message_handler(func=lambda msg: filter_command(msg, ".example"))
def name_command(message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)

    # getting data on the Message and the Chat, (delete unused data)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    chat_admins = bot.get_chat_administrators(chat_id)

    # checking if the member who sent the message is admin
    user_is_admin = user_id in [member.id for member in chat_admins]

    # updating data in rare cases
    update_data(database, chat_id, user_id, message, user_is_admin)
    # Anti Spam Mechanism
    if passed_time(database, user_id, chat_id, "Command_time", 3) or user_is_admin:
        # Command Here
        pass
        set_time(database, user_id, chat_id, "command_time")
    else:
        bot.delete_message(chat_id, message_id)

# TODO finish transformations of all functions to handlers, and make def get_mentioned() func


"""
@bot.message_handler(func=lambda msg: msg.text is not None and msg.text[0] == "." and len(msg.text) > 2)
def on_command(message):

            # Google Help
            if message.text.startswith(".google ") and command.lower() :
                google(chat_id, message)

            # Point System
            if is_command and command.lower() == ".rank_point":
                rank_pont(chat_id, message, chat_name)
                set_time(database, user_id, chat_id, "Command_time")

            if user_is_admin and is_command and command.lower() == ".reset":
                if user_is_admin:
                    reset_point(chat_id, message)
                    set_time(database, user_id, chat_id, "Command_time")
                else:
                    bot.send_message(chat_id, "Just for an admin !")

            # ----commands with a parameter---- #
        

            # Unban command - Admins command
            unban = user_is_admin and is_para_command and str(command.split()[0].lower()) == ".unban"
            if unban:
                unban_command(message, mentioned_user_id, chat_id, user_is_admin)
                bot.delete_message(chat_id, message.message_id)
            elif is_para_command and unban:
                bot.delete_message(chat_id, message.message_id)

            # Point System
            point_up = user_is_admin and is_para_command and str(command.split()[0].lower()) == ".up_point"
            if point_up and user_is_admin:
                up_point(database, message, mentioned_user_id, chat_id)
            elif is_para_command and point_up:
                bot.delete_message(chat_id, message.message_id)

            point_down = user_is_admin and is_para_command and str(command.split()[0].lower()) == ".down_point"
            if point_down and user_is_admin:
                down_point(database, message, mentioned_user_id, chat_id)
            elif is_para_command and point_down:
                bot.delete_message(chat_id, message.message_id)



            # ----commands with multiple parameters---- #
            is_config_command = False
            config = str(command.split()[0].lower()) == ".config"
            if prefix == "." and command_len == 3 and user_is_admin and config:
                is_config_command = True

            # Config Rules command
            rules = config and command_len > 2 and str(command.split()[1].lower()) == "rules"
            if user_is_admin and rules:
                config_rules_command(database, command, chat_id)
                bot.delete_message(chat_id, message.message_id)



            # Config Rank command
            rank = is_config_command and str(command.split()[1].lower()) == "rank"
            if rank:
                config_rank_command(database, chat_id, command)

            # Config Ranking command
            ranking = is_config_command and str(command.split()[1].lower()) == "ranking"
            if ranking:
                config_delay_command(database, "Ranking_delay", chat_id, command)

            # Config rank_user command
            rank = is_config_command and str(command.split()[1].lower()) == "rank_user"
            if rank:
                config_delay_command(database, "RankUser_delay", chat_id, command)

            # Config Admins command
            admins = is_config_command and str(command.split()[1].lower()) == "admins"
            if admins:
                config_delay_command(database, "Admins_delay", chat_id, command)


        else:
            bot.delete_message(chat_id, message_id)
        database.close()
"""

"""
@bot.message_handler(func=lambda msg: msg.text is not None and '@' in msg.text)
def at_answer(message):
    texts = message.text.split()
    at_text = find_at(texts)
    page = requests.post("https://instagram.com/{}".format(at_text[1:]))
    if re.search("The link you followed may be broken, or the page may have been removed.", page.text):
        pass
    else:
        bot.reply_to(message, "https://instagram.com/{}".format(at_text[1:]))
"""


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    message = call.message
    chat_name = call.message.chat.title
    first_name = call.message.from_user.first_name
    if call.data == "cb_refresh":
        ranking = ranking_command(chat_id, message, chat_name, True)
        t1 = threading.Timer(0, refresh, [message, ranking])
        t1.start()
    elif call.data == "cb_wait_refresh":
        bot.answer_callback_query(call.id, "Wait until refresh delay done")
    elif call.data == "help":
        rules_command(chat_id, database)
        bot_m = bot.edit_message_text("Welcome to the <b>{}</b> server!~ 👻 Script Kiddo"
                                      .format(chat_name), chat_id, message_id, parse_mode="HTML")
        t1 = threading.Timer(30, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
    elif call.data == "cb_close":
        bot.delete_message(chat_id, message_id)
        try:
            bot.delete_message(chat_id, message.reply_to_message.message_id)
        except:
            pass


def refresh(message, ranking):
    timer_back = 5
    while timer_back != 0:
        try:
            bot.edit_message_text(ranking, message.chat.id, message.message_id,
                                  reply_markup=refresh_keyboard(timer_back), parse_mode="HTML")
            time.sleep(1)
            timer_back -= 1
            if timer_back == 0:
                bot.edit_message_text(ranking, message.chat.id, message.message_id,
                                      reply_markup=ranking_keyboard(), parse_mode="HTML")
        except:
            break


@bot.message_handler(content_types=["text"])
def on_message(message):
    # checking if the message is from a group
    if message.chat.type == "group" or message.chat.type == "supergroup":
        database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
        # getting data on the Message and the Chat
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        chat_id = message.chat.id
        user_is_admin = False
        chat_admins = bot.get_chat_administrators(chat_id)
        # checking if the member who sent the message is admin
        for chat_member in chat_admins:
            if chat_member.user.id == user_id:
                user_is_admin = True
        update_data(database, chat_id, user_id, message, user_is_admin)
        rank_on = select_query(database, "Rank_on", "Chats", "chat_id", chat_id)[0]

        if "t.me/" in message.text:
                if message.from_user.id != chat_admins:
                    bot.delete_message(chat_id, message.message_id)

        if message.entities:
            virus_total(message, chat_id)



        # level system
        if rank_on == 1 and passed_time(database, user_id, chat_id, "Exp_time", 60):
            update_admins(database, chat_id, chat_admins)
            set_time(database, user_id, chat_id, "Exp_time")
            add_experience(database, chat_id, user_id)
            level_up(database, chat_id, user_id, username, first_name)


def virus_total(message, chat_id):
    first_name = message.from_user.first_name
    urls = []
    for entity in message.entities:
        if entity.type == "text_link":
            urls.append(entity.url)
        elif entity.type == "url":
            urls.append(entity)


    for entity in urls:
        check = str(entity)
        if check.startswith("http"):
            url = entity
            if url.startswith("http"):
                virus_url = "https://www.virustotal.com/ui/search?query={}".format(url)
            else:
                virus_url = "https://www.virustotal.com/ui/search?query=https://{}".format(url)
            try:
                malware = int(requests.get(virus_url).json()['data'][0]['attributes']['last_analysis_stats']['malicious'])
                if malware > 0:
                    len_url = len(url)
                    half = int(len_url / 2)
                    star = "*" * half
                    bot.send_message(chat_id, "{} Sent a Bad Link - '{}{}'".format(first_name, url[:-half], star))
                    bot.delete_message(chat_id, message.message_id)
            except:
                pass
        else:
            url = message.text[entity.offset:entity.offset + entity.length]
            if url.startswith("http"):
                virus_url = "https://www.virustotal.com/ui/search?query={}".format(url)
            else:
                virus_url = "https://www.virustotal.com/ui/search?query=https://{}".format(url)
            try:
                malware = int(requests.get(virus_url).json()['data'][0]['attributes']['last_analysis_stats']['malicious'])
                if malware > 0:
                    len_url = len(url)
                    half = int(len_url / 2)
                    star = "*" * half
                    bot.send_message(chat_id, "@{} Sent a Bad Link - '{}{}'".format(first_name, url[:-half], star))
                    bot.delete_message(chat_id, message.message_id)
            except:
                pass


def unban_command(message, username_user_id, chat_id, username_is_admin):
    if username_user_id is not None:
        bot.unban_chat_member(chat_id, username_user_id)
    else:
        bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.",
                         reply_to_message_id=message.message_id)





# ---config commands---
def config_rules_command(database, command, chat_id):
    cursor = database.cursor()
    rules = command[14:]
    if "'" in rules:
        bot.send_message(chat_id, "Rules cannot included ' in it.")
    else:
        try:
            cursor.execute("UPDATE Chats SET Rules = '{}' WHERE chat_id = {}".format(rules, chat_id))
        except Exception as e:
            bot.send_message(chat_id, "Error: {}".format(e))
        database.commit()


def config_rank_command(database, chat_id, command):
    cursor = database.cursor()
    parameter = str(command.split()[2])
    if parameter.isdecimal():
        cursor.execute("UPDATE Chats SET Rank_delay = {} WHERE chat_id = {}".format(parameter, chat_id))
    elif parameter.lower() == "on":
        cursor.execute("UPDATE Chats SET Rank_on = '{}' WHERE chat_id = {}".format(1, chat_id))
    elif parameter.lower() == "off":
        cursor.execute("UPDATE Chats SET Rank_on = '{}' WHERE chat_id = {}".format(0, chat_id))
    database.commit()


def config_delay_command(database, column, chat_id, command):
    cursor = database.cursor()
    parameter = str(command.split()[2])
    if parameter.isdecimal():
        cursor.execute("UPDATE Chats SET {} = {} WHERE chat_id = {}".format(column, parameter, chat_id))
    database.commit()


# Point System
def up_point(database, message, user_id, chat_id):
    curs = database.cursor()
    username_user_id = select_query(database, "user_id", "users", "chat_id", chat_id, "user_id", user_id)
    if username_user_id:
        username_user_id = username_user_id[0]
        username = select_query(database, "username", "users", "chat_id", chat_id, "user_id", username_user_id)
        if username != "None":
            username = select_query(database, "firstname", "users", "chat_id", chat_id, "user_id", username_user_id)[0]
        else:
            username = username[0]
        point = select_query(database, "point", "users", "user_id", user_id, "chat_id", chat_id)[0]
        point += 1
        curs.execute("UPDATE users SET point = {} WHERE user_id = {} and chat_id = {}".format(point, user_id, chat_id))
        database.commit()
        bot_m = bot.send_message(chat_id, "Excellent @{} !\nYou got a point".format(username))
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
        t1.start()
        t2.start()
    else:
        bot_m = bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.",
                                 reply_to_message_id=message.message_id)
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
        t1.start()
        t2.start()


def reset_point(database, message):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    cursor = database.cursor()
    chat_id = message.chat.id
    cursor.execute("UPDATE users SET point = 0 WHERE chat_id = {}".format(chat_id))
    database.commit()
    bot_m = bot.send_message(chat_id, "Reset challenge .")
    t1 = threading.Timer(1, bot.edit_message_text, args=["Reset challenge ...", chat_id, bot_m.message_id])
    t1.start()
    t2 = threading.Timer(1, bot.edit_message_text, args=["Reset complete !", chat_id, bot_m.message_id])
    t2.start()


def reset_user_ban(message, mentioned_user_id):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    cursor = database.cursor()
    chat_id = message.chat.id
    cursor.execute("DELETE FROM users WHERE chat_id = {} and user_id = {}".format(chat_id, mentioned_user_id))
    database.commit()


def down_point(database, message, mentioned_user_id, chat_id):
    username_user_id = select_query(database, "user_id", "users", "chat_id", chat_id, "user_id", mentioned_user_id)
    if username_user_id is not None:
        username_user_id = username_user_id[0]
        username = select_query(database, "username", "users", "chat_id", chat_id, "user_id", username_user_id)
        if username != "None":
            username = select_query(database, "firstname", "users", "chat_id", chat_id, "user_id", username_user_id)[0]
        else:
            username = username[0]
        point = select_query(database, "point", "users", "user_id", mentioned_user_id, "chat_id", chat_id)[0]
        if point != 0:
            point -= 1
        curs = database.cursor()
        curs.execute(
            "UPDATE users SET point = {} WHERE user_id = {} and chat_id = {}".format(point, mentioned_user_id, chat_id))
        database.commit()
        get_point = select_query(database, "point", "users", "user_id", mentioned_user_id, "chat_id", chat_id)[0]
        if get_point < 0:
            curs.execute(
                "UPDATE users SET point = 0 WHERE user_id = {} and chat_id = {}".format(mentioned_user_id, chat_id))
            database.commit()
        bot_m = bot.send_message(chat_id, "Mmm.. @{} \nless one point".format(username))
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
        t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
        t2.start()
    else:
        bot_m = bot.send_message(chat_id, "Couldn't find this user, make sure to mention him.",
                                 reply_to_message_id=message.message_id)
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
        t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
        t2.start()


def rank_pont(chat_id, message, chat_name):
    database = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_pass, port=db_port)
    cursor = database.cursor()
    try:
        results = cursor.execute("SELECT Username,Firstname,user_id,point FROM Users WHERE chat_id = {}"
                                 " ORDER BY point DESC LIMIT 10".format(chat_id))
        results = cursor.fetchall()
    except:
        results = (["There are no users yet"])
    ranking = "<i>Top 10 Users in {} Server</i> \n<b>From the last challenge:</b>\n".format(chat_name)
    rank = 1
    for user in results:
        if user[0] != "None":
            username = user[0]
        else:
            username = user[1]
        point = user[3]
        if rank == 1:
            ranking += "<b>{}. {} |{}| - 🥇</b>\n".format(rank, username, point)
            rank += 1
        elif rank == 2:
            ranking += "<b>{}. {} |{}| - 🥈</b>\n".format(rank, username, point)
            rank += 1
        elif rank == 3:
            ranking += "<b>{}. {} |{}| - 🥉</b>\n".format(rank, username, point)
            rank += 1
        else:
            ranking += "{}. {} |{}| \n".format(rank, username, point)
            rank += 1
    bot_m = bot.send_message(chat_id, ranking, parse_mode="HTML", reply_to_message_id=message.message_id)
    t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
    t1.start()
    t2 = threading.Timer(10, bot.delete_message, args=[chat_id, message.message_id])
    t2.start()


# end of commands section
def google(chat_id, message):
    text = message.text
    query = text.replace(".google ", "")
    url = "https://lmgtfy.com/?q="
    query = query.replace(" ", "+")
    url = url + query
    bot.send_message(chat_id, "It was hard but I succeeded ..\nFor you :\n{}".format(url))


# returning message if has @ in it
def find_at(msg):
    for text in msg:
        if "@" in text:
            return text


def passed_time(database, user_id, chat_id, column, seconds, table="Users"):
    if table == "Users":
        old_time = select_query(database, column, table, "user_id", user_id, "chat_id", chat_id)[0]
    else:
        old_time = select_query(database, column, table, "chat_id", chat_id)[0]
    time_passed = int(time.time() - old_time)
    if time_passed >= seconds:
        return True
    else:
        return False


def set_time(database, user_id, chat_id, column, table="Users"):
    cursor = database.cursor()
    if table == "Users":
        cursor.execute("UPDATE {} SET {} = {} WHERE chat_id = {} AND user_id = {}"
                       .format(table, column, int(time.time()), chat_id, user_id))
    else:
        cursor.execute("UPDATE {} SET {} = {} WHERE chat_id = {}"
                       .format(table, column, int(time.time()), chat_id, user_id))
    database.commit()


def get_mentioned(database, message, chat_id, chat_admins):
    is_text_mention, is_mention, mentioned_is_admin = (False, False, False)
    mentioned_user_id, mention_length, mention_offset = (0, 0, 0)
    command = message.text
    # Checking if there is a mention in the message
    if message.entities is not None and len(message.entities) == 1:
        if message.entities[0].type == "text_mention":
            is_text_mention = True
        elif message.entities[0].type == "mention":
            is_mention = True

    if is_text_mention:
        mention_length = message.entities[0].length
        mention_offset = message.entities[0].offset
        mentioned_user_id = message.entities[0].user.id
        for chat_member in chat_admins:
            if chat_member.user.id == mentioned_user_id:
                mentioned_is_admin = True
    elif is_mention:
        username = str(command.split()[1][1:])
        mentioned_user_id, mentioned_is_admin = get_user_id(database, username, chat_id, chat_admins)

    if is_text_mention and len(command) == (mention_offset + mention_length):
        return mentioned_user_id, mentioned_is_admin
    if is_mention and mentioned_user_id:
        return mentioned_user_id, mentioned_is_admin
    return None, False


def get_user_id(database, username, chat_id, chat_admins):
    user_id = select_query(database, "user_id", "Users", "Username", username, "chat_id", chat_id)
    if user_id is not None:
        user_admin = False
        for chat_member in chat_admins:
            if chat_member.user.id == user_id[0]:
                user_admin = True
        return user_id[0], user_admin
    else:
        return None, False


def select_query(database, column, table, column_name, column_value, column_name2=None, column_value2=None):
    """
    :param database: Sqlite3 database
    :param column: a string of the selected column to get info from ( to get all columns, string should be "all").
    :param table: From which table
    :param column_name: a string of the column you want to equal to a value ( username = )
    :param column_value: the value of the column_name ( column_name = "drake")
    :param column_name2: a string Optional - adds AND option to the query to check with another column
    :param column_value2: Optional the value of column_name2
    :return: None or results
    """
    if type(column_value) == str:
        column_value = "'{}'".format(column_value)
    if type(column_value2) == str:
        column_value2 = "'{}'".format(column_value2)
    cursor = database.cursor()
    if column.lower() == "all" and column_name2 is not None and column_value2 is not None:
        cursor.execute("SELECT * FROM {} WHERE {} = {} AND {} = {}"
                       .format(table, column_name, column_value, column_name2, column_value2))
    elif column.lower() == "all" and column_name2 is None and column_value2 is None:
        cursor.execute("SELECT * FROM {} WHERE {} = {}"
                       .format(table, column_name, column_value))
    elif column_name2 is None and column_value2 is None:
        cursor.execute("SELECT {} FROM {} WHERE {} = {}"
                       .format(column, table, column_name, column_value))
    else:
        cursor.execute("SELECT {} FROM {} WHERE {} = {} AND {} = {}"
                       .format(column, table, column_name, column_value, column_name2, column_value2))
    return cursor.fetchone()


# adding exp each message the user sent.
def add_experience(database, chat_id, user_id):
    cursor = database.cursor()
    experience = random.choice([15, 20, 25, 30])
    current_experience = select_query(database, "Experience", "Users", "user_id", user_id, "chat_id", chat_id)[0]
    final_exp = int(current_experience + experience)
    cursor.execute("UPDATE Users SET Experience = {} WHERE chat_id = {} AND user_id = {}"
                   .format(final_exp, chat_id, user_id))
    database.commit()


# checking every message if the user have leveled up
def level_up(database, chat_id, user_id, username, firstname):
    cursor = database.cursor()
    experience = select_query(database, "Experience", "Users", "user_id", user_id, "chat_id", chat_id)[0]
    level = select_query(database, "user_level", "Users", "user_id", user_id, "chat_id", chat_id)[0]

    # Updating level and start of exp to make calculations  later.
    def update_info():
        cursor.execute("UPDATE Users SET user_level = {} WHERE chat_id = {} AND user_id = {}"
                       .format(level_end, chat_id, user_id))
        cursor.execute("UPDATE Users SET Start_exp = {} WHERE chat_id = {} AND user_id = {}"
                       .format(experience, chat_id, user_id))

    # Formula for how much exp needed to next level
    level_end = int(experience ** 0.25)

    # checking if he leveled up and congrats him if he has username or neither
    if level < level_end and username is not None:
        bot_m = bot.send_message(chat_id,
                                 "@{} has leveled up to level {} Congratulations 👏".format(username, (level_end - 1)))
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
        update_info()
    elif level < level_end:
        bot_m = bot.send_message(chat_id,
                                 "{} has leveled up to level {} Congratulations 👏".format(firstname, (level_end - 1)))
        t1 = threading.Timer(10, bot.delete_message, args=[chat_id, bot_m.message_id])
        t1.start()
        update_info()
    # updating every change to the database.
    database.commit()


def update_admins(database, chat_id, chat_admins):
    cursor = database.cursor()
    for admin in chat_admins:
        cursor.execute("UPDATE Users SET is_admin = True WHERE chat_id = {} AND user_id = {}"
                       .format(chat_id, admin.user.id))
    database.commit()

    cursor.execute("SELECT user_id FROM Users WHERE chat_id = {} AND is_admin = True"
                   .format(chat_id))
    saved_admins = cursor.fetchall()

    for user in saved_admins:
        is_admin = False
        for admin in chat_admins:
            if admin.user.id == user[0]:
                is_admin = True
                break
        if not is_admin:
            cursor.execute("UPDATE Users SET is_admin = False WHERE chat_id = {} AND user_id = {}"
                           .format(chat_id, user[0]))
    database.commit()


# checks if need to update the database every message
def update_data(database, chat_id, user_id, message, is_admin):
    user = message.from_user
    cursor = database.cursor()
    current_firstname = user.first_name
    if "'" in current_firstname:
        current_firstname.replace("'", '"')
    # checking if the chat is already in the database
    result = select_query(database, "all", "Chats", "chat_id", chat_id)
    if result is None:
        default_rule = "'There are no rules yet, please contact an admin to set them.'"
        # in case the chat is not inside, adding the chat
        sql = "INSERT INTO Chats(chat_id, Rules, Rank_delay, Admins_delay, RankUser_delay," \
              "Ranking_delay, Ranking_time, Admins_time, Rank_on) VALUES({},{},{},{},{},{},{},{},{})" \
            .format(chat_id, default_rule, 900, 1800, 3600, 900, 1, 1, 1)
        cursor.execute(sql)
        database.commit()

    # checking if the user is already in the database in the current chat.
    result = select_query(database, "user_id", "Users", "user_id", user_id, "chat_id", chat_id)
    if result is None:
        if not user.is_bot:
            sql = "INSERT INTO Users(chat_id, user_id, Username," \
                  "Firstname ,user_level, Experience, Start_exp, Warnings," \
                  " Exp_time, Command_time, Rank_time, RankUser_time, is_admin) " \
                  "VALUES({},{},'{}','{}',{},{},{},{},{},{},{},{},{})" \
                .format(chat_id, user.id, user.username, current_firstname, 2, 0, 0, 0, 0, 0, 0, 0, is_admin)
            cursor.execute(sql)
            database.commit()

    else:
        current_username = user.username
        username = select_query(database, "Username", "Users", "user_id", user_id, "chat_id", chat_id)[0]
        firstname = select_query(database, "Firstname", "Users", "user_id", user_id, "chat_id", chat_id)[0]
        if current_username != username:
            cursor.execute("UPDATE Users SET Username = '{}' WHERE chat_id = {} AND user_id = {}"
                           .format(current_username, chat_id, user_id))
        if current_firstname != firstname:
            cursor.execute("UPDATE Users SET Firstname = '{}' WHERE chat_id = {} AND user_id = {}"
                           .format(current_firstname, chat_id, user_id))
        cursor.execute("UPDATE Users SET is_admin = {} WHERE chat_id = {} AND user_id = {}"
                       .format(is_admin, chat_id, user_id))

        database.commit()


# when a new user joins the chat, adding him to the database.
def add_new_user(database, new_members, chat_id, message):
    cursor = database.cursor()
    user_id = message.from_user.id
    for member in new_members:
        if not member.is_bot:
            current_firstname = member.first_name
            # Anti SQL injection
            if "'" in current_firstname:
                current_firstname.replace("'", '"')

            # Checking who invited the user (if at all)
            if message.from_user.id != member.id:
                print("The user has invite by {}".format(user_id))
                up_point(database, message, user_id, chat_id)

            # checking if the chat is already in the database
            result = select_query(database, "all", "Chats", "chat_id", chat_id)
            if result is None:
                default_rule = "'There are no rules yet, please contact an admin to set them.'"
                # in case the chat is not inside, adding the chat
                sql = "INSERT INTO Chats(chat_id, Rules, Rank_delay, Admins_delay, RankUser_delay," \
                      "Ranking_delay, Ranking_time, Admins_time, Rank_on) VALUES({},{},{},{},{},{},{},{},{})" \
                    .format(chat_id, default_rule, 900, 1800, 3600, 900, 1, 1, 1)
                cursor.execute(sql)
                database.commit()

            # checking if the user is already in the database in the current chat.
            result = select_query(database, "user_id", "Users", "user_id", member.id, "chat_id", chat_id)
            if result is None:
                sql = "INSERT INTO Users(chat_id, user_id, Username," \
                      "Firstname ,user_level, Experience, Start_exp, Warnings," \
                      " Exp_time, Command_time, Rank_time, RankUser_time, invite_by) " \
                      "VALUES({},{},'{}','{}',{},{},{},{},{},{},{},{},{})" \
                    .format(chat_id, member.id, member.username, current_firstname, 2, 0, 0, 0, 0, 0, 0, 0, user_id)
                cursor.execute(sql)

                # will send a welcome message either the user have username or not.
                if member.username is not None:
                    bot_m = bot.send_message(chat_id,
                                             "@{} Welcome to the {} server!~ 🥳 Rookie! \n<i>type</i> <b>.help</b> <i>for bot commands</i>"
                                             .format(member.username, message.chat.title), parse_mode="HTML", reply_markup=help_markup())
                    t1 = threading.Timer(30, bot.delete_message, args=[chat_id, bot_m.message_id])
                    t1.start()

                else:
                    bot_m = bot.send_message(chat_id,
                                             "{} Welcome to the {} server!~ 🥳 Scr1pt Kidd0 \n<i>type</i> <b>.help</b> <i>for bot commands</i>"
                                             .format(member.first_name, message.chat.title), parse_mode="HTML", reply_markup=help_markup())
                    t1 = threading.Timer(30, bot.delete_message, args=[chat_id, bot_m.message_id])
                    t1.start()
                    t2 = threading.Timer(30, bot.delete_message, args=[chat_id, message.message_id])
                    t2.start()

            # updating the database in case that any update was made.
            database.commit()
        else:
            m_id = message.message_id
            bot_id = member.id
            bot.kick_chat_member(chat_id, bot_id)
            bot.delete_message(chat_id, m_id)


# Replay Markup Keyboards
def ranking_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="cb_refresh"),
               types.InlineKeyboardButton("❌ Close Message", callback_data="cb_close"))
    return markup


def refresh_keyboard(timer_back):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("⛔ Refresh again in {}".format(timer_back), callback_data="cb_wait_refresh"))
    markup.add(types.InlineKeyboardButton("❌ Close Message".format(timer_back), callback_data="cb_close"))
    return markup


def help_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(types.InlineKeyboardButton("rules", callback_data="help"))
    return markup


@server.route('/' + bot_token, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://telebot-penteration.herokuapp.com/" + bot_token)
    return "!", 200


if __name__ == '__main__':
    webhook()
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

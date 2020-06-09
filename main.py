import telebot
import datetime as d

import config
import funcs as f
import static
import db


bot = telebot.TeleBot(config.TG_TOKEN)
main_menu = f.create_keyboard(static.start_markup, row_width=2)


@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 'Приветик. Я пока ничего не умею, но скоро научусь!!', reply_markup=main_menu)


@bot.message_handler(func=lambda m: m.text == 'Новая задача')
def add_target(message):
    markup = f.create_keyboard(
        ['Главное меню'], row_width=1, resize_keyboard=True)
    bot.send_message(message.chat.id, 'Введите вашу задачу:',
                     reply_markup=markup)
    bot.register_next_step_handler(message, add_task_name)


def add_task_name(message):
    if message.text == 'Главное меню':
        bot.send_message(
            message.chat.id, 'Вы вернулись в главное меню', reply_markup=main_menu)
    else:
        db.Task.create(user_id=message.chat.id, task_text=message.text)
        bot.send_message(
            message.chat.id, 'Вы успешно добавили задачу в список дел', reply_markup=main_menu)


@bot.message_handler(func=lambda m: m.text == 'Список дел')
def view_todo_list(message):
    query = db.Task.select().where(db.Task.task_date == d.datetime.date(
        d.datetime.today())).where(db.Task.user_id == message.chat.id)
    tasks_selected = query.dicts().execute()

    task_dict = {}
    for task in tasks_selected:
        key = str(int(task['done'])) + '_task_' + str(task['task_id'])
        if task['done']:
            task_dict[key] = '✅ ' + task['task_text']
        else:
            task_dict[key] = '❌ ' + task['task_text']

    inline_markup = f.create_inline_keyboard(task_dict)
    bot.send_message(message.chat.id,
                     '<b>Ваш список дел на сегодня</b>\n<i>Если хотите отметить выполненную задачу, ткните в нее</i>',
                     reply_markup=inline_markup, parse_mode='html')


@bot.callback_query_handler(func=lambda q: q.data[2:6] == 'task')
def change_progress_task(query):
    sql_query = db.Task.update(done=not bool(int(query.data[0]))).where(
        db.Task.task_id == query.data[7:])
    sql_query.execute()

    query_1 = db.Task.select().where(db.Task.task_date == d.datetime.date(
        d.datetime.today())).where(db.Task.user_id == query.message.chat.id)
    tasks_selected = query_1.dicts().execute()

    task_dict = {}
    for task in tasks_selected:
        not_done = str(int(not int(query.data[0])))
        key = not_done + '_' + 'task_' + str(task['task_id'])
        if task['done']:
            task_dict[key] = '✅ ' + task['task_text']
        else:
            task_dict[key] = '❌ ' + task['task_text']

    inline_markup = f.create_inline_keyboard(task_dict)

    bot.edit_message_reply_markup(message_id=query.message.message_id,
                                  chat_id=query.message.chat.id, reply_markup=inline_markup)


@bot.message_handler(func=lambda g: True)
def idk(m):
    bot.send_message(m.chat.id, 'Я не знаю, что ответить🤷')


bot.polling()

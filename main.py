import telebot
import datetime as d

import config
import funcs as f
import static
import db


bot = telebot.TeleBot(config.TG_TOKEN)
main_menu = f.create_keyboard(static.start_markup, row_width=2, one_time_keyboard=True)


@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, f"Привет, {message.from_user.first_name}. Я пока ничего не умею, но скоро научусь!!",
        reply_markup=main_menu)
    have_user = False
    users = db.User.select().dicts().execute()
    for user in users:
        if user['user_id'] == message.chat.id:
            have_user = True

    if not have_user:
        db.User.create(user_id=message.chat.id, user_name=message.from_user.username)


@bot.message_handler(func=lambda m: m.text == 'q')
def q(message):
    pass
    # users = db.User.select()
    # users_selected = users.dicts().execute()[0]
    # print(users_selected)
    # print(message.from_user)


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
    try:
        user = db.User.get(user_id=message.chat.id)
        if user.last_target_list:
            bot.edit_message_text('Вы открыли новый список дел', message.chat.id, user.last_target_list + 1)
            # bot.delete_message(message.chat.id, user.last_target_list + 1)
    except telebot.apihelper.ApiException:
        pass
    user.last_target_list = message.message_id
    user.save()

    query = db.Task.select().where(db.Task.task_date == d.datetime.date(
        d.datetime.today())).where(db.Task.user_id == message.chat.id)
    tasks_selected = query.dicts().execute()
    if len(tasks_selected) == 0:
        inline_keyboard_new_task = f.create_inline_keyboard({'new_task': 'Добавить задачу'})
        bot.send_message(
            message.chat.id, '<b>Ваш список дел пуст 🤦‍♂️</b>',
            parse_mode='html', reply_markup=inline_keyboard_new_task)

    else:
        task_dict = {}
        for task in tasks_selected:
            key = 'task_' + str(task['task_id'])
            if task['done']:
                task_dict[key] = '✅ ' + task['task_text']
            else:
                task_dict[key] = '❌ ' + task['task_text']

        inline_markup = f.create_inline_keyboard(task_dict)
        bot.send_message(message.chat.id,
                         '<strong>Ваш список дел на сегодня</strong>\n'
                         '<i>Если хотите отметить развернуть задачу, ткните в нее</i>',
                         reply_markup=inline_markup, parse_mode='html')


@bot.callback_query_handler(func=lambda q: q.data[:4] == 'task')
def open_task(query):
    sql_query = db.Task.select().where(db.Task.task_id == query.data[5:])
    try:
        new_task = sql_query.dicts().execute()[0]
        if new_task['done']:
            status = '✅'
        else:
            status = '❌'

        changed_dict = {}
        for key in static.inline_dict.keys():
            new_key = key + '_' + str(new_task['task_id'])
            changed_dict[new_key] = static.inline_dict[key]

        inline_keyboard = f.create_inline_keyboard(changed_dict, row_width=2)
        date_format = str(new_task['task_date'])[-2:] + '.' + str(new_task['task_date'])[5:7] + '.'\
                     + str(new_task['task_date'])[:4]
        mess_text = status + ' <b>' + new_task['task_text'] + '</b> ' + status + \
            '\n---------------------------------\n' + f"<i>Запланировано на: {date_format}</i>" \
                    + '\n---------------------------------\n' + str(new_task['task_desc'])
        bot.edit_message_text(mess_text, query.message.chat.id,
                              query.message.message_id, parse_mode='html', reply_markup=inline_keyboard)

    except IndexError:
        bot.send_message(query.message.chat.id, 'Похоже вы уже удалили эту задачу')
        view_todo_list(query.message)
        bot.delete_message(query.message.chat.id, query.message.message_id)


@bot.callback_query_handler(func=lambda q: q.data[:4] == 'done')
def change_progress_task(query):
    try:
        sql_query = db.Task.select().where(db.Task.task_id == query.data[5:])
        new_task = sql_query.dicts().execute()[0]

        sql_query = db.Task.update(done=not new_task['done']).where(db.Task.task_id == query.data[5:])
        sql_query.execute()

        if not new_task['done']:
            status = '✅'
        else:
            status = '❌'

        changed_dict = {}
        for key in static.inline_dict.keys():
            new_key = key + '_' + str(new_task['task_id'])
            changed_dict[new_key] = static.inline_dict[key]
        # date_format = str(new_task['task_date'])[-2:] + '.' + str(new_task['task_date'])[5:7] + '.' \
        #               + str(new_task['task_date'])[:4]
        date_format = f"{new_task['task_date'].day}.{new_task['task_date'].month}.{new_task['task_date'].year}"
        inline_keyboard = f.create_inline_keyboard(changed_dict, row_width=2)
        mess_text = status + ' <b>' + new_task['task_text'] + '</b> ' + status + \
                    '\n---------------------------------\n' + f"<i>Запланировано на: {date_format}</i>" \
                    + '\n---------------------------------\n' + str(new_task['task_desc'])
        bot.edit_message_text(mess_text, query.message.chat.id, reply_markup=inline_keyboard,
                              message_id=query.message.message_id, parse_mode='html')

    except IndexError:
        bot.send_message(query.message.chat.id, 'Похоже вы уже удалили эту задачу')
        view_todo_list(query.message)
        bot.delete_message(query.message.chat.id, query.message.message_id)


@bot.callback_query_handler(func=lambda q: q.data[:6] == 'delete')
def delete_task(query):
    task = db.Task.get(db.Task.task_id == query.data[7:])
    task.delete_instance()
    bot.edit_message_text('Вы удалили задачу', message_id=query.message.message_id, chat_id=query.message.chat.id)
    view_todo_list(query.message)


@bot.callback_query_handler(func=lambda q: q.data == 'new_task')
def new_task_callback(query):
    bot.delete_message(query.message.chat.id, query.message.message_id)
    add_target(query.message)


@bot.callback_query_handler(func=lambda q: q.data[:4] == 'desc')
def change_desc(query):
    bot.send_message(query.message.chat.id, 'Введите новое описание')
    bot.register_next_step_handler(query.message, edit_task_desc, query)


def edit_task_desc(message, query):
    task = db.Task.update(task_desc=message.text).where(db.Task.task_id == query.data[5:])
    task.execute()
    bot.delete_message(query.message.chat.id, query.message.message_id)
    bot.send_message(message.chat.id, 'Вы изменили описание')


@bot.message_handler(func=lambda m: m.text == 'Команды')
def team(message):
    # Открыть базу данных, посмотреть юзеров в команде и вывести их списком
    query = db.GroupMember.select().where(db.GroupMember.UserID == message.chat.id)
    list_of_groups = list(query.execute())
    print(list_of_groups)
    markup = f.create_inline_keyboard({'join': 'Добавить команду'})
    bot.send_message(message.chat.id, 'Вот ваши команды', reply_markup=markup)


@bot.callback_query_handler(func=lambda q: q.data == 'join')
def join(query):
    bot.send_message(query.message.chat.id, 'Пришлите индефикатор группы')
    bot.register_next_step_handler(query.message, scan_unique_id)


def scan_unique_id(message):
    query = db.Group.select().where(db.Group.unique_id == message.text)
    group = query.execute()
    if len(list(group)):
        group = group[0]
        try:
            group_member = db.GroupMember.create(UserID=message.chat.id, group_id=group.group_id)
        except Exception as Error:
            bot.send_message(message.chat.id, 'Вы уже есть в этой группе')

    else:
        bot.send_message(message.chat.id, 'Группы с таким индентификатором не существует')


@bot.message_handler(func=lambda m: m.text == 'Создать команду')
def write_team_name(message):
    bot.send_message(message.chat.id, 'Введите название команды')
    bot.register_next_step_handler(message, create_team)


def create_team(message):
    created_group_id = db.Group.create(name=message.text, unique_id='Еще не готово')
    db.GroupMember.create(UserID=message.chat.id, group_id=created_group_id.group_id)
    unique_id = f.generator_id(created_group_id, 10)
    updated_unique_id = db.Group.update(unique_id=unique_id).where(db.Group.group_id == created_group_id)
    updated_unique_id.execute()
    bot.send_message(message.chat.id, f'Вот ваш уникальный идентификатор: {created_group_id.unique_id}')


# @bot.callback_query_handler(func=lambda q: True)
# def huynya(q):
#     print(q.data)


bot.polling()

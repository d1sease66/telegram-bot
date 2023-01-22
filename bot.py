import datetime
import random
import typing
import os

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData

from sheets import service, spreadsheet_id

API_TOKEN = '5680438074:AAFuOaELOXB34t2EmBVhfl7kf-l0EWuHxUQ'
ORDERS = '@orders_endvr'

CATEGORIES_LIST = ['Кроссовки', 'Одежда', 'Аксессуары', 'Техника']
SIZE_LIST = ['до 1 кг', 'около 1 кг', 'до 2 кг']

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

vote_cb = CallbackData('dun_w', 'action', 'order_id')
DICT_WITH_YOUR_ORDER = {}


class UserState(StatesGroup):
    category = State()
    size = State()
    price = State()
    link = State()
    weight = State()


def get_order_info(order_info):
    request = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=["Лист1", "Лист2"]
    ).execute()
    value_ranges = request['valueRanges'][0]
    all_values = value_ranges['values'][1:]
    orders = types.InlineKeyboardMarkup(row_width=3)
    text = ''
    for value in all_values:
        if order_info in value:
            text = md.text(
                md.text('Номер заказа:', value[0]),
                md.text('Категория:', value[2]),
                   md.text('Вес:', value[3]),
                   md.text('Размер/Комплектация:', value[4]),
                   md.text('Артикул/Ссылка:', value[5]),
                   md.text('Сумма:', f'{value[6]} рублей'),
                   md.text('Статус:', value[7]),
                   md.text('Дата:', value[8]),
                   sep='\n'
            )
    return text


def get_payment_data(your_order_id):
    request = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=["Лист1", "Лист2"]
    ).execute()
    value_ranges = request['valueRanges'][0]
    all_values = value_ranges['values'][1:]
    orders = types.InlineKeyboardMarkup(row_width=3)
    text = ''
    for value in all_values:
        if your_order_id in value:
            return value[7]


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    DICT_WITH_YOUR_ORDER.clear()
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    make_order = types.InlineKeyboardButton('Сделать заказ', callback_data=vote_cb.new(order_id='-', action='Сделать заказ'))
    check_order = types.InlineKeyboardButton('Проверить статус заказа',
                                             callback_data=vote_cb.new(order_id='-', action='Проверить статус заказа'))
    link = types.InlineKeyboardButton('Поддержка', url='https://t.me/rupak0v')
    feedback = types.InlineKeyboardButton('Отзывы', url='https://t.me/endvr_feedback')
    channel = types.InlineKeyboardButton('Канал в телеграмме', url='https://t.me/endvr_logistics')
    inline_markup.add(make_order, check_order, link, feedback, channel)
    await bot.send_message(message.chat.id, 'Привет, это бот компании ENVDR. Через меня вы можете оформить заказ '
                                            'или посмотреть статус уже оформленных заказов ',
                           reply_markup=inline_markup)


@dp.callback_query_handler(vote_cb.filter(action='Отменить заказ'))
@dp.callback_query_handler(vote_cb.filter(action='Главное меню'))
async def send_welcome_command(query: types.CallbackQuery, callback_data: typing.Dict[str, str], state: FSMContext):
    DICT_WITH_YOUR_ORDER.clear()
    await state.finish()
    callback_data_action = callback_data['action']
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    make_order = types.InlineKeyboardButton('Сделать заказ', callback_data=vote_cb.new(order_id='-', action='Сделать заказ'))
    check_order = types.InlineKeyboardButton(
        'Проверить статус заказа',
        callback_data=vote_cb.new(order_id='-', action='Проверить статус заказа')
    )
    link = types.InlineKeyboardButton('Поддержка', url='https://t.me/rupak0v')
    feedback = types.InlineKeyboardButton('Отзывы', url='https://t.me/endvr_feedback')
    channel = types.InlineKeyboardButton('Канал в телеграмме', url='https://t.me/endvr_logistics')
    inline_markup.add(make_order, check_order, link, feedback, channel)
    await bot.edit_message_text(
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        text='Здравствуйте! Это ENVDR бот для заказа вещей с Poizon. Что вам нужно?',
        reply_markup=inline_markup
    )


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply(
        'Заказ был отменен. Для того, чтобы открыть меню введите -  /start',
        reply_markup=types.ReplyKeyboardRemove())


@dp.callback_query_handler(vote_cb.filter(action='Сделать заказ'))
async def make_order(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    action = callback_data['action']
    if action == 'Сделать заказ':
        choose_category_markup = types.InlineKeyboardMarkup(row_width=2)
        sneakers_mk = types.InlineKeyboardButton('Кроссовки', callback_data=vote_cb.new(order_id='-', action='Кроссовки'))
        it_mk = types.InlineKeyboardButton('Техника', callback_data=vote_cb.new(order_id='-', action='Техника'))
        clothes_mk = types.InlineKeyboardButton('Одежда', callback_data=vote_cb.new(order_id='-', action='Одежда'))
        acc = types.InlineKeyboardButton('Аксессуары', callback_data=vote_cb.new(order_id='-', action='Аксессуары'))
        other = types.InlineKeyboardButton('Другое', callback_data=vote_cb.new(order_id='-', action='Другое'))
        main_menu = types.InlineKeyboardButton('Главное меню', callback_data=vote_cb.new(order_id='-', action='Главное меню'))
        choose_category_markup.add(sneakers_mk, it_mk, clothes_mk, acc, other, main_menu)
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text='Выберите категорию товара',
            reply_markup=choose_category_markup
        )


@dp.callback_query_handler(vote_cb.filter(action=['Проверить статус заказа', 'Назад']))
async def check_orders(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    CORRECT_VALUES = []
    request = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=["Лист1", "Лист2"]
    ).execute()
    value_ranges = request['valueRanges'][0]
    all_values = value_ranges['values'][1:]
    orders = types.InlineKeyboardMarkup(row_width=3)
    for value in all_values:
        if f'@{query.from_user.username}' in value:
            CORRECT_VALUES.append(f'Товар с артикулом: {value[4]}. Статус: {value[7]}')
            orders.add(types.InlineKeyboardButton(
                f'Заказ: {value[0]}. Статус: {value[7]}',
                callback_data=vote_cb.new(order_id=value[0], action=f'Открыть заказ'))
            )
    orders.add(types.InlineKeyboardButton('Главное меню', callback_data=vote_cb.new(order_id='-', action='Главное меню')))
    if len(CORRECT_VALUES) != 0:
        if len(CORRECT_VALUES) == 1:
            text = f'У вас оформлен {len(CORRECT_VALUES)} заказ'
        elif 1 < len(CORRECT_VALUES) < 5:
            text = f'У вас оформлено {len(CORRECT_VALUES)} заказа'
        else:
            text = f'У вас оформлено {len(CORRECT_VALUES)} заказов'
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=orders
        )
    else:
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text='У вас нет заказов',
            reply_markup=orders
        )


@dp.callback_query_handler(vote_cb.filter(action='Открыть заказ'))
async def choose_order_info(query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs):
    action = callback_data['action']
    order_id = callback_data['order_id']
    text = get_order_info(order_id)
    inline_markup_2 = types.InlineKeyboardMarkup()
    back = types.InlineKeyboardButton('<<Назад', callback_data=vote_cb.new(order_id='-', action='Назад'))
    inline_markup_2.add(back)
    if action == 'Открыть заказ':
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=inline_markup_2,
            parse_mode=ParseMode.HTML,
        )


@dp.callback_query_handler(vote_cb.filter(action='Другое'))
async def check_the_right_price(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    await query.answer()
    callback_data_action = callback_data['action']
    if callback_data_action == 'Другое':
        inline_markup_2 = types.InlineKeyboardMarkup()
        main_menu = types.InlineKeyboardButton('Главное меню', callback_data=vote_cb.new(order_id='-',action='Главное меню'))
        link = types.InlineKeyboardButton('Поддержка', url='https://t.me/rupak0v')
        inline_markup_2.add(main_menu, link)
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text="К сожалению бот не предусмотрел заказ вещей этой категории((. Обратитесь пожалуйста в нашу поддержку.",
            reply_markup=inline_markup_2
        )


@dp.callback_query_handler(vote_cb.filter(action=['Кроссовки', 'Одежда', 'Аксессуары', 'Техника']))
async def input_title(query: types.CallbackQuery, callback_data: typing.Dict[str, str],state: FSMContext):
    await query.answer()
    action = callback_data['action']
    await UserState.category.set()
    await state.update_data(category=action)
    if action in CATEGORIES_LIST:
        if action == 'Кроссовки' or action == 'Одежда' or action == 'Аксессуары':
            text = 'Укажите нужный размер для вашего товара и цвет, если представлено несколько позиций'
        else:
            text = 'Укажите нужную комплектацию для вашего товара и цвет, если представлено несколько позиций'
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text=text,
        )
    await UserState.next()


@dp.message_handler(state=UserState.size)
async def input_price(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    DICT_WITH_YOUR_ORDER['size'] = message.text
    await message.reply(
        text='Укажите цену для товара в юанях.',
    )
    await UserState.next()


@dp.message_handler(lambda message: not message.text.isdigit(), state=UserState.price)
async def check_the_right_price(message: types.Message):
    await bot.delete_message(message.chat.id, message.message_id)
    return await bot.send_message(message.chat.id, "Введите целое число")


@dp.message_handler(state=UserState.price)
async def input_article(message: types.Message, state: FSMContext):
    await state.update_data(price=int(message.text))
    DICT_WITH_YOUR_ORDER['price'] = message.text
    await message.reply(
        text='Укажите ссылку/артикул нужного вам товара.',
    )
    await UserState.next()


@dp.message_handler(state=UserState.link)
async def main(message: types.Message, state: FSMContext):
    global new_price
    global order_id
    global category
    global weight
    global link
    global size
    await state.update_data(link=message.text)
    async with state.proxy() as data:
        if data['category'] == 'Кроссовки':
            data['weight'] = 'около 1 кг'
        elif data['category'] == 'Одежда' or data['category'] == 'Аксессуары':
            data['weight'] = 'до 1 кг'
        elif data['category'] == 'Техника':
            data['weight'] = 'до 2 кг'

        if data['weight'] == 'около 1 кг':
            new_price = int(data['price'] * 11.15 + 600)
        elif data['weight'] == 'до 1 кг':
            new_price = int(data['price'] * 11.15 + 500)
        elif data['weight'] == 'до 2 кг':
            new_price = int(data['price'] * 11.15 + 1000)
        else:
            new_price = 'Нет цены'
        category = data['category']
        weight = data['weight']
        size = data['size']
        link = data['link']
        markup = types.InlineKeyboardMarkup()
        order_id = random.randint(1005, 40000)
        markup.row(types.InlineKeyboardButton('Оплатить товар', callback_data=vote_cb.new(order_id='-', action='Оплатить товар')))
        markup.row(types.InlineKeyboardButton('Отменить заказ', callback_data=vote_cb.new(order_id='-', action='Отменить заказ')))
        await bot.send_message(
            message.chat.id,
            text=md.text(
                md.text('Номер заказа:', order_id),
                md.text('Категория:', data['category']),
                md.text('Вес:', data['weight']),
                md.text('Размер/Комплектация:', data['size']),
                md.text('Артикул/Cсылка:', data['weight']),
                md.text('Итоговая цена:', new_price),
                sep='\n',
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )
    await state.finish()


@dp.callback_query_handler(vote_cb.filter(action='Оплатить товар'))
async def buy(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    inline_markup_2 = types.InlineKeyboardMarkup()
    payment_check = types.InlineKeyboardButton('Проверить оплату', callback_data=vote_cb.new(order_id=order_id, action='Проверить оплату') )
    inline_markup_2.add(payment_check)
    await bot.edit_message_text(
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        text=f'Ваш заказ создан! Для оплаты вам нужно перевести сумму в размере {new_price} по номеру карты: \n\n'
             f'5536914016830832 - тинькофф \n'
             f'2202205022502600 - сбер \n\n'
             f'После оплаты нажмите на кнопку "Проверить оплату"',
        parse_mode=ParseMode.HTML,
        reply_markup=inline_markup_2
    )
    date = datetime.datetime.today()
    await bot.send_message(
        ORDERS,
        md.text(
            md.text('Номер заказа:', order_id),
            md.text('Пользователь:', f'@{query.from_user.username}'),
            md.text('Категория:', category),
            md.text('Вес:', weight),
            md.text('Размер/Комплектация:', size),
            md.text('Артикул/Ссылка:', link),
            md.text('Сумма:', f'{new_price} рублей'),
            md.text('Дата:', date.strftime("%m/%d/%Y")),
            sep='\n'
        ),
        parse_mode=ParseMode.HTML,
    )
    values = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range='Лист1!A2',
        valueInputOption="RAW",
        body={
            "values": [
                [
                    order_id,
                    f'@{query.from_user.username}',
                    category,
                    weight,
                    size,
                    link,
                    new_price,
                    'Создан',
                    date.strftime("%m/%d/%Y")
                ],
            ]
        }
    ).execute()


@dp.callback_query_handler(vote_cb.filter(action='Проверить оплату'))
async def check_payment(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    your_order_id = callback_data['order_id']
    if get_payment_data(your_order_id) == 'Подтвержден':
        inline_markup_2 = types.InlineKeyboardMarkup()
        main_menu = types.InlineKeyboardButton(
            'Главное меню',
            callback_data=vote_cb.new(order_id='-', action='Главное меню')
        )
        inline_markup_2.add(main_menu)
        await bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            text=f'Вы успешно оплатили заказ!'
                 f'Посмотреть статус заказа вы можете в главном меню бота.'
                 f'В случае проблем с заказом, наша поддержка с вами свяжется',
            parse_mode=ParseMode.HTML,
            reply_markup=inline_markup_2
        )
    else:
        await query.answer('Оплата еще не была подтверждена', show_alert=True)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)

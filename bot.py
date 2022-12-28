import datetime

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ContentType
from aiogram.utils import executor

from sheets import service, spreadsheet_id

API_TOKEN = '5680438074:AAFuOaELOXB34t2EmBVhfl7kf-l0EWuHxUQ'
PAYMENTS_TOKEN = '1744374395:TEST:1d216a48d9848d11c825'
ORDERS = '@orders_endvr'


CATEGORIES_LIST = ['Кроссовки', 'Одежда', 'Аксессуары', 'Техника']
SIZE_LIST = ['до 1 кг', 'около 1 кг', 'до 2 кг']

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)


class Form(StatesGroup):
    category = State()
    size = State()
    price = State()
    article = State()
    weight = State()
    buy = State()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    markup = types.ReplyKeyboardMarkup()
    make_order = types.KeyboardButton('Сделать заказ')
    check_order = types.KeyboardButton('Проверить статус заказа')
    markup.add(make_order, check_order)
    await bot.send_message(message.chat.id, 'Здравствуйте! Это ENVDR бот. Что вам нужно?', reply_markup=markup)


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):

    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply(
        'Заказ был отменен. Для того, чтобы открыть меню введите -  /start',
        reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(content_types=['text'])
async def choose_order(message: types.Message):
    if message.text == 'Сделать заказ':
        markup = types.ReplyKeyboardMarkup()
        sneakers_mk = types.KeyboardButton('Кроссовки')
        it_mk = types.KeyboardButton('Техника')
        clothes_mk = types.KeyboardButton('Одежда')
        acc = types.KeyboardButton('Аксессуары')
        markup.add(sneakers_mk, it_mk, clothes_mk, acc)
        await bot.send_message(message.chat.id, 'Выберите категорию товара', reply_markup=markup)
        await Form.category.set()
    elif message.text == 'Проверить статус заказа':
        CORRECT_VALUES = []
        request = service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id, ranges=["Лист1", "Лист2"]
        ).execute()
        value_ranges = request['valueRanges'][0]
        all_values = value_ranges['values'][1:]
        for value in all_values:
            if f'@{message.from_user.username}' in value:
                CORRECT_VALUES.append(f'Товар с артикулом: {value[4]}. Статус {value[6]}')
        if len(CORRECT_VALUES) != 0:
            await bot.send_message(message.chat.id, f'У вас оформлено {len(CORRECT_VALUES)} заказа')
            for msg in CORRECT_VALUES:
                await bot.send_message(message.chat.id, msg)
        else:
            await bot.send_message(message.chat.id, 'У вас нет заказов')
    else:
        await bot.send_message(message.chat.id, 'Не понимаю вас')


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: message.text not in CATEGORIES_LIST, state=Form.category)
async def check_the_right_price(message: types.Message):
    return await message.reply("Выберите верную категорию")


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: message.text in CATEGORIES_LIST, state=Form.category)
async def input_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['category'] = message.text
    await Form.next()
    markup = types.ReplyKeyboardRemove()
    await message.reply(
        'Укажите размер товара для одежды и кроссовок.'
        'Для техники и всего остального напишите нужную комплектацию. '
        'Если нет, то просто отправьте "-"',
        reply_markup=markup
    )


@dp.message_handler(content_types=['text'])
@dp.message_handler(state=Form.size)
async def input_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['size'] = message.text
    await Form.next()
    await message.reply('Укажите цену в юанях за нужный вам размер:')


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.price)
async def check_the_right_price(message: types.Message):
    return await message.reply("Введите целое число")


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: message.text.isdigit(), state=Form.price)
async def input_article(message: types.Message, state: FSMContext):
    await Form.next()
    await state.update_data(price=int(message.text))
    await bot.send_photo(
        message.chat.id,
        open('photo.jpg', 'rb'),
        caption=(
            'Укажите артикул товара (На фото показано, где вы можете найти его)'
        ),
    )


@dp.message_handler(content_types=['text'])
@dp.message_handler(state=Form.article)
async def input_weight(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['article'] = message.text
    await Form.next()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    if data['category'] == 'Кроссовки':
        markup.add('около 1 кг')
    elif data['category'] == 'Одежда' or data['category'] == 'Аксессуары':
        markup.add('до 1 кг')
    elif data['category'] == 'Техника':
        markup.add('до 2 кг')
    await message.reply('Выберите вес товара', reply_markup=markup)


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: message.text not in SIZE_LIST, state=Form.weight)
async def check_the_right_price(message: types.Message):
    return await message.reply("Выберите размер, предложенный в меню")


@dp.message_handler(content_types=['text'])
@dp.message_handler(lambda message: message.text in SIZE_LIST, state=Form.weight)
async def main(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['weight'] = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add('Оплатить товар')
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Категория:', data['category']),
                md.text('Вес:', data['weight']),
                md.text('Размер/Комплектация:', data['size']),
                md.text('Артикул:', data['article']),
                sep='\n',
            ),
            parse_mode=ParseMode.HTML,
        )
        if data['weight'] == 'около 1 кг':
            new_price = int(data['price'] * 10.6 + 600)
        elif data['weight'] == 'до 1 кг':
            new_price = int(data['price'] * 10.6 + 500)
        elif data['weight'] == 'до 2 кг':
            new_price = int(data['price'] * 10.6 + 1000)
        else:
            new_price = 'Нет цены'
        await bot.send_message(
            message.chat.id,
            f'Итоговая цена: {new_price}. Для отмены заказа введите команду /cancel',
            reply_markup=markup
        )
    await Form.next()
    global PRICE
    PRICE = types.LabeledPrice(label='Оплата вашей пары', amount=new_price * 100)


@dp.message_handler(state=Form.buy)
async def buy(message: types.Message, state: FSMContext,):
    async with state.proxy() as data:
        data['buy'] = message.text
        markup = types.ReplyKeyboardRemove()
        if PAYMENTS_TOKEN.split(':')[1] == 'TEST':
            await bot.send_message(message.chat.id, 'Тестовый платеж', reply_markup=markup)
        await bot.send_invoice(message.chat.id,
                               title=f'Оплата вашей пары - {data["article"]}',
                               description='-',
                               provider_token=PAYMENTS_TOKEN,
                               currency='rub',
                               is_flexible=False,
                               prices=[PRICE],
                               start_parameter='pay_for_your_item',
                               payload='test_invoice_payload'
                               )
    await Form.next()


@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def message_to_orders_chat(message: types.Message, state: FSMContext):
    await bot.send_message(
        message.chat.id,
        f'Вам платеж на сумму {message.successful_payment.total_amount // 100} прошел успешно!'
    )
    async with state.proxy() as data:
        date = datetime.datetime.today()
        await bot.send_message(
            ORDERS,
            md.text(
                md.text('Пользователь:', f'@{message.from_user.username}'),
                md.text('Категория:', data['category']),
                md.text('Вес:', data['weight']),
                md.text('Размер/Комплектация:', data['size']),
                md.text('Артикул:', data['article']),
                md.text('Сумма:', f'{message.successful_payment.total_amount // 100} рублей'),
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
                        f'@{message.from_user.username}',
                        data['category'],
                        data['weight'],
                        data['size'],
                        data['article'],
                        message.successful_payment.total_amount // 100,
                        'Принят',
                        date.strftime("%m/%d/%Y")
                    ],
                ]
            }
        ).execute()
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)

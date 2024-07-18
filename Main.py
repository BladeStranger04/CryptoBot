import telebot
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
import io
import time

# Токен бота
API_TOKEN = 'token'

bot = telebot.TeleBot(API_TOKEN)
matplotlib.use('agg')

# Флаг Скриннера
screener = False

# Список криптовалют, которые будут отображаться в боте
crypto_list = [
    {'name': 'Bitcoin', 'ticker': 'BTCUSDT'},
    {'name': 'Ethereum', 'ticker': 'ETHUSDT'},
    {'name': 'Binance Coin', 'ticker': 'BNBUSDT'},
    {'name': 'Cardano', 'ticker': 'ADAUSDT'},
    {'name': 'Dogecoin', 'ticker': 'DOGEUSDT'},
    {'name': 'Polkadot', 'ticker': 'DOTUSDT'},
    {'name': 'Chainlink', 'ticker': 'LINKUSDT'},
    {'name': 'Litecoin', 'ticker': 'LTCUSDT'},
    {'name': 'Ripple', 'ticker': 'XRPUSDT'},
]

# Словарь данных о криптовалюте, которые будут отображаться в боте
crypto_data = {}

# Функция для мониторинга криптовалют
def monitor_crypto(message):
    global screener

    # Если флаг Screener = True, то начинаем мониторинг
    if screener:
        for crypto in crypto_list:
            # Получаем текущий курс криптовалюты из словаря crypto_data
            current_rate = crypto_data[crypto['ticker']]['close'].iloc[-1]
            # Обновляем данные по криптовалюте
            update_crypto_data(crypto['ticker'])
            # Получаем новый курс криптовалюты
            new_rate = crypto_data[crypto['ticker']]['close'].iloc[-1]
            # Если курс изменился, отправляем сообщение
            if new_rate != current_rate:
                change = round(((new_rate - current_rate) / current_rate) * 100, 2)
                if change >= 0:
                    change = "+" + str(change)
                text = f"{crypto['name']}: {new_rate} ({change}% change)"
                bot.send_message(chat_id=message.chat.id, text=text)
    # Если флаг Screener = False, то ничего не делаем
    else:
        pass

# Добавляем таймер для мониторинга каждую минуту
def monitor_schedule(message):
    while True:
        monitor_crypto(message)
        time.sleep(60)

# Функция для получения данных по криптовалюте
def get_crypto_data(ticker, interval='1d', limit='6'):
    url = f'https://api.binance.com/api/v3/klines?symbol={ticker}&interval={interval}&limit={limit}'
    response = requests.get(url)
    raw_data = response.json()
    df = pd.DataFrame(raw_data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                         'quote_asset_volume', 'number_of_trades', 'last_price',
                                         'taker_buy_quote_asset_volume', 'unknown'])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    df['open'] = pd.to_numeric(df['open'])
    df['close'] = pd.to_numeric(df['close'])
    return df


# Функция для обновления данных по криптовалюте
def update_crypto_data(ticker):
    crypto_data[ticker] = get_crypto_data(ticker)

# Функция для создания кнопок с именованием криптовалют
def create_crypto_buttons():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3)
    buttons = []
    for crypto in crypto_list:
        buttons.append(telebot.types.KeyboardButton(crypto['name']))
    buttons.append(telebot.types.KeyboardButton('Choose Mode'))
    markup.add(*buttons)
    return markup

# Функция для создания кнопок выбора режима
def create_mode_buttons():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
    buttons = [telebot.types.KeyboardButton("CurrencyTracker"), telebot.types.KeyboardButton("Screener")]
    markup.add(*buttons)
    return markup

# Приветствие бота
@bot.message_handler(commands=['start'])
def send_hello(message):
    response = "Hello, I am a bot that can output cryptocurrency rates and track market changes." \
               "\nAll information is taken from Binance website."
    bot.send_message(message.chat.id, response, reply_markup=create_mode_buttons())

# Добавляем обработчик для отлова всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global screener

    # Режим для вывода курса криптовалют
    if message.text == "CurrencyTracker":
        screener = False
        bot.send_message(message.chat.id, "Mode: CurrencyTracker", reply_markup=create_crypto_buttons())
    # Режим для сканирования рынка
    elif message.text == "Screener":
        screener = True
        monitor_schedule(message)
        bot.send_message(message.chat.id, "Mode: Screener")
    # Выбор режима бота
    elif message.text == "Choose Mode":
        screener = False
        bot.send_message(message.chat.id, "Let's switch mode!", reply_markup=create_mode_buttons())
    # Выводим курс крипты
    else:
        for crypto in crypto_list:
            if message.text == crypto['name']:
                update_crypto_data(crypto['ticker'])
                current_crypto_data = crypto_data[crypto['ticker']]
                # Получаем данные за последние 6 дней
                last_6_days_data = current_crypto_data[current_crypto_data['open_time'] > datetime.now() - timedelta(days=7)]
                # Рисуем график изменения курса
                plt.plot(last_6_days_data['open_time'], last_6_days_data['open'])
                plt.title(f'{crypto["name"]} rate for the last 6 days')
                plt.xlabel('Date')
                plt.ylabel('Rate, USD')
                # Сохраняем график в буфер обмена
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                # Отправляем изображение и текущий курс
                bot.send_photo(message.chat.id, photo=buffer.getvalue())
                dollar = '💵'
                bot.send_message(message.chat.id, f'{crypto["name"]} - {current_crypto_data.iloc[-1]["close"]:.2f} USD ' + dollar * 3)
                # Очищаем график для следующего вывода
                plt.clf()
                # Выходим из цикла после отправки сообщения
                break

if name == 'main':
    # Загружаем информацию о криптовалюте
    for crypto in crypto_list:
        update_crypto_data(crypto['ticker'])

    # Запускаем бота
    bot.polling()

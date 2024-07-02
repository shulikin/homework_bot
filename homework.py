"""
Telegram-бот отслеживает статус домашней работы.

Обращается к API сервис Практикум Домашка и передаёт статус..
"""

import logging
import os
import sys
import time
from http import HTTPStatus

import urllib.error
import requests
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(funcName)s - [%(levelname)s] - %(message)s'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

FIRST_REGISTRATION = 1709251200
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """
    Проверяем доступность переменных.

    Переменные необходимы для работы программы.
    """
    return all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])


def send_message(bot, message):
    """
    Отправляем сообщение в Telegram-чат.

    Обработка ошибок, запись лога.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(f'Не удалось отправить сообщение {error}')


def get_api_answer(timestamp):
    """
    Запрос к сервису - Практикум API.

    Ожидаем ответ (status_code).
    """
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        message = f'Практикум API недоступен: {error}'
        raise ConnectionError(message)
    if response.status_code != HTTPStatus.OK:
        raise urllib.error.HTTPError
    try:
        response_json = response.json()
    except ValueError as error:
        message = f'Ответ сервера не преобразовываться в JSON: {error}'
        raise ValueError(message)
    return response_json


def check_response(response: dict) -> list:
    """
    Проверяем ответ на соответствие требованиям.

    Параметра функции - ответ API, приведённый к типам данных.
    """
    if not isinstance(response, dict):
        message = 'Ответ API не является словарем'
        raise TypeError(message)
    homeworks = response.get('homeworks')
    if homeworks is None:
        message = 'В ответе API ключ <homeworks> не найден'
        raise KeyError(message)
    if not isinstance(homeworks, list):
        message = 'В <homeworks> неверный тип данных'
        raise TypeError(message)
    return homeworks


def parse_status(homework: dict) -> str:
    """
    Информация о домашней работе.

    Возвращаем из словаря HOMEWORK_VERDICTS <status>
    для отправки в Telegram.
    """
    if 'homework_name' not in homework:
        message_error = 'В словаре нет ключа <homework_name>'
        raise KeyError(message_error)
    else:
        homework_name = homework.get('homework_name')
    if 'status' not in homework:
        message_error = 'В словаре нет ключа <status>'
        raise KeyError(message_error)
    else:
        homework_verdict = homework.get('status')
    if homework_verdict not in HOMEWORK_VERDICTS:
        message_error = f'Статус работы не определен: <{homework_verdict}>'
        raise KeyError(message_error)
    logging.info('Статус работы обновлен.')
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{HOMEWORK_VERDICTS[homework_verdict]}')


def main():
    """Основная логика работы бота."""
    old_message = None
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_date = FIRST_REGISTRATION
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения')
        sys.exit('Продолжать работу бота нет смысла...')

    while True:
        try:
            response = get_api_answer(current_date)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                new_message = f'Статус домашней работы {status}'
                logger.debug(new_message)

            else:
                new_message = 'Статус домашней работы не изменился'
                logger.debug(new_message)
        except Exception as error:
            new_message = f'Сбой в работе программы: {error}'
            logging.error({error})

        if old_message != new_message:
            send_message(bot, new_message)
        old_message = new_message
        current_date = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

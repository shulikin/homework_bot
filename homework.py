import logging
import os
import sys
import time
from http import HTTPStatus

import telebot.apihelper
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

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
# ENDPOINT = ''
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
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.info(f'Ответ на запрос API: {response.status_code}')
        if response.status_code != HTTPStatus.OK:
            raise response.raise_for_status()
    except Exception as error:
        message = f'Практикум API недоступен: {error}'
        logger.error(message)
        raise Exception(message)
    return response.json()


def check_response(response: dict) -> list:
    """
    Проверяем ответ на соответствие требованиям.

    Параметра функции - ответ API, приведённый к типам данных.
    """
    if not isinstance(response, dict):
        message = 'Ответ API не является словарем'
        logger.error(message)
        raise TypeError(message)
    homeworks = response.get('homeworks')
    if homeworks is None:
        message = 'В ответе API ключ <homeworks> не найден'
        logger.error(message)
        raise KeyError(message)
    if not isinstance(homeworks, list):
        message = 'В <homeworks> неверный тип данных'
        logger.error(message)
        raise TypeError(message)
    return homeworks


def parse_status(homework: dict) -> str:
    """
    Информация о домашней работе.

    Возвращаем из словаря HOMEWORK_VERDICTS <status>
    для отправки в Telegram.
    """
    print(homework)
    homework_name = homework.get('homework_name')
    homework_verdict = homework.get('status')
    if not homework_name:
        message = f'Пустое значение по ключу {homework_name}'
        logger.error(message)
        raise KeyError(message)
    if homework_verdict not in HOMEWORK_VERDICTS:
        message = f'Статус домашней работы не определен.{homework_verdict}'
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS[homework_verdict]
    logging.info('Статус проверки работы обновлен.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения')
        sys.exit('Продолжать работу бота нет смысла...')

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                send_message(bot, status)
            else:
                logger.debug('Статус домашней работы не изменился')
        except telebot.apihelper.ApiTelegramException:
            logging.error('Ошибка отправки сообщения в Telegram')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

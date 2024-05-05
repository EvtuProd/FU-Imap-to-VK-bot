import imaplib
import email
from email.header import decode_header
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import json
import logging
import os
import time
import base64  # Добавим импорт модуля base64

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Функция для декодирования base64
def decode_base64(encoded_string):
    encoded_string += '=' * (4 - len(encoded_string) % 4)
    decoded_bytes = base64.b64decode(encoded_string)
    return decoded_bytes.decode('utf-8')

# Функция для отправки сообщения в беседу ВКонтакте
def send_vk_message(sender_name, sender_email, subject, body, attachments, vk):
    # ID беседы, куда вы хотите отправить сообщение
    peer_id = 2000000001

    # Составляем текст сообщения
    message_text = f"От: {sender_name}:{sender_email}\nТема: {subject}\nТело: {body}"

    # Добавляем метку о наличии вложений, если они есть
    if attachments:
        message_text += "\n\n**В сообщении есть вложения. Пожалуйста, зайдите в почтовый клиент, чтобы их просмотреть.**"

    # Отправляем сообщение в беседу ВКонтакте
    vk.messages.send(
        random_id='0',
        peer_id=peer_id,
        message=message_text
    )
    logging.info(f'Отправлено сообщение в беседу VK: {message_text}')

# Функция для обработки писем
def process_emails(email_username, email_password, vk_token):
    while True:
        try:
            # Подключаемся к серверу почты
            logging.info('Подключение к серверу почты...')
            mail = imaplib.IMAP4_SSL('imap.yandex.ru')
            mail.login(email_username, email_password)

            # Выбираем ящик с почтой (inbox)
            logging.info('Выбор ящика с почтой (inbox)...')
            mail.select('inbox')

            # Ищем непрочитанные сообщения
            logging.info('Поиск непрочитанных сообщений...')
            result, data = mail.search(None, 'UNSEEN')

            # Инициализируем сессию ВКонтакте с помощью токена
            vk_session = vk_api.VkApi(token=vk_token)
            vk = vk_session.get_api()

            # Обрабатываем найденные сообщения
            for num in data[0].split():
                # Получаем данные сообщения
                logging.info(f'Получение данных сообщения {num}...')
                result, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]

                # Преобразуем данные в объект письма
                email_message = email.message_from_bytes(raw_email)

                sender_name, sender_email = email.utils.parseaddr(email_message['From'])

                # Раскодируем имя отправителя, если оно закодировано
                sender_name = sender_name.replace('=?UTF-8?B?', '')
                sender_name = sender_name.replace('==?=', '')
                sender_name = sender_name.replace(' ', '')
                sender_name = decode_base64(sender_name)

                # Декодируем тему письма
                subject_bytes, subject_encoding = decode_header(email_message['Subject'])[0]
                subject_decoded = subject_bytes.decode(subject_encoding)

                # Печатаем текст письма, если он есть
                if email_message.is_multipart():
                    attachments = []
                    for part in email_message.walk():
                        content_disposition = str(part.get("Content-Disposition"))
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                # Декодируем имя файла, если оно закодировано
                                filename = decode_header(filename)[0][0]
                                if isinstance(filename, bytes):
                                    # Если имя файла было закодировано в байтах, декодируем его в строку UTF-8
                                    filename = filename.decode('utf-8')
                                # Сохраняем вложение на диск
                                folder_name = "attachments"
                                if not os.path.isdir(folder_name):
                                    os.mkdir(folder_name)
                                filepath = os.path.join(folder_name, filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                attachments.append(filepath)

                        elif "text/plain" in part.get_content_type():
                            # Декодируем и получаем текст письма
                            body = part.get_payload(decode=True).decode()

                    # Отправляем сообщение в беседу ВКонтакте
                    send_vk_message(sender_name, sender_email, subject_decoded, body, attachments, vk)
        except Exception as e:
            logging.error(f'Ошибка при обработке писем: {e}')
            # Отправляем уведомление об ошибке в ВКонтакте
            send_vk_message('Система', 'system@example.com', 'Ошибка при обработке писем', f'Произошла ошибка при обработке писем: {e}', [], vk)
        finally:
            # Закрываем соединение
            logging.info('Закрытие соединения с сервером почты...')
            mail.logout()

        # Добавляем паузу перед следующей проверкой почты, чтобы не нагружать сервер
        time.sleep(5)  # Проверяем почту каждую минуту

# Загружаем логин, пароль и токен из файла JSON
with open('config.json', 'r') as f:
    config = json.load(f)

mail_username = config.get('email_credentials', {}).get('username', '')
mail_password = config.get('email_credentials', {}).get('password', '')
vk_token = config.get('vk_credentials', {}).get('token', '')

process_emails(mail_username, mail_password, vk_token)

import imaplib
import email
from email.header import decode_header
import base64
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import json

# Функция для декодирования base64
def decode_base64(encoded_string):
    encoded_string += '=' * (4 - len(encoded_string) % 4)
    decoded_bytes = base64.b64decode(encoded_string)
    return decoded_bytes.decode('utf-8')

# Функция для отправки сообщения в беседу ВКонтакте
def send_vk_message(sender_name, sender_email, subject, body, vk):
    # ID беседы, куда вы хотите отправить сообщение
    peer_id = 2000000001

    # Составляем текст сообщения
    message_text = f"От: {sender_name}:{sender_email}\nТема: {subject}\nТело: {body}"

    # Отправляем сообщение в беседу
    vk.messages.send(
        random_id='0',
        peer_id=peer_id,
        message=message_text
    )

# Функция для обработки писем
def process_emails(mail_username, mail_password, vk_token):
    # Подключаемся к серверу почты
    mail = imaplib.IMAP4_SSL('imap.yandex.ru')
    mail.login(mail_username, mail_password)

    # Выбираем ящик с почтой (inbox)
    mail.select('inbox')

    # Ищем непрочитанные сообщения
    result, data = mail.search(None, 'UNSEEN')

    # Инициализируем сессию ВКонтакте с помощью токена
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()

    # Обрабатываем найденные сообщения
    for num in data[0].split():
        # Получаем данные сообщения
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
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Ищем текстовую часть письма
                if "text/plain" in content_type:
                    # Декодируем и получаем текст письма
                    body = part.get_payload(decode=True).decode()

                    # Отправляем сообщение в беседу ВКонтакте
                    send_vk_message(sender_name, sender_email, subject_decoded, body, vk)

    # Закрываем соединение
    mail.close()
    mail.logout()

# Загружаем логин, пароль и токен из файла JSON
with open('config.json', 'r') as f:
    config = json.load(f)

mail_username = config.get('mail_username', '')
mail_password = config.get('mail_password', '')
vk_token = config.get('vk_token', '')

# Бесконечный цикл для постоянного мониторинга почты
while True:
    process_emails(mail_username, mail_password, vk_token)

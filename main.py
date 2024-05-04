import imaplib
import email
from email.header import decode_header
import email.utils
import base64

def decode_base64(encoded_string):
    # Добавляем недостающие символы
    encoded_string += '=' * (4 - len(encoded_string) % 4)
    # Декодируем из base64
    decoded_bytes = base64.b64decode(encoded_string)
    # Возвращаем декодированный текст
    return decoded_bytes.decode('utf-8')

def process_emails():
    # Подключаемся к серверу почты
    mail = imaplib.IMAP4_SSL('imap.yandex.ru')
    mail.login('tuhachewscky@yandex.ru','nivlqlsojzdjepyv')

    # Выбираем ящик с почтой (inbox)
    mail.select('inbox')

    # Ищем непрочитанные сообщения
    result, data = mail.search(None, 'UNSEEN')

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

        # Теперь можно обработать письмо
        # Например, распечатать его заголовок
        print('From:', sender_name, ':', sender_email, 'Subject:', email_message['Subject'])

        # Печатаем текст письма, если он есть
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Ищем текстовую часть письма
                if "text/plain" in content_type:
                    # Декодируем и печатаем текст
                    body = part.get_payload(decode=True).decode()
                    print("Message Body:", body)


    # Закрываем соединение
    mail.close()
    mail.logout()

# Бесконечный цикл для постоянного мониторинга почты
while True:
    process_emails()
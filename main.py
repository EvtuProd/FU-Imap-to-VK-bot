import imaplib
import email
from email.header import decode_header
import vk_api
import json
import logging
import os
import time
import base64

# Creating a formatter for logging
class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.ERROR: '\033[91m',  # red
        logging.WARNING: '\033[93m',  # yellow
        logging.INFO: '\033[92m',  # green
    }
    ENDCOLOR = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, '\033[0m')  # default color reset
        log_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        log_fmt = super().format(record)
        return f"{log_time} - {log_color}{log_fmt}{self.ENDCOLOR}"

# Creating and configuring a handler for console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())

# Adding the handler to the root logger
logging.root.addHandler(console_handler)

# Disabling colored output for the root logger (as it will be handled by the formatter)
logging.root.setLevel(logging.NOTSET)

# Function to decode base64
def decode_base64(encoded_string):
    encoded_string += '=' * (4 - len(encoded_string) % 4)
    decoded_bytes = base64.b64decode(encoded_string)
    return decoded_bytes.decode('utf-8')

# Function to send a message to a VK conversation
def send_vk_message(sender_name, sender_email, subject, body, attachments, vk):
    # Conversation ID where you want to send the message
    peer_id = 2000000001

    # Composing the message text
    message_text = f"From: {sender_name}:{sender_email}\nSubject: {subject}\nBody: {body}"

    # Adding a note about attachments if there are any
    if attachments:
        message_text += "\n\n**The message contains attachments. Please check your email client to view them.**"

    # Sending the message to the VK conversation
    try:
        vk.messages.send(
            random_id='0',
            peer_id=peer_id,
            message=message_text
        )
        logging.WARNING(f'Message sent to VK conversation: {message_text}')
    except Exception as e:
        logging.error(f'Error sending message to VK conversation: {e}')

# Function to process emails
def process_emails(email_username, email_password, vk_token):
    while True:
        try:
            # Connecting to the mail server
            logging.info('Connecting to the mail server...')
            mail = imaplib.IMAP4_SSL('imap.yandex.ru')
            mail.login(email_username, email_password)

            # Selecting the mailbox (inbox)
            logging.info('Selecting the mailbox (inbox)...')
            mail.select('inbox')

            # Searching for unread messages
            logging.info('Searching for unread messages...')
            result, data = mail.search(None, 'UNSEEN')

            # Initializing VK session using the token
            vk_session = vk_api.VkApi(token=vk_token)
            vk = vk_session.get_api()

            # Processing the found messages
            for num in data[0].split():
                # Getting message data
                logging.info(f'Getting data for message {num}...')
                result, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]

                # Converting data to email object
                email_message = email.message_from_bytes(raw_email)

                sender_name, sender_email = email.utils.parseaddr(email_message['From'])

                # Decoding sender name if encoded
                sender_name = sender_name.replace('=?UTF-8?B?', '')
                sender_name = sender_name.replace('==?=', '')
                sender_name = sender_name.replace(' ', '')
                sender_name = decode_base64(sender_name)

                # Decoding email subject
                subject_bytes, subject_encoding = decode_header(email_message['Subject'])[0]
                subject_decoded = subject_bytes.decode(subject_encoding)

                # Printing email text if available
                if email_message.is_multipart():
                    attachments = []
                    for part in email_message.walk():
                        content_disposition = str(part.get("Content-Disposition"))
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                # Decoding filename if encoded
                                filename = decode_header(filename)[0][0]
                                if isinstance(filename, bytes):
                                    # If filename was encoded in bytes, decode it to UTF-8 string
                                    filename = filename.decode('utf-8')
                                # Saving attachment to disk
                                folder_name = "attachments"
                                if not os.path.isdir(folder_name):
                                    os.mkdir(folder_name)
                                filepath = os.path.join(folder_name, filename)
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                attachments.append(filepath)

                        elif "text/plain" in part.get_content_type():
                            # Decoding and getting email text
                            body = part.get_payload(decode=True).decode()

                    # Sending message to VK conversation
                    send_vk_message(sender_name, sender_email, subject_decoded, body, attachments, vk)
        except Exception as e:
            logging.error(f'Error processing emails: {e}')
        finally:
            # Closing the connection
            try:
                mail.logout()
            except Exception as e:
                logging.error(f'Error closing connection to mail server: {e}')

        # Adding a pause before the next email check to avoid overloading the server
        time.sleep(60)  # Check email every minute

# Loading login, password, and token from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

mail_username = config.get('email_credentials', {}).get('username', '')
mail_password = config.get('email_credentials', {}).get('password', '')
vk_token = config.get('vk_credentials', {}).get('token', '')

process_emails(mail_username, mail_password, vk_token)

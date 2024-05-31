import imaplib
import email
from email.header import decode_header
import vk_api
import json
import logging
import os
import time
import base64
import threading
from imapclient import imap_utf7

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

# Creating and configuring a handler for file output
log_filename = 'bot.log'
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Adding the file handler to the root logger
logging.root.addHandler(file_handler)

# Setting the level for the file handler
logging.root.setLevel(logging.NOTSET)
file_handler.setLevel(logging.INFO)

# Function to decode base64
def decode_base64(encoded_string):
    encoded_string += '=' * (4 - len(encoded_string) % 4)
    decoded_bytes = base64.b64decode(encoded_string)
    return decoded_bytes.decode('utf-8')

# Function to send a message to a VK conversation
def send_vk_message(sender_name, sender_email, subject, body, attachments, folder_name, vk):
    # Conversation ID where you want to send the message
    peer_id = 2000000001

    # Composing the message text
    message_text = f"Folder: {folder_name}\nFrom: {sender_name}:{sender_email}\nSubject: {subject}\nBody: {body}"

    # Adding a note about attachments if there are any
    if attachments:
        message_text += "\n\n**The message contains attachments. Please check your email client to view them.**"

    # Sending the message to the VK conversation
    try:
        vk.messages.send(
            random_id=0,
            peer_id=peer_id,
            message=message_text
        )
        logging.warning(f'Message sent to VK conversation: {message_text}')
    except Exception as e:
        logging.error(f'Error sending message to VK conversation: {e}')

# Function to process emails
def process_emails(email_username, email_password, vk_token):
    folders = ["inbox", "Джава", "Линукс", "МЛ", "СУБД", "ТеорияАлгоритмов", "ЭкономикаМММММ", "Эксель"]

    while True:
        try:
            # Connecting to the mail server
            logging.info('\n')
            logging.info('Connecting to the mail server...')

            mail = imaplib.IMAP4_SSL('imap.mail.ru')
            mail.login(email_username, email_password)

            # Initializing VK session using the token
            vk_session = vk_api.VkApi(token=vk_token)
            vk = vk_session.get_api()

            for folder in folders:
                try:
                    # Encode folder name to UTF-7
                    folder_utf7 = imap_utf7.encode(folder)

                    # Selecting the mailbox (folder)
                    logging.info(f'Selecting the mailbox ({folder})...')
                    status, data = mail.select(folder_utf7)
                    if status != 'OK':
                        raise Exception(f'Failed to select mailbox: {folder}')

                    # Searching for unread messages
                    logging.info('Searching for unread messages...')
                    result, data = mail.search(None, 'UNSEEN')

                    # Processing the found messages
                    for num in data[0].split():
                        try:
                            # Getting message data
                            logging.info(f'Getting data for message {num}...')
                            result, data = mail.fetch(num, '(RFC822)')
                            raw_email = data[0][1]

                            # Converting data to email object
                            email_message = email.message_from_bytes(raw_email)

                            sender_name, sender_email = email.utils.parseaddr(email_message['From'])

                            # Decoding sender name if encoded
                            sender_name = sender_name.replace('=?UTF-8?B?', '').replace('==?=', '').replace(' ', '')
                            try:
                                sender_name = decode_base64(sender_name)
                            except Exception as e:
                                logging.error(f"Error decoding sender name: {e}")
                                sender_name = "Unknown"

                            # Decoding email subject
                            subject_bytes, subject_encoding = decode_header(email_message['Subject'])[0]
                            try:
                                subject_decoded = subject_bytes.decode(subject_encoding)
                            except Exception as e:
                                logging.error(f"Error decoding subject: {e}")
                                subject_decoded = "No subject"

                            # Extracting email body and attachments
                            body = ""
                            attachments = []
                            if email_message.is_multipart():
                                for part in email_message.walk():
                                    content_disposition = str(part.get("Content-Disposition"))
                                    if "attachment" in content_disposition:
                                        filename = part.get_filename()
                                        if filename:
                                            # Decoding filename if encoded
                                            filename = decode_header(filename)[0][0]
                                            if isinstance(filename, bytes):
                                                filename = filename.decode('utf-8')
                                            # Saving attachment to disk
                                            folder_name = "attachments"
                                            if not os.path.isdir(folder_name):
                                                os.mkdir(folder_name)
                                            filepath = os.path.join(folder_name, filename)
                                            with open(filepath, "wb") as f:
                                                f.write(part.get_payload(decode=True))
                                            attachments.append(filepath)
                                    elif part.get_content_type() == "text/plain":
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                        except Exception as e:
                                            logging.error(f"Error decoding email body: {e}")
                                            body = "Error decoding email body"
                            else:
                                body = email_message.get_payload(decode=True).decode()

                            # Sending message to VK conversation
                            send_vk_message(sender_name, sender_email, subject_decoded, body, attachments, folder, vk)

                        except Exception as e:
                            logging.error(f'Error processing message {num} in folder {folder}: {e}')
                except Exception as e:
                    logging.error(f'Error processing folder {folder}: {e}')
        except Exception as e:
            logging.error(f'Error processing emails: {e}')
        finally:
            # Closing the connection
            try:
                mail.logout()
            except Exception as e:
                logging.error(f'Error closing connection to mail server: {e}')

        # Adding a pause before the next email check to avoid overloading the server
        logging.info("Waiting for the next email check...")
        time.sleep(10)  # Check email every 10 seconds

# Function to clear log file daily
def clear_log_file():
    while True:
        logging.info("Clearing log file...")
        with open(log_filename, 'w'):
            pass
        time.sleep(24 * 60 * 60)  # Clear log file every 24 hours

# Loading login, password, and token from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

mail_username = config.get('email_credentials', {}).get('username', '')
mail_password = config.get('email_credentials', {}).get('password', '')
vk_token = config.get('vk_credentials', {}).get('token', '')

# Start a separate thread for clearing log file
threading.Thread(target=clear_log_file, daemon=True).start()

# Start processing emails
process_emails(mail_username, mail_password, vk_token)

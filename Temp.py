import requests
import time

# Замените на свой токен сообщества
token = 'vk1.a.XiC0RNsF6u5lB-XCJyeSUosB-Lj4DigHUSNEWhmE-8BJ5t6O5gjLr6FHDv4YJE9x0THPQQLHLbnyAmugS2-4kHy_DbpI-vCDuEfRGcAvi_f_IwB6ySnlZAFT9WC7_ZEA4gUX8JsEZC7vdHhbThwLQkmASIPmmWAgLsmGTSWA2nToyNKhV1El6bOwPhXHlLcVEzhJyrXacj3y21-2NqtSkw'

def get_long_poll_server():
    response = requests.get('https://api.vk.com/method/groups.getLongPollServer', params={'group_id': '225795546', 'access_token': token, 'v': '5.131'})
    data = response.json()
    if 'response' in data:
        data = data['response']
        return data['server'], data['key'], data['ts']
    else:
        print("Ошибка получения Long Poll сервера:", data)
        return None, None, None


def long_poll():
    server, key, ts = get_long_poll_server()
    while True:
        try:
            response = requests.get(f'{server}?act=a_check&key={key}&ts={ts}&wait=25')
            updates = response.json()
            if 'failed' in updates:
                if updates['failed'] == 1:
                    ts = updates['ts']
                else:
                    server, key, ts = get_long_poll_server()
            else:
                ts = updates['ts']
                for update in updates['updates']:
                    print(update)  # Вывод информации о полученном обновлении
        except Exception as e:
            print("Ошибка при получении обновлений:", e)
            time.sleep(1)

if __name__ == "__main__":
    long_poll()

import urllib.parse
import argparse
import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


URL = f'{os.getenv("BASE_URL")}/auth'
HASH_FILE = 'magic_link.json'


def generate_link(base_url, token):
    params = {'token': token}

    parsed_url = urllib.parse.urlparse(base_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    for key, value in params.items():
        query_params[key] = [str(value)]

    new_query = urllib.parse.urlencode(query_params, doseq=True)
    parsed_url = parsed_url._replace(query=new_query)

    return urllib.parse.urlunparse(parsed_url)


def save_hash(token):
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as file:
            data = json.load(file)
    else:
        data = []

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(minutes=2)
    
    data.insert(0, {
        'hash': token_hash,
        'expires_at': expires_at.strftime('%d.%m.%Y %H:%M:%S'),
        'is_used': False
    })

    with open(HASH_FILE, 'w') as file:
        json.dump(data, file)


def main():
    parser = argparse.ArgumentParser(
        description='Генерация защищенной ссылки с токеном')
    parser.add_argument('--url', default=URL,
                        help='Базовый URL для генерации ссылки')

    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    link = generate_link(args.url, token)

    print("=" * 60)
    print("Сгенерированная ссылка:")
    print(link)
    print('Токен:')
    print(token)
    print("=" * 60)

    save_hash(token)


if __name__ == '__main__':
    main()

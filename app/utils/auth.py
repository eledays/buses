import os
from datetime import datetime
from functools import wraps
import hashlib
import json
from traceback import print_exc

from flask import redirect, session



def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authorized"):
            return redirect('login')
        return view(*args, **kwargs)

    return wrapped


def check_ml_token(filename, token) -> bool:
    if not os.path.exists(filename):
        return False

    now = datetime.now()
    token_hash_original = hashlib.sha256(token.encode()).hexdigest()
    found = False

    try:
        with open(filename, 'r') as file:
            lines = json.load(file)

        for line in lines:
            expires_at = line.get('expires_at')
            is_used = line.get('is_used', True)
            token_hash = line.get('hash')

            if not expires_at or not token_hash or is_used:
                if token_hash == token_hash_original:
                    break
                else:
                    continue

            expires_at = datetime.strptime(
                expires_at, '%d.%m.%Y %H:%M:%S')

            if expires_at < now:
                if token_hash == token_hash_original:
                    break
                else:
                    continue

            if token_hash_original == token_hash:
                line['is_used'] = True
                found = True
                break

        if found:
            with open(filename, 'w') as file:
                json.dump(lines, file)

        return found

    except:
        print_exc()
        return False

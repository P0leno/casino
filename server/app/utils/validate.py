import hmac
import hashlib
from urllib.parse import parse_qs

def validate_init_data(init_data: str, bot_token: str) -> bool:
    try:
        parsed = parse_qs(init_data)
        hash_value = parsed.get('hash', [''])[0]
        
        if not hash_value:
            return False
        
        data_check_string = '\n'.join([f'{k}={v[0]}' for k, v in sorted(parsed.items()) if k != 'hash'])
        secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(hash_value, calculated_hash)
    except Exception:
        return False

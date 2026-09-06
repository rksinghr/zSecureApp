# rate_limit.py
import hashlib
from django.core.cache import cache

def hash_identifier(value):
    return hashlib.sha256(
        value.encode()
    ).hexdigest()

def allow_request(prefix, identifier, limit, period):
    identifier = hash_identifier(identifier)
    key = f"rate:{prefix}:{identifier}"
    current = cache.get(key)

    if current is None:
        cache.set(key, 1, period)
        return True

    if current >= limit:
        return False

    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, period)

    return True


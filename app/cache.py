import time

from app.config import CACHE_TTL_SECONDS

# Maps a key to (time saved, value), for example "octocat" -> (1759500000.0, [...])
_cache = {}


def get_cached(key):
    """Return the saved value if it is still fresh, otherwise None."""
    entry = _cache.get(key)

    if entry is None:
        return None

    saved_at, value = entry
    age = time.time() - saved_at

    if age > CACHE_TTL_SECONDS:
        del _cache[key]
        return None

    return value


def set_cached(key, value):
    """Save a value along with the current time."""
    _cache[key] = (time.time(), value)

def clear_cache():
    """Remove everything from the cache. Mainly useful for tests."""
    _cache.clear()
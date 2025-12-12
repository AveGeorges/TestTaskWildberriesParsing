import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache")


def _get_key(prefix, *args):
    parts = [str(a) for a in args]
    data = f"{prefix}:{':'.join(parts)}"
    return hashlib.md5(data.encode()).hexdigest()


def get_cached(key):
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def set_cached(key, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


def clear_cache():
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    logger.info(f"Очищено {count} файлов кэша")
    return count

get_cache_key = _get_key

"""Local, bounded feature journal. Callers pass measurements, never message contents."""
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler

VERSION = '4.1.0'
logger = logging.getLogger('andrea.features')
logger.propagate = False
logger.addHandler(logging.NullHandler())


def configure(root):
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(root / 'features.jsonl', maxBytes=2**20,
                                      backupCount=3, encoding='utf-8')
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def event(component, action, **fields):
    logger.info(json.dumps(dict(time=datetime.datetime.now().astimezone().isoformat(timespec='milliseconds'),
                                version=VERSION, component=component, action=action, **fields), ensure_ascii=False))


def measured(component):
    """Record outcomes and latency; don't persist arguments, results or exception text."""
    from functools import wraps
    from time import perf_counter
    def decorate(method):
        @wraps(method)
        def call(*args, **kwargs):
            started = perf_counter()
            try:
                result = method(*args, **kwargs)
            except Exception as exc:
                event(component, method.__name__, outcome='error', error=type(exc).__name__)
                raise
            meta = {}
            if type(result) is bool: meta['decision'] = result
            elif isinstance(result, (list, tuple, str)): meta['result_size'] = len(result)
            event(component, method.__name__, outcome='ok', ms=round((perf_counter()-started)*1000,2), **meta)
            return result
        return call
    return decorate

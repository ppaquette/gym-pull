import logging
import sys

logger = logging.getLogger(__name__)

def utf8(value):
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

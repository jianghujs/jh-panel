import time
import re
import json



def parseTime(value, default=0, formats=None):
    try:
        value = str(value or '').strip()
        if value == '':
            return default

        if formats is None:
            formats = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S')

        for fmt in formats:
            try:
                return int(time.mktime(time.strptime(value, fmt)))
            except Exception:
                pass

        return int(float(value))
    except Exception:
        return default


def safeInt(value, default=0):
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except Exception:
        return default


def boundedInt(value, default=0, min_value=None, max_value=None):
    result = safeInt(value, default)
    if min_value is not None and result < min_value:
        result = min_value
    if max_value is not None and result > max_value:
        result = max_value
    return result


def safeFloat(value, default=0.0):
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def safeBool(value, default=False):
    try:
        if value in (1, True, "1", "true", "True", "yes", "YES", "on", "ON"):
            return True
        if value in (0, False, "0", "false", "False", "no", "NO", "off", "OFF"):
            return False
        return default
    except Exception:
        return default


def parsePercent(value, default=0.0):
    try:
        raw = str(value or '').strip().replace('%', '')
        if raw == '':
            return default
        return round(safeFloat(raw, default), 2)
    except Exception:
        return default


def parseSizeToBytes(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(float(value))

        raw = str(value).strip()
        if raw == '':
            return default

        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)?$', raw)
        if not match:
            return safeInt(raw, default)

        number = safeFloat(match.group(1), 0)
        unit = str(match.group(2) or 'B').upper()
        unit_map = {
            'B': 1,
            'K': 1024,
            'KB': 1024,
            'M': 1024 ** 2,
            'MB': 1024 ** 2,
            'G': 1024 ** 3,
            'GB': 1024 ** 3,
            'T': 1024 ** 4,
            'TB': 1024 ** 4,
            'P': 1024 ** 5,
            'PB': 1024 ** 5
        }
        return int(number * unit_map.get(unit, 1))
    except Exception:
        return default


def safeJsonText(value, default=None):
    try:
        if default is None:
            default = {}
        if value is None or value == '':
            return json.dumps(default)
        if isinstance(value, (dict, list, int, float, bool)):
            return json.dumps(value)
        return str(value)
    except Exception:
        return json.dumps(default if default is not None else {})


def shortText(value, limit=2000):
    text = str(value or '').replace('\x00', '').strip()
    limit = boundedInt(limit, 2000, 1, None)
    if len(text) > limit:
        return text[-limit:]
    return text


def parseHostStatus(value, default='Stopped'):
    try:
        status = str(value or '').strip().lower()
        if status == 'running':
            return 'Running'
        return default
    except Exception:
        return default


def escapeHtml(value):
    text = str(value or '')
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def quotePgIdentifier(name):
    return '"' + str(name).replace('"', '""') + '"'


def quotePgLiteral(value):
    return "'" + str(value).replace("'", "''") + "'"


def getNested(data, path, default=None):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    if current is None:
        return default
    return current

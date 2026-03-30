from __future__ import annotations

import re
from typing import Dict, List, Optional, Union

import pandas as pd

__all__ = [
    'get_city_name_from_file_name',
    'get_city_name_hebrew',
    'get_alert_key',
]


CITY_NAME_HEBREW_MAP = {
    'Ariel': 'אריאל',
    'Ashdod': 'אשדוד',
    'Ashkelon': 'אשקלון',
    'BatYam': 'בת ים',
    'BeerSheva': 'באר שבע',
    'BetShemesh': 'בית שמש',
    'BneiBrak': 'בני ברק',
    'Eilat': 'אילת',
    'Haifa': 'חיפה',
    'Hedera': 'חדרה',
    'Hertzeliya': 'הרצליה',
    'Holon': 'חולון',
    'Jerusalem': 'ירושלים',
    'KarneyShomron': 'קרני שומרון',
    'KfarSaba': 'כפר סבא',
    'KiryatShmona': 'קריית שמונה',
    'ModiinMakabimReut': 'מודיעין-מכבים-רעות',
    'Natanya': 'נתניה',
    'Nazrat': 'נצרת',
    'PetahTikva': 'פתח תקווה',
    'RamatGan': 'רמת גן',
    'Rehovot': 'רחובות',
    'RishonLetzion': 'ראשון לציון',
    'TelAviv': 'תל אביב',
}


def get_city_name_from_file_name(filename: str) -> Optional[str]:
    """
    מחזירה את החלק אחרי 'GetAlarmsHistory_' עד '_' או ספרה או סוף הקובץ, בלי הסיומת '.json'
    """
    prefix = "GetAlarmsHistory_"
    name_only = filename.rsplit(".json", 1)[0]
    if prefix in name_only:
        part = name_only.split(prefix, 1)[1]
        match = re.match(r'([^\d_]+)', part)
        if match:
            return match.group(1)
    return None


def get_city_name_hebrew(city_name: Optional[str]) -> Optional[str]:
    """Translate the canonical city key to its Hebrew display name."""
    if city_name is None:
        return None
    return CITY_NAME_HEBREW_MAP.get(city_name, city_name)


def get_alert_key(value: Union[str, int], alert_dict: Dict[str, List[int]]) -> Optional[str]:
    """
    מקבלת ערך ובודקת לאיזה קבוצה במילון הוא שייך.
    מחזירה את המפתח או None.
    """
    if isinstance(value, str):
        if not value.isdigit():
            return None
        value_to_check = int(value)
    elif isinstance(value, int):
        value_to_check = value
    else:
        return None

    for key, values in alert_dict.items():
        if value_to_check in values:
            return key
    return None

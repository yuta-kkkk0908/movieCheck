"""
cast フィールドの正規化ユーティリティ
"""
import ast
import json
from typing import List, Optional


def parse_cast_text(value: Optional[str]) -> List[str]:
    """
    cast の保存値（JSON文字列 or 旧str(list)）を list[str] に変換する。
    """
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []

    # JSON配列
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    # 旧形式: "['A', 'B']"
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    return []


def dump_cast_text(cast_list: Optional[List[str]]) -> str:
    """
    cast list を JSON文字列へ変換する。
    """
    safe_list = []
    for item in cast_list or []:
        text = str(item).strip()
        if text:
            safe_list.append(text)
    return json.dumps(safe_list, ensure_ascii=False)


def is_cast_empty(value: Optional[str]) -> bool:
    return len(parse_cast_text(value)) == 0

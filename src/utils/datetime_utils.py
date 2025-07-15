"""
日時処理ユーティリティ

datetime シリアライゼーション/デシリアライゼーションの統一機能
30+箇所で重複していた日時変換処理を統一
"""

from datetime import datetime
from typing import Dict, List, Any, Union


def serialize_datetime_dict(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """辞書内の datetime オブジェクトを ISO 形式文字列に変換
    
    Args:
        data: 変換対象の辞書
        fields: datetime フィールド名のリスト
        
    Returns:
        datetime が ISO 形式文字列に変換された辞書
        
    Example:
        data = {'timestamp': datetime.now(), 'name': 'test'}
        result = serialize_datetime_dict(data, ['timestamp'])
        # {'timestamp': '2025-07-14T10:30:00', 'name': 'test'}
    """
    result = data.copy()
    for field in fields:
        if field in result and isinstance(result[field], datetime):
            result[field] = result[field].isoformat()
    return result


def deserialize_datetime_dict(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """辞書内の ISO 形式文字列を datetime オブジェクトに変換
    
    Args:
        data: 変換対象の辞書
        fields: datetime フィールド名のリスト
        
    Returns:
        ISO 形式文字列が datetime に変換された辞書
        
    Example:
        data = {'timestamp': '2025-07-14T10:30:00', 'name': 'test'}
        result = deserialize_datetime_dict(data, ['timestamp'])
        # {'timestamp': datetime(2025, 7, 14, 10, 30), 'name': 'test'}
    """
    result = data.copy()
    for field in fields:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = datetime.fromisoformat(result[field])
            except ValueError:
                # ISO形式でない場合はそのまま保持
                pass
    return result


def serialize_datetime_value(value: Union[datetime, str, None]) -> Union[str, None]:
    """単一の datetime 値を ISO 形式文字列に変換
    
    Args:
        value: datetime オブジェクト、文字列、または None
        
    Returns:
        ISO 形式文字列または None
    """
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def deserialize_datetime_value(value: Union[str, datetime, None]) -> Union[datetime, None]:
    """単一の ISO 形式文字列を datetime オブジェクトに変換
    
    Args:
        value: ISO 形式文字列、datetime オブジェクト、または None
        
    Returns:
        datetime オブジェクトまたは None
    """
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value
"""
パス処理ユーティリティ

ディレクトリ作成などのパス関連処理の統一機能
12箇所で重複していたディレクトリ作成パターンを統一
"""

from pathlib import Path
from typing import Union


def ensure_directory_exists(file_path: Union[str, Path]) -> Path:
    """ファイルパスからディレクトリを作成し、Pathオブジェクトを返す
    
    ファイルの親ディレクトリが存在しない場合は自動的に作成する。
    既存のディレクトリがある場合はエラーにならない。
    
    Args:
        file_path: ファイルパス（文字列またはPathオブジェクト）
        
    Returns:
        Path: ファイルパスのPathオブジェクト
        
    Example:
        # ディレクトリが存在しない場合でも安全に作成
        output_path = ensure_directory_exists("/path/to/output/file.mp3")
        with open(output_path, 'w') as f:
            f.write("content")
    
    Note:
        これまで12箇所で重複していた以下のパターンを置換:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_directory_path_exists(dir_path: Union[str, Path]) -> Path:
    """ディレクトリパスを作成し、Pathオブジェクトを返す
    
    指定されたディレクトリパスが存在しない場合は自動的に作成する。
    既存のディレクトリがある場合はエラーにならない。
    
    Args:
        dir_path: ディレクトリパス（文字列またはPathオブジェクト）
        
    Returns:
        Path: ディレクトリパスのPathオブジェクト
        
    Example:
        # ディレクトリを安全に作成
        logs_dir = ensure_directory_path_exists("/path/to/logs")
        log_file = logs_dir / "app.log"
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path
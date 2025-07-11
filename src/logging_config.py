"""
ログ設定モジュール

RecRadikoプロジェクト全体のログ設定を統一管理します。
- 通常使用時：コンソール出力なし、ファイル出力のみ
- テスト時：コンソール出力あり、詳細ログ出力
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union


class RecRadikoLogConfig:
    """RecRadikoのログ設定管理クラス"""
    
    # デフォルト設定
    DEFAULT_LOG_LEVEL = logging.INFO
    DEFAULT_LOG_FILE = "recradiko.log"
    DEFAULT_MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self._initialized = False
        self._is_test_mode = self._detect_test_mode()
        self._console_output = self._determine_console_output()
    
    def _detect_test_mode(self) -> bool:
        """テストモードかどうかを判定"""
        # pytest実行時の環境変数をチェック
        return any([
            'PYTEST_CURRENT_TEST' in os.environ,
            'pytest' in sys.modules,
            os.environ.get('RECRADIKO_TEST_MODE', '').lower() == 'true'
        ])
    
    def _determine_console_output(self) -> bool:
        """コンソール出力を行うかどうかを判定"""
        # 環境変数による明示的な制御
        console_env = os.environ.get('RECRADIKO_CONSOLE_OUTPUT', '').lower()
        if console_env == 'true':
            return True
        elif console_env == 'false':
            return False
        
        # テストモードの場合はコンソール出力を有効化
        return self._is_test_mode
    
    def setup_logging(self, 
                     log_level: Optional[Union[str, int]] = None,
                     log_file: Optional[str] = None,
                     console_output: Optional[bool] = None,
                     max_log_size: Optional[int] = None) -> None:
        """
        ログ設定を初期化
        
        Args:
            log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            log_file: ログファイルパス
            console_output: コンソール出力の有無（None時は自動判定）
            max_log_size: ログファイルの最大サイズ（バイト）
        """
        if self._initialized:
            return
        
        # パラメータの設定
        if log_level is None:
            log_level = os.environ.get('RECRADIKO_LOG_LEVEL', self.DEFAULT_LOG_LEVEL)
        
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper(), self.DEFAULT_LOG_LEVEL)
        
        # テスト時はERRORレベル以上のみにして安全性を高める
        if self._is_test_mode and log_level < logging.ERROR:
            log_level = logging.ERROR
        
        if log_file is None:
            log_file = os.environ.get('RECRADIKO_LOG_FILE', self.DEFAULT_LOG_FILE)
        
        if console_output is None:
            console_output = self._console_output
        
        if max_log_size is None:
            max_log_size = self.DEFAULT_MAX_LOG_SIZE
        
        # ハンドラーの設定
        handlers = []
        
        # ファイルハンドラー（テスト時以外で有効）
        if log_file and not self._is_test_mode:
            try:
                # ログファイルのディレクトリを作成
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                # ローテーションハンドラーを使用
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_log_size,
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setLevel(log_level)
                handlers.append(file_handler)
                
            except Exception as e:
                # ファイルハンドラーの作成に失敗した場合は警告
                print(f"Warning: Failed to create log file handler: {e}", file=sys.stderr)
        
        # コンソールハンドラー（テスト時のみ、さらにエラーレベル以上のみ）
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            # テスト時はERRORレベル以上のみ出力して安全性を高める
            if self._is_test_mode:
                console_handler.setLevel(logging.ERROR)
            else:
                console_handler.setLevel(log_level)
            handlers.append(console_handler)
        
        # ロガーの設定
        if handlers:
            logging.basicConfig(
                level=log_level,
                handlers=handlers,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                force=True  # 既存の設定を上書き
            )
        else:
            # ハンドラーがない場合はNullHandlerを設定
            logging.basicConfig(
                level=log_level,
                handlers=[logging.NullHandler()],
                force=True
            )
        
        self._initialized = True
        
        # 設定内容をログに記録（テスト時のみ）
        if console_output:
            logger = logging.getLogger(__name__)
            logger.info(f"ログ設定完了 - レベル: {logging.getLevelName(log_level)}, "
                       f"ファイル: {log_file}, コンソール出力: {console_output}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        ロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            logging.Logger: 設定済みのロガー
        """
        if not self._initialized:
            self.setup_logging()
        
        return logging.getLogger(name)
    
    def is_test_mode(self) -> bool:
        """テストモードかどうかを返す"""
        return self._is_test_mode
    
    def is_console_output_enabled(self) -> bool:
        """コンソール出力が有効かどうかを返す"""
        return self._console_output
    
    def reset(self) -> None:
        """ログ設定をリセット（テスト用）"""
        self._initialized = False
        # 既存のハンドラーを削除
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)


# グローバルインスタンス
_log_config = RecRadikoLogConfig()

# 公開API
def setup_logging(log_level: Optional[Union[str, int]] = None,
                 log_file: Optional[str] = None,
                 console_output: Optional[bool] = None,
                 max_log_size: Optional[int] = None) -> None:
    """
    RecRadikoのログ設定を初期化
    
    Args:
        log_level: ログレベル
        log_file: ログファイルパス
        console_output: コンソール出力の有無
        max_log_size: ログファイルの最大サイズ
    """
    _log_config.setup_logging(log_level, log_file, console_output, max_log_size)


def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: 設定済みのロガー
    """
    return _log_config.get_logger(name)


def is_test_mode() -> bool:
    """テストモードかどうかを返す"""
    return _log_config.is_test_mode()


def is_console_output_enabled() -> bool:
    """コンソール出力が有効かどうかを返す"""
    return _log_config.is_console_output_enabled()


def reset_logging() -> None:
    """ログ設定をリセット（テスト用）"""
    _log_config.reset()
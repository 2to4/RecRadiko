"""
基底クラスとMixin

共通機能を提供する基底クラスとMixin
"""

from src.logging_config import get_logger


class LoggerMixin:
    """ロガー機能を提供するMixin
    
    全11クラスで重複していたロガー初期化パターンを統一
    
    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                super().__init__()  # ロガーが自動初期化される
                # self.logger が利用可能
    """
    
    def __init__(self):
        """ロガーを自動初期化"""
        self.logger = get_logger(self.__class__.__module__)
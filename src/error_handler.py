"""
エラーハンドリングモジュール

このモジュールはRecRadikoの統一エラーハンドリングを提供します。
- カスタム例外クラス
- エラーロギング
- 復旧処理
- 通知機能
"""

import logging
import traceback
import threading
import time
import json
from typing import List, Optional, Dict, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .logging_config import get_logger


class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"           # 軽微な警告
    MEDIUM = "medium"     # 注意が必要なエラー
    HIGH = "high"         # 重要なエラー
    CRITICAL = "critical" # 致命的なエラー


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    AUTHENTICATION = "authentication"     # 認証関連
    NETWORK = "network"                   # ネットワーク関連
    STREAMING = "streaming"               # ストリーミング関連
    RECORDING = "recording"               # 録音関連
    FILE_SYSTEM = "file_system"           # ファイルシステム関連
    SCHEDULING = "scheduling"             # スケジューリング関連
    CONFIGURATION = "configuration"       # 設定関連
    SYSTEM = "system"                     # システム関連
    UNKNOWN = "unknown"                   # 不明


@dataclass
class ErrorRecord:
    """エラー記録"""
    id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    message: str
    details: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""
    resolved: bool = False
    resolution_notes: str = ""
    occurrence_count: int = 1
    first_occurred: datetime = field(default_factory=datetime.now)
    last_occurred: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'category': self.category.value,
            'error_type': self.error_type,
            'message': self.message,
            'details': self.details,
            'context': self.context,
            'stack_trace': self.stack_trace,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes,
            'occurrence_count': self.occurrence_count,
            'first_occurred': self.first_occurred.isoformat(),
            'last_occurred': self.last_occurred.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorRecord':
        """辞書から復元"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['severity'] = ErrorSeverity(data['severity'])
        data['category'] = ErrorCategory(data['category'])
        data['first_occurred'] = datetime.fromisoformat(data['first_occurred'])
        data['last_occurred'] = datetime.fromisoformat(data['last_occurred'])
        return cls(**data)


# カスタム例外クラス群

class RecRadikoError(Exception):
    """RecRadiko基底例外クラス"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}


class AuthenticationError(RecRadikoError):
    """認証エラー"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, context)


class NetworkError(RecRadikoError):
    """ネットワークエラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.NETWORK, severity, context)


class StreamingError(RecRadikoError):
    """ストリーミングエラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.STREAMING, severity, context)


class RecordingError(RecRadikoError):
    """録音エラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.RECORDING, severity, context)


class FileSystemError(RecRadikoError):
    """ファイルシステムエラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.FILE_SYSTEM, severity, context)


class SchedulingError(RecRadikoError):
    """スケジューリングエラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.SCHEDULING, severity, context)


class ConfigurationError(RecRadikoError):
    """設定エラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.CONFIGURATION, severity, context)


class SystemError(RecRadikoError):
    """システムエラー"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.CRITICAL, 
                 context: Dict[str, Any] = None):
        super().__init__(message, ErrorCategory.SYSTEM, severity, context)


class ErrorHandler:
    """統一エラーハンドラー"""
    
    def __init__(self, 
                 log_file: str = "error.log",
                 error_db_file: str = "errors.json",
                 max_error_records: int = 1000,
                 notification_enabled: bool = False,
                 email_config: Optional[Dict[str, Any]] = None):
        
        self.log_file = Path(log_file)
        self.error_db_file = Path(error_db_file)
        self.max_error_records = max_error_records
        self.notification_enabled = notification_enabled
        self.email_config = email_config or {}
        
        # エラー記録
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_count_by_type: Dict[str, int] = {}
        self.lock = threading.RLock()
        
        # ログ設定
        self.logger = self._setup_logger()
        
        # 通知コールバック
        self.notification_callbacks: List[Callable[[ErrorRecord], None]] = []
        
        # 復旧処理コールバック
        self.recovery_handlers: Dict[Type[Exception], Callable[[Exception], bool]] = {}
        
        # 既存のエラー記録を読み込み
        self._load_error_records()
        
        # エラー統計の定期クリーンアップ
        self._start_cleanup_timer()
    
    def _setup_logger(self) -> logging.Logger:
        """エラーログ専用のロガーを設定"""
        logger = get_logger("RecRadiko.ErrorHandler")
        
        # エラーハンドラー用の専用ファイルハンドラーを追加
        if not any(isinstance(h, logging.FileHandler) and str(h.baseFilename) == str(self.log_file.absolute())
                  for h in logger.handlers):
            # ログディレクトリを作成
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _load_error_records(self):
        """既存のエラー記録を読み込み"""
        try:
            if self.error_db_file.exists():
                with open(self.error_db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                with self.lock:
                    for record_data in data.get('records', []):
                        record = ErrorRecord.from_dict(record_data)
                        self.error_records[record.id] = record
                        
                        # エラー種別カウントを復元
                        error_key = f"{record.category.value}:{record.error_type}"
                        self.error_count_by_type[error_key] = record.occurrence_count
                
                self.logger.info(f"エラー記録読み込み完了: {len(self.error_records)} 件")
        
        except Exception as e:
            self.logger.error(f"エラー記録読み込みエラー: {e}")
    
    def _save_error_records(self):
        """エラー記録をファイルに保存"""
        try:
            with self.lock:
                data = {
                    'version': '1.0',
                    'updated_at': datetime.now().isoformat(),
                    'records': [record.to_dict() for record in self.error_records.values()]
                }
            
            # 一時ファイルに書き込み後、原子的に置換
            temp_file = self.error_db_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            temp_file.replace(self.error_db_file)
            
        except Exception as e:
            self.logger.error(f"エラー記録保存エラー: {e}")
    
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any] = None,
                    auto_recovery: bool = True) -> str:
        """エラーを処理し、エラーIDを返す"""
        
        # エラー情報を抽出
        error_type = type(error).__name__
        message = str(error)
        stack_trace = traceback.format_exc()
        
        # カスタム例外の場合は詳細情報を取得
        if isinstance(error, RecRadikoError):
            category = error.category
            severity = error.severity
            if error.context:
                context = {**(context or {}), **error.context}
        else:
            # 標準例外の場合はカテゴリを推定
            category = self._categorize_error(error)
            severity = self._assess_severity(error)
        
        # エラーIDを生成
        error_id = self._generate_error_id(error_type, message)
        
        # 既存のエラー記録をチェック
        with self.lock:
            if error_id in self.error_records:
                # 既存エラーの更新
                record = self.error_records[error_id]
                record.occurrence_count += 1
                record.last_occurred = datetime.now()
                record.context.update(context or {})
            else:
                # 新規エラー記録
                record = ErrorRecord(
                    id=error_id,
                    timestamp=datetime.now(),
                    severity=severity,
                    category=category,
                    error_type=error_type,
                    message=message,
                    details=self._extract_error_details(error),
                    context=context or {},
                    stack_trace=stack_trace
                )
                self.error_records[error_id] = record
            
            # エラー種別カウントを更新
            error_key = f"{category.value}:{error_type}"
            self.error_count_by_type[error_key] = record.occurrence_count
        
        # ログに記録
        log_level = self._get_log_level(severity)
        self.logger.log(log_level, f"[{error_id}] {category.value}: {message}")
        
        if context:
            self.logger.debug(f"[{error_id}] Context: {json.dumps(context, default=str)}")
        
        # 通知を送信
        if self.notification_enabled and severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._send_notifications(record)
        
        # 自動復旧を試行
        if auto_recovery:
            self._attempt_recovery(error, record)
        
        # エラー記録を保存
        self._save_error_records()
        
        return error_id
    
    def _generate_error_id(self, error_type: str, message: str) -> str:
        """エラーIDを生成"""
        import hashlib
        content = f"{error_type}:{message[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """標準例外のカテゴリを推定"""
        error_type = type(error).__name__
        message = str(error).lower()
        
        # ネットワーク関連
        if any(keyword in message for keyword in ['connection', 'timeout', 'network', 'dns', 'socket']):
            return ErrorCategory.NETWORK
        
        # ファイルシステム関連
        if any(keyword in message for keyword in ['file', 'directory', 'permission', 'disk', 'space']):
            return ErrorCategory.FILE_SYSTEM
        
        # 認証関連
        if any(keyword in message for keyword in ['auth', 'login', 'credential', 'token']):
            return ErrorCategory.AUTHENTICATION
        
        # 設定関連
        if any(keyword in message for keyword in ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        
        # エラー種別による分類
        if error_type in ['ValueError', 'TypeError', 'AttributeError']:
            return ErrorCategory.CONFIGURATION
        elif error_type in ['OSError', 'IOError', 'FileNotFoundError']:
            return ErrorCategory.FILE_SYSTEM
        elif error_type in ['ConnectionError', 'TimeoutError']:
            return ErrorCategory.NETWORK
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """エラーの重要度を評価"""
        error_type = type(error).__name__
        message = str(error).lower()
        
        # エラー種別による評価（最優先）
        if error_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError']:
            return ErrorSeverity.CRITICAL
        elif error_type in ['ValueError', 'TypeError', 'AttributeError']:
            return ErrorSeverity.MEDIUM
        
        # 致命的エラー
        if any(keyword in message for keyword in ['critical', 'fatal', 'corrupt', 'crash', 'system failure']):
            return ErrorSeverity.CRITICAL
        
        # 高重要度エラー（より具体的なキーワード）
        if any(keyword in message for keyword in ['failed', 'exception', 'connection failed', 'authentication failed']):
            return ErrorSeverity.HIGH
        
        # 警告レベル
        if any(keyword in message for keyword in ['warning', 'deprecated', 'retry']):
            return ErrorSeverity.LOW
        
        # 一般的な「error」は中程度
        if 'error' in message:
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.MEDIUM
    
    def _extract_error_details(self, error: Exception) -> str:
        """エラーの詳細情報を抽出"""
        details = []
        
        # エラーの属性を収集
        for attr in dir(error):
            if not attr.startswith('_') and hasattr(error, attr):
                try:
                    value = getattr(error, attr)
                    if not callable(value) and str(value):
                        details.append(f"{attr}: {value}")
                except:
                    pass
        
        return "\n".join(details) if details else ""
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """重要度に対応するログレベルを取得"""
        mapping = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.ERROR)
    
    def _send_notifications(self, record: ErrorRecord):
        """エラー通知を送信"""
        try:
            # コールバック通知
            for callback in self.notification_callbacks:
                try:
                    callback(record)
                except Exception as e:
                    self.logger.warning(f"通知コールバックエラー: {e}")
            
            # メール通知
            if self.email_config and record.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._send_email_notification(record)
        
        except Exception as e:
            self.logger.error(f"通知送信エラー: {e}")
    
    def _send_email_notification(self, record: ErrorRecord):
        """メール通知を送信"""
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, to_emails]):
                return
            
            # メッセージを作成
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"RecRadiko エラー通知 - {record.severity.value.upper()}"
            
            body = f"""
RecRadiko でエラーが発生しました。

エラーID: {record.id}
重要度: {record.severity.value.upper()}
カテゴリ: {record.category.value}
エラー種別: {record.error_type}
メッセージ: {record.message}
発生時刻: {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
発生回数: {record.occurrence_count}

詳細:
{record.details}

コンテキスト:
{json.dumps(record.context, indent=2, ensure_ascii=False)}
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # メールを送信
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            self.logger.info(f"エラー通知メール送信完了: {record.id}")
        
        except Exception as e:
            self.logger.error(f"メール通知エラー: {e}")
    
    def _attempt_recovery(self, error: Exception, record: ErrorRecord):
        """自動復旧を試行"""
        try:
            error_type = type(error)
            
            # 登録された復旧ハンドラーを実行
            if error_type in self.recovery_handlers:
                handler = self.recovery_handlers[error_type]
                if handler(error):
                    record.resolved = True
                    record.resolution_notes = "自動復旧成功"
                    self.logger.info(f"自動復旧成功: {record.id}")
                    return
            
            # 汎用復旧処理
            if self._generic_recovery(error, record):
                record.resolved = True
                record.resolution_notes = "汎用復旧処理により解決"
                self.logger.info(f"汎用復旧成功: {record.id}")
        
        except Exception as e:
            self.logger.error(f"復旧処理エラー: {e}")
    
    def _generic_recovery(self, error: Exception, record: ErrorRecord) -> bool:
        """汎用復旧処理"""
        # ネットワークエラーの場合は短時間待機
        if record.category == ErrorCategory.NETWORK:
            self.logger.info("ネットワークエラー復旧: 5秒待機")
            time.sleep(5)
            return True
        
        # ファイルシステムエラーの場合はディレクトリ作成を試行
        if (record.category == ErrorCategory.FILE_SYSTEM and 
            'directory' in record.message.lower()):
            try:
                # コンテキストからパスを取得
                if 'path' in record.context:
                    path = Path(record.context['path'])
                    path.mkdir(parents=True, exist_ok=True)
                    return True
            except:
                pass
        
        return False
    
    def register_recovery_handler(self, 
                                error_type: Type[Exception], 
                                handler: Callable[[Exception], bool]):
        """復旧ハンドラーを登録"""
        self.recovery_handlers[error_type] = handler
        self.logger.info(f"復旧ハンドラー登録: {error_type.__name__}")
    
    def add_notification_callback(self, callback: Callable[[ErrorRecord], None]):
        """通知コールバックを追加"""
        self.notification_callbacks.append(callback)
    
    def remove_notification_callback(self, callback: Callable[[ErrorRecord], None]):
        """通知コールバックを削除"""
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
    
    def get_error_record(self, error_id: str) -> Optional[ErrorRecord]:
        """エラー記録を取得"""
        with self.lock:
            return self.error_records.get(error_id)
    
    def list_errors(self, 
                   category: Optional[ErrorCategory] = None,
                   severity: Optional[ErrorSeverity] = None,
                   resolved_only: Optional[bool] = None,
                   limit: int = 100) -> List[ErrorRecord]:
        """エラー一覧を取得"""
        with self.lock:
            errors = list(self.error_records.values())
        
        # フィルタリング
        if category:
            errors = [e for e in errors if e.category == category]
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        if resolved_only is not None:
            errors = [e for e in errors if e.resolved == resolved_only]
        
        # 最新順でソート
        errors.sort(key=lambda x: x.last_occurred, reverse=True)
        
        return errors[:limit]
    
    def mark_resolved(self, error_id: str, resolution_notes: str = "") -> bool:
        """エラーを解決済みにマーク"""
        with self.lock:
            if error_id in self.error_records:
                record = self.error_records[error_id]
                record.resolved = True
                record.resolution_notes = resolution_notes
                self._save_error_records()
                self.logger.info(f"エラー解決マーク: {error_id}")
                return True
        
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        with self.lock:
            errors = list(self.error_records.values())
        
        if not errors:
            return {}
        
        # 基本統計
        total_errors = len(errors)
        resolved_errors = len([e for e in errors if e.resolved])
        unresolved_errors = total_errors - resolved_errors
        
        # 重要度別統計
        severity_stats = {}
        for severity in ErrorSeverity:
            count = len([e for e in errors if e.severity == severity])
            severity_stats[severity.value] = count
        
        # カテゴリ別統計
        category_stats = {}
        for category in ErrorCategory:
            count = len([e for e in errors if e.category == category])
            category_stats[category.value] = count
        
        # 最近のエラー（24時間以内）
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_errors = len([e for e in errors if e.last_occurred >= recent_cutoff])
        
        # 頻発エラー（発生回数上位5件）
        frequent_errors = sorted(errors, key=lambda x: x.occurrence_count, reverse=True)[:5]
        frequent_stats = [
            {
                'id': e.id,
                'message': e.message[:100],
                'count': e.occurrence_count,
                'category': e.category.value
            }
            for e in frequent_errors
        ]
        
        return {
            'total_errors': total_errors,
            'resolved_errors': resolved_errors,
            'unresolved_errors': unresolved_errors,
            'recent_errors_24h': recent_errors,
            'severity_breakdown': severity_stats,
            'category_breakdown': category_stats,
            'frequent_errors': frequent_stats
        }
    
    def _start_cleanup_timer(self):
        """定期クリーンアップタイマーを開始"""
        def cleanup_task():
            try:
                self.cleanup_old_errors()
            except Exception as e:
                self.logger.error(f"エラークリーンアップエラー: {e}")
            finally:
                # 24時間後に再実行
                threading.Timer(86400, cleanup_task).start()
        
        # 1時間後に初回実行
        threading.Timer(3600, cleanup_task).start()
    
    def cleanup_old_errors(self, retention_days: int = 30):
        """古いエラー記録を削除"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with self.lock:
            errors_to_remove = [
                error_id for error_id, record in self.error_records.items()
                if record.last_occurred < cutoff_date and record.resolved
            ]
            
            for error_id in errors_to_remove:
                del self.error_records[error_id]
            
            # 最大レコード数制限
            if len(self.error_records) > self.max_error_records:
                # 古い解決済みエラーから削除
                sorted_errors = sorted(
                    self.error_records.items(),
                    key=lambda x: (x[1].resolved, x[1].last_occurred)
                )
                
                excess_count = len(self.error_records) - self.max_error_records
                for i in range(excess_count):
                    error_id, _ = sorted_errors[i]
                    del self.error_records[error_id]
        
        if errors_to_remove:
            self._save_error_records()
            self.logger.info(f"古いエラー記録削除: {len(errors_to_remove)} 件")
    
    def export_errors(self, export_path: str, format: str = "json"):
        """エラー記録をエクスポート"""
        try:
            with self.lock:
                data = [record.to_dict() for record in self.error_records.values()]
            
            export_path_obj = Path(export_path)
            
            if format.lower() == "json":
                with open(export_path_obj, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == "csv":
                import csv
                
                if data:
                    with open(export_path_obj, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            
            else:
                raise ValueError(f"未対応の形式: {format}")
            
            self.logger.info(f"エラー記録エクスポート完了: {export_path}")
            
        except Exception as e:
            self.logger.error(f"エラー記録エクスポートエラー: {e}")
    
    def shutdown(self):
        """エラーハンドラーを終了"""
        self.logger.info("エラーハンドラーを終了中...")
        
        # エラー記録を保存
        self._save_error_records()
        
        self.logger.info("エラーハンドラーを終了しました")


# グローバルエラーハンドラーインスタンス
_global_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラーを取得"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler

def handle_error(error: Exception, context: Dict[str, Any] = None) -> str:
    """エラーを処理（便利関数）"""
    return get_error_handler().handle_error(error, context)

def setup_error_handler(**kwargs) -> ErrorHandler:
    """エラーハンドラーを設定"""
    global _global_error_handler
    _global_error_handler = ErrorHandler(**kwargs)
    return _global_error_handler


# テスト用の簡単な使用例
if __name__ == "__main__":
    import sys
    
    # ログ設定（テスト実行時のみ）
    import os
    if os.environ.get('RECRADIKO_TEST_MODE', '').lower() == 'true':
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    try:
        # エラーハンドラーのテスト
        error_handler = ErrorHandler()
        
        # 通知コールバックを設定
        def notification_callback(record: ErrorRecord):
            print(f"エラー通知: {record.severity.value} - {record.message}")
        
        error_handler.add_notification_callback(notification_callback)
        
        # 復旧ハンドラーを設定
        def network_recovery(error):
            print("ネットワークエラー復旧処理を実行")
            return True
        
        error_handler.register_recovery_handler(NetworkError, network_recovery)
        
        # テストエラーを発生させる
        try:
            raise NetworkError("テストネットワークエラー", severity=ErrorSeverity.HIGH)
        except Exception as e:
            error_id = error_handler.handle_error(e, {'test': True})
            print(f"エラーID: {error_id}")
        
        # 統計情報を表示
        stats = error_handler.get_error_statistics()
        print(f"エラー統計: {stats}")
        
        # エラー一覧を表示
        errors = error_handler.list_errors(limit=5)
        print(f"最近のエラー: {len(errors)} 件")
        
        for error_record in errors:
            print(f"  {error_record.id}: {error_record.message}")
        
        # 終了処理
        error_handler.shutdown()
        
    except Exception as e:
        print(f"エラーハンドラーテストエラー: {e}")
        sys.exit(1)
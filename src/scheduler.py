"""
スケジューリング機能モジュール

このモジュールはRecRadikoの録音スケジュール管理を行います。
- 録音予約の管理
- 繰り返し録音の設定
- 事前通知機能
- スケジュール競合の検出
"""

import sqlite3
import threading
import time
import logging
from typing import List, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import json
import uuid

from .logging_config import get_logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.job import Job
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
except ImportError:
    # APSchedulerが利用できない場合の代替実装
    BackgroundScheduler = None
    DateTrigger = None
    CronTrigger = None


class RepeatPattern(Enum):
    """繰り返しパターン"""
    NONE = "none"           # 繰り返しなし
    DAILY = "daily"         # 毎日
    WEEKLY = "weekly"       # 毎週
    WEEKDAYS = "weekdays"   # 平日のみ
    WEEKENDS = "weekends"   # 週末のみ
    MONTHLY = "monthly"     # 毎月
    CUSTOM = "custom"       # カスタム


class ScheduleStatus(Enum):
    """スケジュールステータス"""
    ACTIVE = "active"       # アクティブ
    INACTIVE = "inactive"   # 非アクティブ
    EXPIRED = "expired"     # 期限切れ
    COMPLETED = "completed" # 完了
    CANCELLED = "cancelled" # キャンセル
    SCHEDULED = "scheduled" # スケジュール済み
    RUNNING = "running"     # 実行中
    FAILED = "failed"       # 失敗
    MISSED = "missed"       # 未実行


@dataclass
class RecordingSchedule:
    """録音スケジュール情報"""
    schedule_id: str
    station_id: str
    program_title: str
    start_time: datetime
    end_time: datetime
    repeat_pattern: RepeatPattern = RepeatPattern.NONE
    repeat_end_date: Optional[datetime] = None
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    format: str = "aac"
    bitrate: int = 128
    notification_enabled: bool = True
    notification_minutes: List[int] = field(default_factory=lambda: [5, 1])
    created_at: datetime = field(default_factory=datetime.now)
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    notes: str = ""
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    
    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    @property
    def duration_seconds(self) -> int:
        return int((self.end_time - self.start_time).total_seconds())
    
    def is_active(self) -> bool:
        """現在アクティブかどうかを判定"""
        now = datetime.now()
        return self.start_time <= now < self.end_time
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'schedule_id': self.schedule_id,
            'station_id': self.station_id,
            'program_title': self.program_title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'repeat_pattern': self.repeat_pattern.value,
            'repeat_end_date': self.repeat_end_date.isoformat() if self.repeat_end_date else None,
            'status': self.status.value,
            'format': self.format,
            'bitrate': self.bitrate,
            'notification_enabled': self.notification_enabled,
            'notification_minutes': self.notification_minutes,
            'created_at': self.created_at.isoformat(),
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'execution_count': self.execution_count,
            'notes': self.notes,
            'enabled': self.enabled,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordingSchedule':
        """辞書から復元"""
        data = data.copy()
        
        # 'id' キーを 'schedule_id' にマップ
        if 'id' in data and 'schedule_id' not in data:
            data['schedule_id'] = data.pop('id')
        
        # 日時データを変換
        if isinstance(data.get('start_time'), str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if isinstance(data.get('end_time'), str):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # 列挙型を変換
        if isinstance(data.get('repeat_pattern'), str):
            data['repeat_pattern'] = RepeatPattern(data['repeat_pattern'])
        if isinstance(data.get('status'), str):
            data['status'] = ScheduleStatus(data['status'])
        
        # オプションの日時データを変換
        if data.get('repeat_end_date') and isinstance(data['repeat_end_date'], str):
            data['repeat_end_date'] = datetime.fromisoformat(data['repeat_end_date'])
        if data.get('last_executed') and isinstance(data['last_executed'], str):
            data['last_executed'] = datetime.fromisoformat(data['last_executed'])
        
        # RecordingScheduleに存在しない属性を除去
        valid_fields = {
            'schedule_id', 'station_id', 'program_title', 'start_time', 'end_time',
            'repeat_pattern', 'repeat_end_date', 'status', 'format', 'bitrate',
            'notification_enabled', 'notification_minutes', 'created_at',
            'last_executed', 'execution_count', 'notes', 'enabled', 'tags'
        }
        
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def get_next_execution_time(self, after: Optional[datetime] = None) -> Optional[datetime]:
        """次の実行時刻を取得"""
        if self.status != ScheduleStatus.ACTIVE:
            return None
        
        if after is None:
            after = datetime.now()
        
        # 単発の場合
        if self.repeat_pattern == RepeatPattern.NONE:
            return self.start_time if self.start_time > after else None
        
        # 終了日をチェック
        if self.repeat_end_date and after >= self.repeat_end_date:
            return None
        
        # パターンに応じて次の実行時刻を計算
        base_time = self.start_time
        
        if self.repeat_pattern == RepeatPattern.DAILY:
            next_time = self._next_daily(base_time, after)
        elif self.repeat_pattern == RepeatPattern.WEEKLY:
            next_time = self._next_weekly(base_time, after)
        elif self.repeat_pattern == RepeatPattern.WEEKDAYS:
            next_time = self._next_weekdays(base_time, after)
        elif self.repeat_pattern == RepeatPattern.WEEKENDS:
            next_time = self._next_weekends(base_time, after)
        elif self.repeat_pattern == RepeatPattern.MONTHLY:
            next_time = self._next_monthly(base_time, after)
        else:
            return None
        
        # 終了日チェック
        if self.repeat_end_date and next_time and next_time > self.repeat_end_date:
            return None
        
        return next_time
    
    def _next_daily(self, base_time: datetime, after: datetime) -> Optional[datetime]:
        """毎日の次の実行時刻"""
        days_diff = (after.date() - base_time.date()).days
        if days_diff < 0:
            return base_time
        
        next_date = base_time.date() + timedelta(days=days_diff + 1)
        return datetime.combine(next_date, base_time.time())
    
    def _next_weekly(self, base_time: datetime, after: datetime) -> Optional[datetime]:
        """毎週の次の実行時刻"""
        target_weekday = base_time.weekday()
        days_until = (target_weekday - after.weekday()) % 7
        
        if days_until == 0:
            # 同じ曜日の場合、時刻をチェック
            if after.time() < base_time.time():
                next_date = after.date()
            else:
                next_date = after.date() + timedelta(days=7)
        else:
            next_date = after.date() + timedelta(days=days_until)
        
        return datetime.combine(next_date, base_time.time())
    
    def _next_weekdays(self, base_time: datetime, after: datetime) -> Optional[datetime]:
        """平日の次の実行時刻"""
        current_date = after.date()
        current_time = after.time()
        
        for i in range(7):  # 最大1週間先まで探す
            check_date = current_date + timedelta(days=i)
            check_weekday = check_date.weekday()
            
            # 平日（月曜日=0 から 金曜日=4）
            if check_weekday < 5:
                check_datetime = datetime.combine(check_date, base_time.time())
                if check_datetime > after:
                    return check_datetime
        
        return None
    
    def _next_weekends(self, base_time: datetime, after: datetime) -> Optional[datetime]:
        """週末の次の実行時刻"""
        current_date = after.date()
        
        for i in range(7):  # 最大1週間先まで探す
            check_date = current_date + timedelta(days=i)
            check_weekday = check_date.weekday()
            
            # 週末（土曜日=5, 日曜日=6）
            if check_weekday >= 5:
                check_datetime = datetime.combine(check_date, base_time.time())
                if check_datetime > after:
                    return check_datetime
        
        return None
    
    def _next_monthly(self, base_time: datetime, after: datetime) -> Optional[datetime]:
        """毎月の次の実行時刻"""
        target_day = base_time.day
        
        # 今月の同じ日
        try:
            next_time = after.replace(day=target_day, 
                                    hour=base_time.hour, 
                                    minute=base_time.minute, 
                                    second=base_time.second)
            if next_time > after:
                return next_time
        except ValueError:
            pass  # 存在しない日付（例：2月30日）
        
        # 来月の同じ日
        next_month = after.month + 1
        next_year = after.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        try:
            return datetime(next_year, next_month, target_day,
                          base_time.hour, base_time.minute, base_time.second)
        except ValueError:
            return None


@dataclass
class ScheduleConflict:
    """スケジュール競合情報"""
    schedule1_id: str
    schedule2_id: str
    overlap_start: datetime
    overlap_end: datetime
    duration_minutes: int


@dataclass
class DetectedConflict:
    """検出された競合情報（スケジュールオブジェクト付き）"""
    schedule1: 'RecordingSchedule'
    schedule2: 'RecordingSchedule'
    overlap_start: datetime
    overlap_end: datetime
    duration_minutes: int


class RecordingScheduler:
    """録音スケジューラークラス"""
    
    def __init__(self, 
                 db_path: str = "schedules.db",
                 max_concurrent_recordings: int = 4,
                 recorder=None,
                 error_handler=None,
                 notification_handler=None,
                 schedule_file: str = None):
        
        # ファイルパス設定（後方互換性）
        if schedule_file:
            self.db_path = Path(schedule_file)
        else:
            self.db_path = Path(db_path)
        
        self.max_concurrent_recordings = max_concurrent_recordings
        self.recorder = recorder
        self.error_handler = error_handler
        self.notification_handler = notification_handler
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # 状態管理
        self.is_running = False
        self.timers: Dict[str, threading.Timer] = {}
        
        # スケジューラー設定
        if BackgroundScheduler:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
            self.scheduler.start()
            self.is_running = True
        else:
            # 代替実装のためのタイマー管理
            self.scheduler = None
        
        # スケジュール管理
        self.schedules: Dict[str, RecordingSchedule] = {}
        self.lock = threading.RLock()
        
        # コールバック
        self.recording_callback: Optional[Callable[[RecordingSchedule], None]] = None
        self.notification_callback: Optional[Callable[[str, RecordingSchedule], None]] = None
        
        # データベース初期化
        self._init_database()
        
        # スケジュールを読み込み
        self._load_schedules()
        
        # アクティブなスケジュールを登録
        self._register_active_schedules()
    
    def _init_database(self):
        """データベースを初期化"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schedules (
                        id TEXT PRIMARY KEY,
                        station_id TEXT NOT NULL,
                        program_title TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP NOT NULL,
                        repeat_pattern TEXT NOT NULL,
                        repeat_end_date TIMESTAMP,
                        status TEXT NOT NULL,
                        format TEXT NOT NULL,
                        bitrate INTEGER NOT NULL,
                        notification_enabled BOOLEAN NOT NULL,
                        notification_minutes TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        last_executed TIMESTAMP,
                        execution_count INTEGER DEFAULT 0,
                        notes TEXT DEFAULT '',
                        enabled BOOLEAN DEFAULT 1
                    )
                ''')
                
                # インデックス作成
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_schedules_station_time 
                    ON schedules(station_id, start_time)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_schedules_status 
                    ON schedules(status)
                ''')
                
                # 既存テーブルにenabledカラムを追加（存在しない場合）
                try:
                    conn.execute('ALTER TABLE schedules ADD COLUMN enabled BOOLEAN DEFAULT 1')
                    conn.commit()
                    self.logger.info("enabledカラムを追加しました")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        # カラムが既に存在する場合
                        pass
                    else:
                        raise e
                
                # 既存テーブルにtagsカラムを追加（存在しない場合）
                try:
                    conn.execute('ALTER TABLE schedules ADD COLUMN tags TEXT DEFAULT "[]"')
                    conn.commit()
                    self.logger.info("tagsカラムを追加しました")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        # カラムが既に存在する場合
                        pass
                    else:
                        raise e
                
                conn.commit()
            
            self.logger.info("スケジュールデータベース初期化完了")
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            raise SchedulerError(f"データベースの初期化に失敗しました: {e}")
    
    def _load_schedules(self):
        """データベースからスケジュールを読み込み"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute('SELECT * FROM schedules')
                
                for row in cursor.fetchall():
                    schedule_data = {
                        'id': row[0],
                        'station_id': row[1],
                        'program_title': row[2],
                        'start_time': row[3],
                        'end_time': row[4],
                        'repeat_pattern': row[5],
                        'repeat_end_date': row[6],
                        'status': row[7],
                        'format': row[8],
                        'bitrate': row[9],
                        'notification_enabled': bool(row[10]),
                        'notification_minutes': json.loads(row[11]),
                        'created_at': row[12],
                        'last_executed': row[13],
                        'execution_count': row[14],
                        'notes': row[15] or '',
                        'enabled': bool(row[16]) if len(row) > 16 else True,
                        'tags': json.loads(row[17]) if len(row) > 17 and row[17] else []
                    }
                    
                    schedule = RecordingSchedule.from_dict(schedule_data)
                    self.schedules[schedule.schedule_id] = schedule
            
            self.logger.info(f"スケジュール読み込み完了: {len(self.schedules)} 件")
            
        except Exception as e:
            self.logger.error(f"スケジュール読み込みエラー: {e}")
    
    def _save_schedule(self, schedule: RecordingSchedule):
        """スケジュールをデータベースに保存"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO schedules 
                    (id, station_id, program_title, start_time, end_time, repeat_pattern,
                     repeat_end_date, status, format, bitrate, notification_enabled,
                     notification_minutes, created_at, last_executed, execution_count, notes, enabled, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    schedule.schedule_id,
                    schedule.station_id,
                    schedule.program_title,
                    schedule.start_time.isoformat(),
                    schedule.end_time.isoformat(),
                    schedule.repeat_pattern.value,
                    schedule.repeat_end_date.isoformat() if schedule.repeat_end_date else None,
                    schedule.status.value,
                    schedule.format,
                    schedule.bitrate,
                    schedule.notification_enabled,
                    json.dumps(schedule.notification_minutes),
                    schedule.created_at.isoformat(),
                    schedule.last_executed.isoformat() if schedule.last_executed else None,
                    schedule.execution_count,
                    schedule.notes,
                    schedule.enabled,
                    json.dumps(schedule.tags)
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"スケジュール保存エラー: {e}")
            raise SchedulerError(f"スケジュールの保存に失敗しました: {e}")
    
    def _save_schedules(self):
        """すべてのスケジュールをデータベースに保存"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                with self.lock:
                    # すべてのスケジュールを一括で保存
                    for schedule in self.schedules.values():
                        conn.execute('''
                            INSERT OR REPLACE INTO schedules 
                            (id, station_id, program_title, start_time, end_time, repeat_pattern,
                             repeat_end_date, status, format, bitrate, notification_enabled,
                             notification_minutes, created_at, last_executed, execution_count, notes, enabled, tags)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            schedule.schedule_id,
                            schedule.station_id,
                            schedule.program_title,
                            schedule.start_time.isoformat(),
                            schedule.end_time.isoformat(),
                            schedule.repeat_pattern.value,
                            schedule.repeat_end_date.isoformat() if schedule.repeat_end_date else None,
                            schedule.status.value,
                            schedule.format,
                            schedule.bitrate,
                            schedule.notification_enabled,
                            json.dumps(schedule.notification_minutes),
                            schedule.created_at.isoformat(),
                            schedule.last_executed.isoformat() if schedule.last_executed else None,
                            schedule.execution_count,
                            schedule.notes,
                            schedule.enabled,
                            json.dumps(schedule.tags)
                        ))
                    conn.commit()
                    
            self.logger.info(f"すべてのスケジュールを保存しました: {len(self.schedules)} 件")
            
        except Exception as e:
            self.logger.error(f"スケジュール一括保存エラー: {e}")
            raise SchedulerError(f"スケジュールの一括保存に失敗しました: {e}")
    
    def add_schedule(self, 
                    schedule_or_station_id, 
                    program_title: str = None,
                    start_time: datetime = None,
                    end_time: datetime = None,
                    repeat_pattern: RepeatPattern = RepeatPattern.NONE,
                    repeat_end_date: Optional[datetime] = None,
                    format: str = "aac",
                    bitrate: int = 128,
                    notification_enabled: bool = True,
                    notification_minutes: List[int] = None,
                    notes: str = "") -> Union[str, bool]:
        """録音スケジュールを追加"""
        
        # RecordingScheduleオブジェクトが渡された場合
        if isinstance(schedule_or_station_id, RecordingSchedule):
            schedule = schedule_or_station_id
            schedule_id = schedule.schedule_id
            
            # 重複チェック
            with self.lock:
                if schedule_id in self.schedules:
                    self.logger.warning(f"重複スケジュールID: {schedule_id}")
                    return False
        else:
            # 個別パラメータが渡された場合
            station_id = schedule_or_station_id
            
            if notification_minutes is None:
                notification_minutes = [5, 1]
            
            # バリデーション
            if start_time >= end_time:
                raise SchedulerError("開始時刻は終了時刻より前である必要があります")
            
            if repeat_end_date and repeat_end_date <= start_time:
                raise SchedulerError("繰り返し終了日は開始時刻より後である必要があります")
            
            # スケジュールIDを生成
            schedule_id = str(uuid.uuid4())
            
            # スケジュールを作成
            schedule = RecordingSchedule(
                schedule_id=schedule_id,
                station_id=station_id,
                program_title=program_title,
                start_time=start_time,
                end_time=end_time,
                repeat_pattern=repeat_pattern,
                repeat_end_date=repeat_end_date,
                format=format,
                bitrate=bitrate,
                notification_enabled=notification_enabled,
                notification_minutes=notification_minutes,
                notes=notes
            )
        
        # 競合チェック
        conflicts = self.check_conflicts(schedule)
        if conflicts:
            self.logger.warning(f"スケジュール競合を検出: {len(conflicts)} 件")
        
        with self.lock:
            self.schedules[schedule.schedule_id] = schedule
        
        # データベースに保存
        self._save_schedule(schedule)
        
        # スケジューラーに登録
        self._register_schedule_jobs(schedule)
        
        self.logger.info(f"スケジュール追加: {schedule.schedule_id}")
        return schedule.schedule_id
    
    def _register_schedule_jobs(self, schedule: RecordingSchedule):
        """スケジュールをジョブスケジューラーに登録"""
        if schedule.status != ScheduleStatus.ACTIVE:
            return
        
        if self.scheduler:
            # APSchedulerを使用
            self._register_apscheduler_jobs(schedule)
        else:
            # 代替実装を使用
            self._register_timer_jobs(schedule)
    
    def _register_apscheduler_jobs(self, schedule: RecordingSchedule):
        """APSchedulerにジョブを登録"""
        # 録音ジョブ
        if schedule.repeat_pattern == RepeatPattern.NONE:
            # 単発録音
            trigger = DateTrigger(run_date=schedule.start_time)
            self.scheduler.add_job(
                func=self._execute_recording,
                trigger=trigger,
                args=[schedule.schedule_id],
                id=f"recording_{schedule.schedule_id}",
                replace_existing=True
            )
        else:
            # 繰り返し録音
            trigger = self._create_cron_trigger(schedule)
            if trigger:
                self.scheduler.add_job(
                    func=self._execute_recording,
                    trigger=trigger,
                    args=[schedule.schedule_id],
                    id=f"recording_{schedule.schedule_id}",
                    replace_existing=True
                )
        
        # 通知ジョブ
        if schedule.notification_enabled:
            for minutes_before in schedule.notification_minutes:
                notification_time = schedule.start_time - timedelta(minutes=minutes_before)
                if notification_time > datetime.now():
                    self.scheduler.add_job(
                        func=self._send_notification,
                        trigger=DateTrigger(run_date=notification_time),
                        args=[schedule.schedule_id, minutes_before],
                        id=f"notification_{schedule.schedule_id}_{minutes_before}",
                        replace_existing=True
                    )
    
    def _create_cron_trigger(self, schedule: RecordingSchedule) -> Optional[CronTrigger]:
        """繰り返しパターンからCronTriggerを作成"""
        start_time = schedule.start_time
        
        if schedule.repeat_pattern == RepeatPattern.DAILY:
            return CronTrigger(
                hour=start_time.hour,
                minute=start_time.minute,
                second=start_time.second,
                end_date=schedule.repeat_end_date
            )
        elif schedule.repeat_pattern == RepeatPattern.WEEKLY:
            return CronTrigger(
                day_of_week=start_time.weekday(),
                hour=start_time.hour,
                minute=start_time.minute,
                second=start_time.second,
                end_date=schedule.repeat_end_date
            )
        elif schedule.repeat_pattern == RepeatPattern.WEEKDAYS:
            return CronTrigger(
                day_of_week='mon-fri',
                hour=start_time.hour,
                minute=start_time.minute,
                second=start_time.second,
                end_date=schedule.repeat_end_date
            )
        elif schedule.repeat_pattern == RepeatPattern.WEEKENDS:
            return CronTrigger(
                day_of_week='sat,sun',
                hour=start_time.hour,
                minute=start_time.minute,
                second=start_time.second,
                end_date=schedule.repeat_end_date
            )
        elif schedule.repeat_pattern == RepeatPattern.MONTHLY:
            return CronTrigger(
                day=start_time.day,
                hour=start_time.hour,
                minute=start_time.minute,
                second=start_time.second,
                end_date=schedule.repeat_end_date
            )
        
        return None
    
    def _register_timer_jobs(self, schedule: RecordingSchedule):
        """代替実装でタイマージョブを登録"""
        next_execution = schedule.get_next_execution_time()
        if not next_execution:
            return
        
        delay = (next_execution - datetime.now()).total_seconds()
        if delay > 0:
            timer = threading.Timer(delay, self._execute_recording, args=[schedule.schedule_id])
            timer.start()
            self.timers[f"recording_{schedule.schedule_id}"] = timer
        
        # 通知タイマー
        if schedule.notification_enabled:
            for minutes_before in schedule.notification_minutes:
                notification_time = next_execution - timedelta(minutes=minutes_before)
                delay = (notification_time - datetime.now()).total_seconds()
                if delay > 0:
                    timer = threading.Timer(
                        delay, 
                        self._send_notification, 
                        args=[schedule.schedule_id, minutes_before]
                    )
                    timer.start()
                    self.timers[f"notification_{schedule.schedule_id}_{minutes_before}"] = timer
    
    def _register_active_schedules(self):
        """アクティブなスケジュールをすべて登録"""
        with self.lock:
            for schedule in self.schedules.values():
                if schedule.status == ScheduleStatus.ACTIVE:
                    self._register_schedule_jobs(schedule)
    
    def _execute_recording(self, schedule_id: str):
        """録音を実行"""
        try:
            with self.lock:
                schedule = self.schedules.get(schedule_id)
            
            if not schedule or schedule.status != ScheduleStatus.ACTIVE:
                return
            
            self.logger.info(f"録音実行: {schedule_id}")
            
            # 録音コールバックを呼び出し
            if self.recording_callback:
                self.recording_callback(schedule)
            
            # 実行記録を更新
            schedule.last_executed = datetime.now()
            schedule.execution_count += 1
            
            # 繰り返しの場合は次の実行をスケジュール
            if schedule.repeat_pattern != RepeatPattern.NONE:
                next_execution = schedule.get_next_execution_time()
                if next_execution:
                    self._register_schedule_jobs(schedule)
                else:
                    # 繰り返し終了
                    schedule.status = ScheduleStatus.COMPLETED
            else:
                # 単発の場合は完了
                schedule.status = ScheduleStatus.COMPLETED
            
            # データベースを更新
            self._save_schedule(schedule)
            
        except Exception as e:
            self.logger.error(f"録音実行エラー {schedule_id}: {e}")
    
    def _execute_schedule(self, schedule_id: str):
        """スケジュールを実行（_execute_recordingのエイリアス）"""
        self._execute_recording(schedule_id)
    
    def _send_notification(self, schedule_id: str, minutes_before: int):
        """録音前通知を送信"""
        try:
            with self.lock:
                schedule = self.schedules.get(schedule_id)
            
            if not schedule or schedule.status != ScheduleStatus.ACTIVE:
                return
            
            message = f"録音予定: {schedule.program_title} ({minutes_before}分前)"
            
            if self.notification_callback:
                self.notification_callback(message, schedule)
            
            self.logger.info(f"通知送信: {message}")
            
        except Exception as e:
            self.logger.error(f"通知送信エラー: {e}")
    
    def _job_listener(self, event):
        """ジョブ実行イベントリスナー"""
        if event.exception:
            self.logger.error(f"スケジュールジョブエラー: {event.exception}")
    
    def get_schedule(self, schedule_id: str) -> Optional[RecordingSchedule]:
        """スケジュールを取得"""
        with self.lock:
            return self.schedules.get(schedule_id)
    
    def list_schedules(self, 
                      status: Optional[ScheduleStatus] = None,
                      station_id: Optional[str] = None,
                      repeat_pattern: Optional[RepeatPattern] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> List[RecordingSchedule]:
        """スケジュール一覧を取得"""
        with self.lock:
            schedules = list(self.schedules.values())
        
        # フィルタリング
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        if station_id:
            schedules = [s for s in schedules if s.station_id == station_id]
        
        if repeat_pattern:
            schedules = [s for s in schedules if s.repeat_pattern == repeat_pattern]
        
        if start_date:
            schedules = [s for s in schedules if s.start_time >= start_date]
        
        if end_date:
            schedules = [s for s in schedules if s.start_time <= end_date]
        
        # 開始時刻でソート
        schedules.sort(key=lambda x: x.start_time)
        
        return schedules
    
    def update_schedule(self, schedule_or_id, **kwargs) -> bool:
        """スケジュールを更新"""
        with self.lock:
            # RecordingScheduleオブジェクトが渡された場合
            if isinstance(schedule_or_id, RecordingSchedule):
                updated_schedule = schedule_or_id
                schedule_id = updated_schedule.schedule_id
                existing_schedule = self.schedules.get(schedule_id)
                if not existing_schedule:
                    return False
                
                # 既存ジョブを削除
                self._remove_schedule_jobs(schedule_id)
                
                # スケジュールを置き換え
                self.schedules[schedule_id] = updated_schedule
                
                # データベースを更新
                self._save_schedule(updated_schedule)
                
                # 新しいジョブを登録
                if updated_schedule.status == ScheduleStatus.ACTIVE:
                    self._register_schedule_jobs(updated_schedule)
                
                return True
            else:
                # 文字列のschedule_idが渡された場合
                schedule_id = schedule_or_id
                schedule = self.schedules.get(schedule_id)
                if not schedule:
                    return False
                
                # 既存ジョブを削除
                self._remove_schedule_jobs(schedule_id)
                
                # 属性を更新
                for key, value in kwargs.items():
                    if hasattr(schedule, key):
                        setattr(schedule, key, value)
                
                # データベースを更新
                self._save_schedule(schedule)
                
                # 新しいジョブを登録
                if schedule.status == ScheduleStatus.ACTIVE:
                    self._register_schedule_jobs(schedule)
                
                return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """スケジュールを削除"""
        try:
            with self.lock:
                if schedule_id not in self.schedules:
                    self.logger.warning(f"削除対象のスケジュールが見つかりません: {schedule_id}")
                    return False
                
                # ジョブを削除
                self._remove_schedule_jobs(schedule_id)
                
                # メモリから削除
                del self.schedules[schedule_id]
            
            # データベースから削除
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
                conn.commit()
            
            self.logger.info(f"スケジュール削除: {schedule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"スケジュール削除エラー: {e}")
            return False
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """スケジュールを削除（delete_scheduleのエイリアス）"""
        return self.delete_schedule(schedule_id)
    
    def enable_schedule(self, schedule_id: str) -> bool:
        """スケジュールを有効にする"""
        try:
            with self.lock:
                schedule = self.schedules.get(schedule_id)
                if not schedule:
                    self.logger.warning(f"スケジュールが見つかりません: {schedule_id}")
                    return False
                
                if schedule.enabled:
                    self.logger.info(f"スケジュールは既に有効です: {schedule_id}")
                    return True
                
                # スケジュールを有効にする
                schedule.enabled = True
                schedule.status = ScheduleStatus.ACTIVE
                
                # データベースを更新
                self._save_schedule(schedule)
                
                # ジョブを再登録
                self._register_schedule_jobs(schedule)
                
                self.logger.info(f"スケジュールを有効にしました: {schedule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"スケジュール有効化エラー: {e}")
            return False
    
    def disable_schedule(self, schedule_id: str) -> bool:
        """スケジュールを無効にする"""
        try:
            with self.lock:
                schedule = self.schedules.get(schedule_id)
                if not schedule:
                    self.logger.warning(f"スケジュールが見つかりません: {schedule_id}")
                    return False
                
                if not schedule.enabled:
                    self.logger.info(f"スケジュールは既に無効です: {schedule_id}")
                    return True
                
                # スケジュールを無効にする
                schedule.enabled = False
                schedule.status = ScheduleStatus.INACTIVE
                
                # 関連するジョブを削除
                self._remove_schedule_jobs(schedule_id)
                
                # データベースを更新
                self._save_schedule(schedule)
                
                self.logger.info(f"スケジュールを無効にしました: {schedule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"スケジュール無効化エラー: {e}")
            return False
    
    def _remove_schedule_jobs(self, schedule_id: str):
        """スケジュールに関連するジョブを削除"""
        if self.scheduler:
            # APSchedulerからジョブを削除
            try:
                self.scheduler.remove_job(f"recording_{schedule_id}")
            except:
                pass
            
            # 通知ジョブも削除
            for minutes in [1, 5, 10, 15, 30, 60]:  # 一般的な通知時間
                try:
                    self.scheduler.remove_job(f"notification_{schedule_id}_{minutes}")
                except:
                    pass
        else:
            # タイマーを削除
            timers_to_cancel = [
                key for key in self.timers.keys() 
                if key.startswith(f"recording_{schedule_id}") or 
                   key.startswith(f"notification_{schedule_id}")
            ]
            
            for timer_key in timers_to_cancel:
                timer = self.timers.pop(timer_key, None)
                if timer:
                    timer.cancel()
    
    def check_conflicts(self, schedule: RecordingSchedule) -> List[ScheduleConflict]:
        """スケジュール競合をチェック"""
        conflicts = []
        
        with self.lock:
            for other_schedule in self.schedules.values():
                if (other_schedule.schedule_id == schedule.schedule_id or 
                    other_schedule.status != ScheduleStatus.ACTIVE):
                    continue
                
                # 時間の重複をチェック
                overlap = self._check_time_overlap(schedule, other_schedule)
                if overlap:
                    conflicts.append(overlap)
        
        return conflicts
    
    def detect_conflicts(self) -> List[DetectedConflict]:
        """すべてのスケジュール間の競合を検出"""
        conflicts = []
        
        with self.lock:
            schedule_list = list(self.schedules.values())
            
            # すべてのスケジュールペアをチェック
            for i in range(len(schedule_list)):
                for j in range(i + 1, len(schedule_list)):
                    schedule1 = schedule_list[i]
                    schedule2 = schedule_list[j]
                    
                    # 両方ともアクティブなスケジュールのみチェック
                    if (schedule1.status == ScheduleStatus.ACTIVE and 
                        schedule2.status == ScheduleStatus.ACTIVE):
                        
                        # 時間の重複をチェック
                        overlap = self._check_time_overlap(schedule1, schedule2)
                        if overlap:
                            conflicts.append(DetectedConflict(
                                schedule1=schedule1,
                                schedule2=schedule2,
                                overlap_start=overlap.overlap_start,
                                overlap_end=overlap.overlap_end,
                                duration_minutes=overlap.duration_minutes
                            ))
        
        return conflicts
    
    def _check_time_overlap(self, 
                          schedule1: RecordingSchedule, 
                          schedule2: RecordingSchedule) -> Optional[ScheduleConflict]:
        """2つのスケジュール間の時間重複をチェック"""
        
        # 単純な重複チェック（同日のみ）
        if schedule1.start_time.date() == schedule2.start_time.date():
            overlap_start = max(schedule1.start_time, schedule2.start_time)
            overlap_end = min(schedule1.end_time, schedule2.end_time)
            
            if overlap_start < overlap_end:
                duration_minutes = int((overlap_end - overlap_start).total_seconds() / 60)
                return ScheduleConflict(
                    schedule1_id=schedule1.schedule_id,
                    schedule2_id=schedule2.schedule_id,
                    overlap_start=overlap_start,
                    overlap_end=overlap_end,
                    duration_minutes=duration_minutes
                )
        
        return None
    
    def get_upcoming_recordings(self, hours: int = 24) -> List[Dict[str, Any]]:
        """今後の録音予定を取得"""
        now = datetime.now()
        until = now + timedelta(hours=hours)
        
        upcoming = []
        
        with self.lock:
            for schedule in self.schedules.values():
                if schedule.status != ScheduleStatus.ACTIVE:
                    continue
                
                next_execution = schedule.get_next_execution_time(now)
                if next_execution and next_execution <= until:
                    upcoming.append({
                        'schedule': schedule,
                        'next_execution': next_execution,
                        'time_until': next_execution - now
                    })
        
        # 実行時刻でソート
        upcoming.sort(key=lambda x: x['next_execution'])
        
        return upcoming
    
    def get_next_schedules(self, hours: int = 24) -> List[RecordingSchedule]:
        """次回実行予定のスケジュールを取得"""
        now = datetime.now()
        until = now + timedelta(hours=hours)
        
        next_schedules = []
        
        with self.lock:
            for schedule in self.schedules.values():
                if schedule.status != ScheduleStatus.ACTIVE:
                    continue
                
                next_execution = schedule.get_next_execution_time(now)
                if next_execution and next_execution <= until:
                    next_schedules.append(schedule)
        
        # 実行時刻でソート
        next_schedules.sort(key=lambda x: x.get_next_execution_time(now))
        
        return next_schedules
    
    def export_schedules(self, file_path: str) -> bool:
        """スケジュール一覧をJSONファイルにエクスポート"""
        try:
            with self.lock:
                schedules = list(self.schedules.values())
            
            # スケジュールを辞書リストに変換
            export_data = []
            for schedule in schedules:
                export_data.append(schedule.to_dict())
            
            # JSONファイルに保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"スケジュール一覧をエクスポート: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"スケジュールエクスポートエラー: {e}")
            return False
    
    def _save_schedules(self) -> bool:
        """すべてのスケジュールをデータベースに保存"""
        try:
            with self.lock:
                schedules = list(self.schedules.values())
            
            with sqlite3.connect(str(self.db_path)) as conn:
                for schedule in schedules:
                    # 同じロジックを使用してスケジュールを保存
                    conn.execute('''
                        INSERT OR REPLACE INTO schedules 
                        (id, station_id, program_title, start_time, end_time, 
                         repeat_pattern, repeat_end_date, status, format, bitrate,
                         notification_enabled, notification_minutes, created_at,
                         last_executed, execution_count, notes, enabled, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        schedule.schedule_id,
                        schedule.station_id,
                        schedule.program_title,
                        schedule.start_time.isoformat(),
                        schedule.end_time.isoformat(),
                        schedule.repeat_pattern.value,
                        schedule.repeat_end_date.isoformat() if schedule.repeat_end_date else None,
                        schedule.status.value,
                        schedule.format,
                        schedule.bitrate,
                        schedule.notification_enabled,
                        json.dumps(schedule.notification_minutes),
                        schedule.created_at.isoformat(),
                        schedule.last_executed.isoformat() if schedule.last_executed else None,
                        schedule.execution_count,
                        schedule.notes,
                        schedule.enabled,
                        json.dumps(schedule.tags)
                    ))
                conn.commit()
            
            self.logger.info(f"全スケジュールをデータベースに保存: {len(schedules)} 件")
            return True
            
        except Exception as e:
            self.logger.error(f"スケジュール一括保存エラー: {e}")
            return False
    
    def set_recording_callback(self, callback: Callable[[RecordingSchedule], None]):
        """録音実行コールバックを設定"""
        self.recording_callback = callback
    
    def set_notification_callback(self, callback: Callable[[str, RecordingSchedule], None]):
        """通知コールバックを設定"""
        self.notification_callback = callback
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self.lock:
            schedules = list(self.schedules.values())
        
        total_schedules = len(schedules)
        active_schedules = len([s for s in schedules if s.status == ScheduleStatus.SCHEDULED])
        completed_schedules = len([s for s in schedules if s.status == ScheduleStatus.COMPLETED])
        
        # 放送局別統計
        station_stats = {}
        for schedule in schedules:
            station = schedule.station_id
            if station not in station_stats:
                station_stats[station] = {'count': 0}
            station_stats[station]['count'] += 1
        
        # 繰り返しパターン統計
        pattern_stats = {}
        for schedule in schedules:
            pattern = schedule.repeat_pattern.value
            if pattern not in pattern_stats:
                pattern_stats[pattern] = 0
            pattern_stats[pattern] += 1
        
        # ステータス別統計
        status_stats = {}
        for schedule in schedules:
            status = schedule.status.value
            if status not in status_stats:
                status_stats[status] = 0
            status_stats[status] += 1
        
        return {
            'total_schedules': total_schedules,
            'active_schedules': active_schedules,
            'completed_schedules': completed_schedules,
            'stations': station_stats,
            'repeat_patterns': pattern_stats,
            'status_breakdown': status_stats
        }
    
    def pause(self):
        """スケジューラーを一時停止"""
        self.logger.info("スケジューラーを一時停止中...")
        
        if self.scheduler:
            self.scheduler.pause()
        
        # タイマーをキャンセル
        for timer in self.timers.values():
            timer.cancel()
        
        self.logger.info("スケジューラーを一時停止しました")
    
    def resume(self):
        """スケジューラーを再開"""
        self.logger.info("スケジューラーを再開中...")
        
        if self.scheduler:
            self.scheduler.resume()
        
        # スケジュールを再実行
        self._reschedule_all()
        
        self.logger.info("スケジューラーを再開しました")
    
    def shutdown(self):
        """スケジューラーを終了"""
        self.logger.info("スケジューラーを終了中...")
        
        if self.scheduler:
            self.scheduler.shutdown()
        
        # タイマーをキャンセル
        for timer in self.timers.values():
            timer.cancel()
        self.timers.clear()
        
        self.logger.info("スケジューラーを終了しました")
    
    def _reschedule_all(self):
        """全てのスケジュールを再スケジュール"""
        with self.lock:
            for schedule in self.schedules.values():
                if schedule.enabled:
                    try:
                        self._schedule_recording(schedule)
                    except Exception as e:
                        self.logger.error(f"スケジュール再設定エラー {schedule.schedule_id}: {e}")


class SchedulerError(Exception):
    """スケジューラーエラーの例外クラス"""
    pass


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
        # スケジューラーのテスト
        scheduler = RecordingScheduler()
        
        # テスト用コールバック
        def recording_callback(schedule: RecordingSchedule):
            print(f"録音実行: {schedule.program_title} ({schedule.station_id})")
        
        def notification_callback(message: str, schedule: RecordingSchedule):
            print(f"通知: {message}")
        
        scheduler.set_recording_callback(recording_callback)
        scheduler.set_notification_callback(notification_callback)
        
        # テストスケジュールを追加
        now = datetime.now()
        test_time = now + timedelta(minutes=2)
        
        schedule_id = scheduler.add_schedule(
            station_id="TBS",
            program_title="テスト番組",
            start_time=test_time,
            end_time=test_time + timedelta(minutes=30),
            repeat_pattern=RepeatPattern.NONE,
            notification_enabled=True,
            notification_minutes=[1]
        )
        
        print(f"テストスケジュール追加: {schedule_id}")
        
        # 予定一覧を表示
        upcoming = scheduler.get_upcoming_recordings(24)
        print(f"今後の録音予定: {len(upcoming)} 件")
        
        for item in upcoming:
            schedule = item['schedule']
            next_time = item['next_execution']
            print(f"  {schedule.program_title} - {next_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 統計情報を表示
        stats = scheduler.get_statistics()
        print(f"統計情報: アクティブ {stats['active_schedules']} / 総計 {stats['total_schedules']}")
        
        # しばらく待機（テスト実行を確認）
        print("録音とnotifications をテスト中... (5分間待機)")
        time.sleep(300)
        
        # 終了処理
        scheduler.shutdown()
        
    except Exception as e:
        print(f"スケジューラーテストエラー: {e}")
        sys.exit(1)
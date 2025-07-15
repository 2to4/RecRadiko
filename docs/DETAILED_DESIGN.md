# RecRadiko対話型インターフェース 詳細設計書
## バージョン 2.0 - クラス・メソッド詳細仕様

---

## 1. 詳細設計概要

### 1.1 設計目標
概要設計で定義したアーキテクチャを基に、実装可能レベルまでクラス・メソッド・データ構造を詳細化し、開発チームが一貫性を持って実装できる仕様を提供する。

### 1.2 実装方針
- **SOLID原則**: 単一責任・開放閉鎖・依存性逆転の遵守
- **デザインパターン**: State・Strategy・Templateメソッドパターンの活用
- **エラーハンドリング**: 例外安全性とグレースフルデグラデーション
- **テスタビリティ**: Mock化・依存注入による単体テスト容易性

---

## 2. コアクラス詳細設計

### 2.1 MenuManager クラス

#### 2.1.1 クラス仕様
```python
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
import logging
from enum import Enum

class NavigationAction(Enum):
    """画面遷移アクション"""
    PUSH = "push"           # 新しい画面にスタック
    POP = "pop"             # 前の画面に戻る
    REPLACE = "replace"     # 現在画面を置き換え
    RESET = "reset"         # スタックをクリアして新画面
    EXIT = "exit"           # アプリケーション終了

@dataclass
class NavigationResult:
    """画面遷移結果"""
    action: NavigationAction
    screen_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    exit_code: int = 0

class MenuManager:
    """メニュー管理・画面遷移制御クラス"""
    
    def __init__(self, session_manager: 'SessionManager', ui_service: 'UIService'):
        self.session_manager = session_manager
        self.ui_service = ui_service
        self.screen_registry: Dict[str, type] = {}
        self.screen_stack: List[str] = []
        self.current_screen: Optional['ScreenBase'] = None
        self.global_context: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
    def register_screen(self, screen_id: str, screen_class: type) -> None:
        """
        画面クラスを登録
        
        Args:
            screen_id: 画面識別子 ('main_menu', 'station_select' など)
            screen_class: ScreenBase継承クラス
            
        Raises:
            ValueError: 重複したscreen_idの場合
        """
        if screen_id in self.screen_registry:
            raise ValueError(f"Screen ID '{screen_id}' is already registered")
            
        if not issubclass(screen_class, ScreenBase):
            raise TypeError(f"Screen class must inherit from ScreenBase")
            
        self.screen_registry[screen_id] = screen_class
        self.logger.debug(f"Registered screen: {screen_id}")
        
    def navigate_to(self, screen_id: str, 
                   action: NavigationAction = NavigationAction.PUSH,
                   context: Optional[Dict[str, Any]] = None) -> None:
        """
        指定画面に遷移
        
        Args:
            screen_id: 遷移先画面ID
            action: 遷移アクション
            context: 遷移時に渡すコンテキストデータ
            
        Raises:
            ValueError: 未登録のscreen_idの場合
        """
        if screen_id not in self.screen_registry:
            raise ValueError(f"Unknown screen ID: {screen_id}")
            
        # 現在画面の状態保存
        if self.current_screen:
            self.session_manager.save_screen_state(
                self.current_screen.__class__.__name__.lower(),
                self.current_screen.get_state()
            )
            
        # 画面スタック操作
        if action == NavigationAction.PUSH:
            if self.current_screen:
                self.screen_stack.append(self.current_screen.__class__.__name__.lower())
        elif action == NavigationAction.POP:
            if self.screen_stack:
                screen_id = self.screen_stack.pop()
        elif action == NavigationAction.RESET:
            self.screen_stack.clear()
            
        # 新画面インスタンス作成
        screen_class = self.screen_registry[screen_id]
        self.current_screen = screen_class(
            session_manager=self.session_manager,
            ui_service=self.ui_service,
            context=context or {}
        )
        
        # 画面状態復元
        saved_state = self.session_manager.load_screen_state(screen_id)
        if saved_state:
            self.current_screen.restore_state(saved_state)
            
        self.logger.info(f"Navigated to screen: {screen_id}")
        
    def go_back(self) -> bool:
        """
        前画面に戻る
        
        Returns:
            bool: 戻り操作が成功したかどうか
        """
        if not self.screen_stack:
            return False
            
        previous_screen_id = self.screen_stack.pop()
        self.navigate_to(previous_screen_id, NavigationAction.REPLACE)
        return True
        
    def run(self) -> int:
        """
        メインループ実行
        
        Returns:
            int: 終了コード (0: 正常終了, 1: エラー終了)
        """
        try:
            # 初期画面設定
            self.navigate_to('main_menu', NavigationAction.RESET)
            
            while self.current_screen:
                try:
                    # 画面表示
                    self.current_screen.display()
                    
                    # ユーザー入力受付
                    user_input = self.ui_service.get_user_input()
                    
                    # 入力処理
                    result = self.current_screen.handle_input(user_input)
                    
                    # 画面遷移処理
                    if result.action == NavigationAction.EXIT:
                        break
                    elif result.screen_id:
                        self.navigate_to(result.screen_id, result.action, result.context)
                        
                except KeyboardInterrupt:
                    self.logger.info("User interrupted with Ctrl+C")
                    if self.ui_service.confirm_exit():
                        break
                except Exception as e:
                    self.logger.error(f"Screen error: {e}")
                    self.ui_service.display_error(
                        "予期しないエラーが発生しました。メインメニューに戻ります。",
                        str(e)
                    )
                    self.navigate_to('main_menu', NavigationAction.RESET)
                    
            return 0
            
        except Exception as e:
            self.logger.critical(f"Critical error in main loop: {e}")
            return 1
        finally:
            # セッション状態保存
            self.session_manager.save_session()
```

### 2.2 ScreenBase 基底クラス

#### 2.2.1 基底クラス仕様
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import logging

class ScreenBase(ABC):
    """画面基底クラス - 全画面共通機能・インターフェース"""
    
    def __init__(self, session_manager: 'SessionManager', 
                 ui_service: 'UIService', 
                 context: Optional[Dict[str, Any]] = None):
        self.session_manager = session_manager
        self.ui_service = ui_service
        self.context = context or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 画面共通プロパティ
        self.title = ""
        self.subtitle = ""
        self.options: List[MenuOption] = []
        self.common_options: Dict[str, str] = {
            "99": "メインメニューに戻る",
            "0": "終了"
        }
        
        # 画面状態
        self.is_loaded = False
        self.error_message = ""
        self.info_message = ""
        
    @abstractmethod
    def load_data(self) -> None:
        """画面データ読み込み - サブクラスで実装必須"""
        pass
        
    @abstractmethod
    def build_options(self) -> List[MenuOption]:
        """選択肢構築 - サブクラスで実装必須"""
        pass
        
    @abstractmethod
    def handle_input(self, user_input: str) -> NavigationResult:
        """入力処理 - サブクラスで実装必須"""
        pass
        
    def display(self) -> None:
        """画面表示 - テンプレートメソッドパターン"""
        try:
            # データ読み込み（初回のみ）
            if not self.is_loaded:
                self.load_data()
                self.is_loaded = True
                
            # 選択肢構築
            self.options = self.build_options()
            
            # 画面クリア
            self.ui_service.clear_screen()
            
            # ヘッダー表示
            self._display_header()
            
            # メッセージ表示
            self._display_messages()
            
            # 選択肢表示
            self._display_options()
            
            # フッター表示
            self._display_footer()
            
        except Exception as e:
            self.logger.error(f"Display error: {e}")
            self.ui_service.display_error("画面表示エラーが発生しました", str(e))
            
    def _display_header(self) -> None:
        """ヘッダー表示"""
        self.ui_service.display_header(self.title, self.subtitle)
        
    def _display_messages(self) -> None:
        """メッセージ表示"""
        if self.error_message:
            self.ui_service.display_error_message(self.error_message)
            self.error_message = ""  # 一度表示したらクリア
            
        if self.info_message:
            self.ui_service.display_info_message(self.info_message)
            self.info_message = ""
            
    def _display_options(self) -> None:
        """選択肢表示"""
        self.ui_service.display_options(self.options + self._build_common_options())
        
    def _display_footer(self) -> None:
        """フッター表示"""
        self.ui_service.display_input_prompt()
        
    def _build_common_options(self) -> List[MenuOption]:
        """共通選択肢構築"""
        return [
            MenuOption(number=num, label=label) 
            for num, label in self.common_options.items()
        ]
        
    def validate_input(self, user_input: str) -> Tuple[bool, str]:
        """
        入力検証
        
        Args:
            user_input: ユーザー入力文字列
            
        Returns:
            Tuple[is_valid, error_message]
        """
        # 基本検証
        if not user_input.strip():
            return False, "入力が空です。番号を入力してください。"
            
        # 数字検証
        if not user_input.isdigit():
            return False, "数字を入力してください。"
            
        # 範囲検証
        option_numbers = [opt.number for opt in self.options] + list(self.common_options.keys())
        if user_input not in option_numbers:
            valid_options = ", ".join(sorted(option_numbers, key=int))
            return False, f"有効な選択肢 ({valid_options}) を入力してください。"
            
        return True, ""
        
    def get_state(self) -> Dict[str, Any]:
        """画面状態取得 - セッション保存用"""
        return {
            "context": self.context,
            "is_loaded": self.is_loaded,
            "class_name": self.__class__.__name__
        }
        
    def restore_state(self, state: Dict[str, Any]) -> None:
        """画面状態復元 - セッション復元用"""
        self.context = state.get("context", {})
        self.is_loaded = state.get("is_loaded", False)
        
    def set_error_message(self, message: str) -> None:
        """エラーメッセージ設定"""
        self.error_message = message
        self.logger.warning(f"Error message set: {message}")
        
    def set_info_message(self, message: str) -> None:
        """情報メッセージ設定"""
        self.info_message = message
        self.logger.info(f"Info message set: {message}")
```

#### 2.2.2 データクラス定義
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class MenuOption:
    """メニュー選択肢データクラス"""
    number: str                    # 選択番号 ("1", "2", ...)
    label: str                     # 表示ラベル
    description: Optional[str] = None  # 詳細説明（オプション）
    enabled: bool = True           # 選択可能かどうか
    icon: Optional[str] = None     # アイコン文字（将来拡張用）
    
    def __post_init__(self):
        """バリデーション"""
        if not self.number or not self.label:
            raise ValueError("number and label are required")
```

### 2.3 具体画面クラス詳細設計

#### 2.3.1 MainMenuScreen クラス
```python
class MainMenuScreen(ScreenBase):
    """メインメニュー画面"""
    
    def __init__(self, session_manager: 'SessionManager', 
                 ui_service: 'UIService', 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(session_manager, ui_service, context)
        self.title = "RecRadiko タイムフリー録音システム"
        self.subtitle = f"バージョン 2.0 - メニュー駆動型UI"
        
    def load_data(self) -> None:
        """データ読み込み - システム状態確認"""
        try:
            # 認証状態確認
            auth_status = self.session_manager.get_auth_status()
            
            # 設定状態確認
            config_status = self.session_manager.get_config_status()
            
            # システム情報をコンテキストに保存
            self.context.update({
                "auth_status": auth_status,
                "config_status": config_status,
                "system_ready": auth_status and config_status
            })
            
        except Exception as e:
            self.logger.error(f"Failed to load system status: {e}")
            self.set_error_message("システム状態の確認に失敗しました")
            
    def build_options(self) -> List[MenuOption]:
        """選択肢構築"""
        options = [
            MenuOption("1", "番組録音 (放送局→日付→番組選択)", 
                      "過去1週間のタイムフリー番組録音"),
            MenuOption("2", "番組検索・一覧表示", 
                      "番組名・出演者による検索"),
            MenuOption("3", "録音履歴表示", 
                      "過去の録音結果確認"),
            MenuOption("4", "設定管理", 
                      "地域・音質・保存先設定"),
            MenuOption("5", "システム情報", 
                      "バージョン・API状況・統計情報")
        ]
        
        # システム状態に応じて選択肢を無効化
        if not self.context.get("system_ready", False):
            options[0].enabled = False
            options[0].description = "設定または認証が必要です"
            
        return options
        
    def handle_input(self, user_input: str) -> NavigationResult:
        """入力処理"""
        # 入力検証
        is_valid, error_msg = self.validate_input(user_input)
        if not is_valid:
            self.set_error_message(error_msg)
            return NavigationResult(NavigationAction.REPLACE, "main_menu")
            
        # 共通選択肢処理
        if user_input == "0":
            return NavigationResult(NavigationAction.EXIT)
            
        # メニュー選択処理
        menu_map = {
            "1": ("station_select", {"from_main": True}),
            "2": ("search_screen", {}),
            "3": ("history_screen", {}),
            "4": ("settings_screen", {}),
            "5": ("info_screen", {})
        }
        
        if user_input in menu_map:
            screen_id, context = menu_map[user_input]
            
            # システム準備状態チェック（録音機能の場合）
            if user_input == "1" and not self.context.get("system_ready", False):
                self.set_error_message("録音機能を使用するには設定と認証が必要です。[4] 設定管理で設定してください。")
                return NavigationResult(NavigationAction.REPLACE, "main_menu")
                
            return NavigationResult(NavigationAction.PUSH, screen_id, context)
            
        # 予期しない入力（バリデーション通過後なので通常発生しない）
        self.set_error_message(f"未実装の機能です: {user_input}")
        return NavigationResult(NavigationAction.REPLACE, "main_menu")
```

#### 2.3.2 StationSelectScreen クラス
```python
from typing import List, Dict, Any, Optional

class StationSelectScreen(ScreenBase):
    """放送局選択画面"""
    
    def __init__(self, session_manager: 'SessionManager', 
                 ui_service: 'UIService', 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(session_manager, ui_service, context)
        self.title = "Step 1/3: 放送局選択"
        self.stations: List[Dict[str, Any]] = []
        self.current_region = ""
        
        # 追加共通選択肢
        self.common_options.update({
            "88": "地域変更"
        })
        
    def load_data(self) -> None:
        """放送局データ読み込み"""
        try:
            # 現在地域取得
            self.current_region = self.session_manager.get_current_region()
            
            # 放送局一覧取得
            self.stations = self.ui_service.get_stations_for_region(self.current_region)
            
            # サブタイトル更新
            region_name = self.session_manager.get_region_name(self.current_region)
            self.subtitle = f"現在の地域: {region_name} ({self.current_region})"
            
            self.logger.info(f"Loaded {len(self.stations)} stations for region {self.current_region}")
            
        except Exception as e:
            self.logger.error(f"Failed to load station data: {e}")
            self.set_error_message("放送局情報の取得に失敗しました")
            self.stations = []
            
    def build_options(self) -> List[MenuOption]:
        """放送局選択肢構築"""
        options = []
        
        for i, station in enumerate(self.stations, 1):
            option = MenuOption(
                number=str(i),
                label=station["name"],
                description=station.get("description", ""),
                enabled=station.get("available", True)
            )
            options.append(option)
            
        return options
        
    def handle_input(self, user_input: str) -> NavigationResult:
        """入力処理"""
        # 入力検証
        is_valid, error_msg = self.validate_input(user_input)
        if not is_valid:
            self.set_error_message(error_msg)
            return NavigationResult(NavigationAction.REPLACE, "station_select")
            
        # 共通選択肢処理
        if user_input == "0":
            return NavigationResult(NavigationAction.EXIT)
        elif user_input == "99":
            return NavigationResult(NavigationAction.POP)
        elif user_input == "88":
            return NavigationResult(NavigationAction.PUSH, "region_select")
            
        # 放送局選択処理
        try:
            station_index = int(user_input) - 1
            if 0 <= station_index < len(self.stations):
                selected_station = self.stations[station_index]
                
                # 選択状態保存
                self.session_manager.set_selected_station(
                    selected_station["id"], 
                    selected_station["name"]
                )
                
                # 次画面へ遷移
                context = {
                    "station_id": selected_station["id"],
                    "station_name": selected_station["name"],
                    "from_station_select": True
                }
                
                return NavigationResult(NavigationAction.PUSH, "date_select", context)
                
        except (ValueError, IndexError):
            pass
            
        # 予期しない入力
        self.set_error_message(f"無効な選択です: {user_input}")
        return NavigationResult(NavigationAction.REPLACE, "station_select")
```

#### 2.3.3 DateSelectScreen クラス
```python
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class DateSelectScreen(ScreenBase):
    """日付選択画面"""
    
    def __init__(self, session_manager: 'SessionManager', 
                 ui_service: 'UIService', 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(session_manager, ui_service, context)
        self.title = "Step 2/3: 日付選択"
        self.available_dates: List[Dict[str, Any]] = []
        self.station_name = context.get("station_name", "未選択")
        
        # 追加共通選択肢
        self.common_options.update({
            "88": "放送局を変更"
        })
        
    def load_data(self) -> None:
        """利用可能日付データ生成"""
        try:
            # 過去7日間の日付生成（タイムフリー制限）
            today = datetime.now()
            self.available_dates = []
            
            for i in range(7):
                date = today - timedelta(days=i)
                date_info = {
                    "date": date.strftime("%Y-%m-%d"),
                    "display": self._format_date_display(date, i),
                    "weekday": date.strftime("%A"),
                    "available": True  # 将来的にAPI可用性チェック
                }
                self.available_dates.append(date_info)
                
            # サブタイトル更新
            self.subtitle = f"選択された放送局: {self.station_name}"
            
            self.logger.info(f"Generated {len(self.available_dates)} available dates")
            
        except Exception as e:
            self.logger.error(f"Failed to generate date data: {e}")
            self.set_error_message("日付情報の生成に失敗しました")
            self.available_dates = []
            
    def _format_date_display(self, date: datetime, days_ago: int) -> str:
        """日付表示フォーマット"""
        if days_ago == 0:
            return f"{date.strftime('%Y-%m-%d')} (今日)"
        elif days_ago == 1:
            return f"{date.strftime('%Y-%m-%d')} (昨日)"
        else:
            return f"{date.strftime('%Y-%m-%d')} ({days_ago}日前)"
            
    def build_options(self) -> List[MenuOption]:
        """日付選択肢構築"""
        options = []
        
        for i, date_info in enumerate(self.available_dates, 1):
            option = MenuOption(
                number=str(i),
                label=date_info["display"],
                enabled=date_info["available"]
            )
            options.append(option)
            
        return options
        
    def handle_input(self, user_input: str) -> NavigationResult:
        """入力処理"""
        # 入力検証
        is_valid, error_msg = self.validate_input(user_input)
        if not is_valid:
            self.set_error_message(error_msg)
            return NavigationResult(NavigationAction.REPLACE, "date_select")
            
        # 共通選択肢処理
        if user_input == "0":
            return NavigationResult(NavigationAction.EXIT)
        elif user_input == "99":
            return NavigationResult(NavigationAction.POP)
        elif user_input == "88":
            # 放送局選択に戻る
            return NavigationResult(NavigationAction.POP)
            
        # 日付選択処理
        try:
            date_index = int(user_input) - 1
            if 0 <= date_index < len(self.available_dates):
                selected_date = self.available_dates[date_index]
                
                # 選択状態保存
                self.session_manager.set_selected_date(selected_date["date"])
                
                # 次画面へ遷移
                context = {
                    "station_id": self.context.get("station_id"),
                    "station_name": self.context.get("station_name"),
                    "selected_date": selected_date["date"],
                    "from_date_select": True
                }
                
                return NavigationResult(NavigationAction.PUSH, "program_select", context)
                
        except (ValueError, IndexError):
            pass
            
        # 予期しない入力
        self.set_error_message(f"無効な選択です: {user_input}")
        return NavigationResult(NavigationAction.REPLACE, "date_select")
```

---

## 3. サービスクラス詳細設計

### 3.1 UIService クラス

#### 3.1.1 クラス仕様
```python
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

class UIService:
    """UI専用ビジネスロジック・ユーティリティクラス"""
    
    def __init__(self, session_manager: 'SessionManager'):
        self.session_manager = session_manager
        self.terminal_width = self._get_terminal_width()
        self.colors_enabled = self._check_color_support()
        
        # キーボードナビゲーション状態
        self.current_options: List[MenuOption] = []
        self.current_selection_index: int = 0
        self.shortcut_keys: Dict[str, str] = {}
        self.page_size: int = 10
        
    def setup_keyboard_navigation(self, options: List[MenuOption], 
                                shortcut_keys: Optional[Dict[str, str]] = None,
                                initial_selection: int = 0) -> None:
        """キーボードナビゲーション設定"""
        self.current_options = options
        self.current_selection_index = initial_selection
        self.shortcut_keys = shortcut_keys or {}
        
        # 無効な選択肢をスキップ
        self._move_to_enabled_option()
        
    def _move_to_enabled_option(self) -> None:
        """有効な選択肢に移動"""
        start_index = self.current_selection_index
        
        while not self.current_options[self.current_selection_index].enabled:
            self.current_selection_index = (self.current_selection_index + 1) % len(self.current_options)
            
            # 全選択肢が無効な場合は元の位置に戻す
            if self.current_selection_index == start_index:
                break
                
    def get_selected_option(self) -> MenuOption:
        """現在選択中のオプション取得"""
        return self.current_options[self.current_selection_index]
        
    def clear_screen(self) -> None:
        """画面クリア"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """ヘッダー表示"""
        # 区切り線
        separator = "=" * self.terminal_width
        print(separator)
        
        # タイトル中央揃え
        title_line = f"    {title}"
        print(title_line)
        
        # サブタイトル
        if subtitle:
            subtitle_line = f"    {subtitle}"
            print(subtitle_line)
            
        print(separator)
        print()  # 空行
        
    def display_options(self, options: List[MenuOption]) -> None:
        """選択肢一覧表示"""
        for option in options:
            # 有効/無効の表示調整
            status_mark = "" if option.enabled else " (無効)"
            
            # 基本表示
            option_line = f"[{option.number}] {option.label}{status_mark}"
            
            # 説明がある場合
            if option.description:
                # 説明を次行にインデント表示
                print(option_line)
                desc_line = f"    {option.description}"
                print(self._format_with_color(desc_line, "dim"))
            else:
                print(option_line)
                
        print()  # 空行
        
    def display_input_prompt(self) -> None:
        """入力プロンプト表示"""
        prompt = "選択してください: "
        print(prompt, end="", flush=True)
        
    def get_user_input(self) -> str:
        """キーボードナビゲーション対応ユーザー入力取得"""
        try:
            # 現在選択項目表示（ハイライト）
            self.display_selection_state()
            
            # キーボード入力ループ
            while True:
                key = self._get_key()
                
                if key == 'UP':
                    self._move_selection_up()
                elif key == 'DOWN':
                    self._move_selection_down()
                elif key == 'PGUP':
                    self._move_page_up()
                elif key == 'PGDN':
                    self._move_page_down()
                elif key == 'ENTER':
                    return str(self.current_selection_index)
                elif key == 'ESC':
                    return "99"  # 前画面に戻る
                elif key == 'Q':
                    return "0"   # 終了
                elif key.upper() in self.shortcut_keys:
                    return self.shortcut_keys[key.upper()]
                    
                # 選択状態更新表示
                self.update_selection_display()
                
        except (EOFError, KeyboardInterrupt):
            return "0"  # 終了扱い
            
    def _get_key(self) -> str:
        """単一キー入力取得（非ブロッキング）"""
        import sys
        import tty
        import termios
        
        if sys.platform == "win32":
            import msvcrt
            key = msvcrt.getch().decode('utf-8', errors='ignore')
        else:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                key = sys.stdin.read(1)
                
                # ANSI エスケープシーケンス処理
                if key == '\x1b':  # ESC
                    key += sys.stdin.read(2)
                    if key == '\x1b[A':
                        return 'UP'
                    elif key == '\x1b[B':
                        return 'DOWN'
                    elif key == '\x1b[5~':
                        return 'PGUP'
                    elif key == '\x1b[6~':
                        return 'PGDN'
                    else:
                        return 'ESC'
                        
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
        # キーマッピング
        if key == '\r' or key == '\n':
            return 'ENTER'
        elif key == '\x1b':
            return 'ESC'
        elif ord(key) == 3:  # Ctrl+C
            raise KeyboardInterrupt()
        else:
            return key.upper()
            
    def _move_selection_up(self) -> None:
        """選択項目を上に移動"""
        if self.current_selection_index > 0:
            self.current_selection_index -= 1
        else:
            # 循環選択: 最後の項目に移動
            self.current_selection_index = len(self.current_options) - 1
            
    def _move_selection_down(self) -> None:
        """選択項目を下に移動"""
        if self.current_selection_index < len(self.current_options) - 1:
            self.current_selection_index += 1
        else:
            # 循環選択: 最初の項目に移動
            self.current_selection_index = 0
            
    def _move_page_up(self) -> None:
        """ページアップ（10項目上移動）"""
        self.current_selection_index = max(0, self.current_selection_index - 10)
        
    def _move_page_down(self) -> None:
        """ページダウン（10項目下移動）"""
        max_index = len(self.current_options) - 1
        self.current_selection_index = min(max_index, self.current_selection_index + 10)
        
    def display_selection_state(self) -> None:
        """現在の選択状態表示"""
        self.clear_screen()
        self.display_header()
        
        # 選択肢表示（ハイライト付き）
        for i, option in enumerate(self.current_options):
            if i == self.current_selection_index:
                # 選択中項目: → マーク + ハイライト
                line = f"→ {option.label}"
                print(self._format_with_color(line, "highlight"))
            else:
                # 通常項目
                line = f"  {option.label}"
                if not option.enabled:
                    line = self._format_with_color(line, "dim")
                print(line)
                
    def update_selection_display(self) -> None:
        """選択状態のみ部分更新"""
        # カーソル移動による部分更新（フリッカー防止）
        for i, option in enumerate(self.current_options):
            # カーソル位置移動
            print(f"\r\x1b[{i+1}A", end="")
            
            if i == self.current_selection_index:
                line = f"→ {option.label}"
                print(self._format_with_color(line, "highlight"), end="")
            else:
                line = f"  {option.label}"
                if not option.enabled:
                    line = self._format_with_color(line, "dim")
                print(line, end="")
                
        # カーソルを最後の行に戻す
        print(f"\r\x1b[{len(self.current_options)}B", end="")
        sys.stdout.flush()
            
    def display_error_message(self, message: str) -> None:
        """エラーメッセージ表示"""
        error_line = f"❌ エラー: {message}"
        print(self._format_with_color(error_line, "red"))
        print()
        
    def display_info_message(self, message: str) -> None:
        """情報メッセージ表示"""
        info_line = f"ℹ️  {message}"
        print(self._format_with_color(info_line, "blue"))
        print()
        
    def display_success_message(self, message: str) -> None:
        """成功メッセージ表示"""
        success_line = f"✅ {message}"
        print(self._format_with_color(success_line, "green"))
        print()
        
    def display_progress_bar(self, progress: float, message: str = "") -> None:
        """プログレスバー表示"""
        bar_width = min(50, self.terminal_width - 20)
        filled_width = int(bar_width * progress)
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        percentage = int(progress * 100)
        progress_line = f"{bar} {percentage}%"
        
        if message:
            progress_line += f" - {message}"
            
        # キャリッジリターンで同一行更新
        print(f"\r{progress_line}", end="", flush=True)
        
    def confirm_exit(self) -> bool:
        """終了確認"""
        print("\n終了しますか？ (y/N): ", end="", flush=True)
        response = input().strip().lower()
        return response in ['y', 'yes', 'はい']
        
    def display_error(self, title: str, details: str) -> None:
        """詳細エラー表示"""
        self.clear_screen()
        self.display_header("エラーが発生しました")
        
        print(f"エラー内容: {title}")
        print(f"詳細: {details}")
        print()
        print("任意のキーを押してください...")
        input()
        
    def get_stations_for_region(self, region_id: str) -> List[Dict[str, Any]]:
        """地域別放送局一覧取得"""
        # 既存サービスへの委譲
        from src.program_info import ProgramInfo
        program_info = ProgramInfo()
        
        stations = program_info.get_stations_for_area(region_id)
        return [
            {
                "id": station.get("id"),
                "name": station.get("name"),
                "description": station.get("description", ""),
                "available": True
            }
            for station in stations
        ]
        
    def get_programs_for_date(self, station_id: str, date: str) -> List[Dict[str, Any]]:
        """指定日の番組一覧取得"""
        # 既存サービスへの委譲
        from src.program_history import ProgramHistoryManager
        history_manager = ProgramHistoryManager()
        
        programs = history_manager.get_programs_by_date(station_id, date)
        return [
            {
                "id": program.get("id"),
                "title": program.get("title"),
                "start_time": program.get("start_time"),
                "end_time": program.get("end_time"),
                "duration": program.get("duration"),
                "cast": program.get("cast", ""),
                "description": program.get("description", "")
            }
            for program in programs
        ]
        
    def _get_terminal_width(self) -> int:
        """ターミナル幅取得"""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80  # デフォルト幅
            
    def _check_color_support(self) -> bool:
        """カラー出力サポート確認"""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        
    def _format_with_color(self, text: str, color: str) -> str:
        """カラーフォーマット適用"""
        if not self.colors_enabled:
            return text
            
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "blue": "\033[94m",
            "dim": "\033[2m",
            "highlight": "\033[7m",      # 反転表示（ハイライト）
            "bold": "\033[1m",           # 太字
            "underline": "\033[4m",      # 下線
            "reset": "\033[0m"
        }
        
        color_code = colors.get(color, "")
        reset_code = colors["reset"]
        
        return f"{color_code}{text}{reset_code}"
```

### 3.2 SessionManager クラス

#### 3.2.1 クラス仕様
```python
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

class SessionManager:
    """セッション・状態管理クラス"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".recradiko"
        self.config_dir.mkdir(exist_ok=True)
        
        self.session_file = self.config_dir / "session.json"
        self.state_file = self.config_dir / "ui_state.json"
        
        # セッションデータ
        self.session_data = self._load_session()
        self.ui_state = self._load_ui_state()
        
        # 現在のユーザー選択
        self.current_selection = UserSelection()
        
    def _load_session(self) -> Dict[str, Any]:
        """セッションデータ読み込み"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # セッションの有効性確認
                session_time = datetime.fromisoformat(data.get("last_activity", ""))
                if datetime.now() - session_time < timedelta(hours=1):
                    return data
                    
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load session: {e}")
            
        # デフォルトセッション
        return {
            "session_id": self._generate_session_id(),
            "start_time": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "user_preferences": {}
        }
        
    def _load_ui_state(self) -> Dict[str, Any]:
        """UI状態データ読み込み"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load UI state: {e}")
            
        return {"screen_states": {}, "navigation_history": []}
        
    def save_session(self) -> None:
        """セッションデータ保存"""
        try:
            self.session_data["last_activity"] = datetime.now().isoformat()
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save session: {e}")
            
    def save_ui_state(self) -> None:
        """UI状態保存"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.ui_state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save UI state: {e}")
            
    def save_screen_state(self, screen_id: str, state: Dict[str, Any]) -> None:
        """画面状態保存"""
        self.ui_state["screen_states"][screen_id] = {
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
        self.save_ui_state()
        
    def load_screen_state(self, screen_id: str) -> Optional[Dict[str, Any]]:
        """画面状態読み込み"""
        screen_data = self.ui_state["screen_states"].get(screen_id)
        if screen_data:
            return screen_data.get("state")
        return None
        
    def set_selected_station(self, station_id: str, station_name: str) -> None:
        """選択放送局設定"""
        self.current_selection.station_id = station_id
        self.current_selection.station_name = station_name
        
    def set_selected_date(self, date: str) -> None:
        """選択日付設定"""
        self.current_selection.selected_date = date
        
    def set_selected_program(self, program: Dict[str, Any]) -> None:
        """選択番組設定"""
        self.current_selection.selected_program = program
        
    def get_current_selection(self) -> 'UserSelection':
        """現在の選択状態取得"""
        return self.current_selection
        
    def get_current_region(self) -> str:
        """現在地域取得"""
        # 既存設定システムから取得
        from src.config import Config
        config = Config()
        return config.get("area_id", "JP13")  # デフォルト東京
        
    def get_region_name(self, region_id: str) -> str:
        """地域名取得"""
        from src.region_mapper import RegionMapper
        mapper = RegionMapper()
        return mapper.get_prefecture_name(region_id)
        
    def get_auth_status(self) -> bool:
        """認証状態取得"""
        try:
            from src.auth import AuthService
            auth = AuthService()
            return auth.is_authenticated()
        except Exception:
            return False
            
    def get_config_status(self) -> bool:
        """設定状態取得"""
        try:
            from src.config import Config
            config = Config()
            return config.is_valid()
        except Exception:
            return False
            
    def _generate_session_id(self) -> str:
        """セッションID生成"""
        import uuid
        return str(uuid.uuid4())

@dataclass
class UserSelection:
    """ユーザー選択状態データクラス"""
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    selected_date: Optional[str] = None
    selected_program: Optional[Dict[str, Any]] = None
    recording_settings: Optional[Dict[str, Any]] = None
```

---

## 4. 状態遷移詳細設計

### 4.1 状態遷移表

| 現在状態 | 入力 | 次状態 | アクション | データ保存 |
|---------|------|--------|------------|------------|
| MainMenu | [1] | StationSelect | PUSH | なし |
| MainMenu | [2] | SearchScreen | PUSH | なし |
| MainMenu | [0] | EXIT | EXIT | セッション保存 |
| StationSelect | [1-N] | DateSelect | PUSH | station_id, station_name |
| StationSelect | [88] | RegionSelect | PUSH | なし |
| StationSelect | [99] | MainMenu | POP | なし |
| DateSelect | [1-7] | ProgramSelect | PUSH | selected_date |
| DateSelect | [88] | StationSelect | POP | なし |
| ProgramSelect | [1-N] | RecordingConfirm | PUSH | selected_program |
| ProgramSelect | [77] | ProgramSearch | PUSH | search_context |
| RecordingConfirm | [1] | RecordingProgress | REPLACE | recording_config |

### 4.2 エラー状態遷移

| エラー種別 | 回復アクション | 遷移先 | ユーザー通知 |
|------------|----------------|--------|--------------|
| API接続エラー | 自動リトライ(3回) | 元画面 | "接続中..." → "リトライ中..." |
| 認証エラー | 設定画面誘導 | SettingsScreen | "認証設定が必要です" |
| データ不整合 | キャッシュクリア | MainMenu | "データを再読み込みします" |
| 予期しないエラー | ログ出力・通知 | MainMenu | "予期しないエラーが発生しました" |

---

## 5. パフォーマンス最適化詳細

### 5.1 データキャッシュ戦略

#### 5.1.1 放送局データキャッシュ
```python
class StationCache:
    """放送局データキャッシュ"""
    
    def __init__(self, cache_duration: int = 3600):  # 1時間
        self.cache_duration = cache_duration
        self.cache_data = {}
        
    def get_stations(self, region_id: str) -> Optional[List[Dict[str, Any]]]:
        """キャッシュから放送局データ取得"""
        cache_key = f"stations_{region_id}"
        
        if cache_key in self.cache_data:
            cached_item = self.cache_data[cache_key]
            
            # キャッシュ有効性チェック
            if datetime.now() - cached_item["timestamp"] < timedelta(seconds=self.cache_duration):
                return cached_item["data"]
                
        return None
        
    def set_stations(self, region_id: str, stations: List[Dict[str, Any]]) -> None:
        """放送局データをキャッシュに保存"""
        cache_key = f"stations_{region_id}"
        self.cache_data[cache_key] = {
            "data": stations,
            "timestamp": datetime.now()
        }
```

#### 5.1.2 番組データキャッシュ
```python
class ProgramCache:
    """番組データキャッシュ - SQLiteベース"""
    
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self._init_cache_db()
        
    def _init_cache_db(self) -> None:
        """キャッシュDB初期化"""
        # 既存のProgramHistoryManager活用
        pass
        
    def get_programs(self, station_id: str, date: str) -> Optional[List[Dict[str, Any]]]:
        """番組データ取得（キャッシュ優先）"""
        # キャッシュ確認 → API取得 → キャッシュ保存
        pass
```

### 5.2 レスポンシブ表示最適化

#### 5.2.1 非同期データ読み込み
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncUIService(UIService):
    """非同期対応UIサービス"""
    
    def __init__(self, session_manager: SessionManager):
        super().__init__(session_manager)
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    async def load_data_async(self, loader_func, *args, **kwargs):
        """データ読み込み非同期実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, loader_func, *args, **kwargs)
        
    def display_loading_spinner(self, message: str = "読み込み中..."):
        """ローディングスピナー表示"""
        # 回転アニメーション実装
        pass
```

---

**文書バージョン**: 1.0  
**作成日**: 2025-07-15  
**更新日**: 2025-07-15  
**承認**: システム設計チーム
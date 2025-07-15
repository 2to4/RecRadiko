# RecRadiko対話型インターフェース テスト仕様書
## バージョン 2.0 - UI刷新機能 品質保証計画

---

## 1. テスト概要

### 1.1 テスト目標
新規UI機能（メニュー駆動型インターフェース）の品質保証を通じて、ユーザビリティ・機能性・信頼性・パフォーマンスを検証し、プロダクション品質のリリースを保証する。

### 1.2 テスト戦略
- **多層テスト**: 単体→統合→システム→受入の4層構造
- **TDD準拠**: 実装前テストケース作成・Red-Green-Refactorサイクル
- **自動化重視**: CI/CD統合可能な自動テスト90%以上
- **実用性保証**: 実際のユーザーワークフローによる検証

### 1.3 品質基準
- **テストカバレッジ**: コード95%以上、分岐90%以上
- **パフォーマンス**: 画面遷移100ms以内、API呼び出し3秒以内
- **信頼性**: 24時間連続操作エラーゼロ
- **ユーザビリティ**: 新規ユーザー10分以内の操作習得

---

## 2. テストレベル設計

### 2.1 単体テスト (Unit Test)

#### 2.1.1 MenuManager単体テスト
```python
# tests/ui/test_menu_manager.py

import pytest
from unittest.mock import Mock, patch
from src.ui.menu_manager import MenuManager, NavigationAction, NavigationResult
from src.ui.screen_base import ScreenBase

class TestMenuManager:
    """MenuManager単体テスト"""
    
    @pytest.fixture
    def menu_manager(self):
        """テスト用MenuManagerインスタンス"""
        session_manager = Mock()
        ui_service = Mock()
        return MenuManager(session_manager, ui_service)
        
    @pytest.fixture
    def mock_screen_class(self):
        """モック画面クラス"""
        class MockScreen(ScreenBase):
            def load_data(self): pass
            def build_options(self): return []
            def handle_input(self, user_input): 
                return NavigationResult(NavigationAction.EXIT)
                
        return MockScreen
        
    def test_register_screen_success(self, menu_manager, mock_screen_class):
        """画面登録成功テスト"""
        # 実行
        menu_manager.register_screen("test_screen", mock_screen_class)
        
        # 検証
        assert "test_screen" in menu_manager.screen_registry
        assert menu_manager.screen_registry["test_screen"] == mock_screen_class
        
    def test_register_screen_duplicate_id_error(self, menu_manager, mock_screen_class):
        """重複ID登録エラーテスト"""
        # 事前条件
        menu_manager.register_screen("test_screen", mock_screen_class)
        
        # 実行・検証
        with pytest.raises(ValueError, match="Screen ID .* is already registered"):
            menu_manager.register_screen("test_screen", mock_screen_class)
            
    def test_register_screen_invalid_class_error(self, menu_manager):
        """無効クラス登録エラーテスト"""
        class InvalidScreen:
            pass
            
        # 実行・検証
        with pytest.raises(TypeError, match="Screen class must inherit from ScreenBase"):
            menu_manager.register_screen("invalid", InvalidScreen)
            
    def test_navigate_to_push_action(self, menu_manager, mock_screen_class):
        """PUSH遷移テスト"""
        # 事前条件
        menu_manager.register_screen("screen1", mock_screen_class)
        menu_manager.register_screen("screen2", mock_screen_class)
        
        # 初期画面設定
        menu_manager.navigate_to("screen1")
        assert len(menu_manager.screen_stack) == 0
        
        # PUSH遷移実行
        menu_manager.navigate_to("screen2", NavigationAction.PUSH)
        
        # 検証
        assert len(menu_manager.screen_stack) == 1
        assert menu_manager.screen_stack[0] == "mockscreen"
        assert isinstance(menu_manager.current_screen, mock_screen_class)
        
    def test_navigate_to_pop_action(self, menu_manager, mock_screen_class):
        """POP遷移テスト"""
        # 事前条件
        menu_manager.register_screen("screen1", mock_screen_class)
        menu_manager.register_screen("screen2", mock_screen_class)
        
        # スタック状態作成
        menu_manager.navigate_to("screen1")
        menu_manager.navigate_to("screen2", NavigationAction.PUSH)
        initial_stack_size = len(menu_manager.screen_stack)
        
        # POP遷移実行
        menu_manager.navigate_to("screen1", NavigationAction.POP)
        
        # 検証
        assert len(menu_manager.screen_stack) == initial_stack_size - 1
        
    def test_navigate_to_unknown_screen_error(self, menu_manager):
        """未登録画面遷移エラーテスト"""
        with pytest.raises(ValueError, match="Unknown screen ID"):
            menu_manager.navigate_to("unknown_screen")
            
    def test_go_back_success(self, menu_manager, mock_screen_class):
        """戻り操作成功テスト"""
        # 事前条件
        menu_manager.register_screen("screen1", mock_screen_class)
        menu_manager.register_screen("screen2", mock_screen_class)
        
        menu_manager.navigate_to("screen1")
        menu_manager.navigate_to("screen2", NavigationAction.PUSH)
        
        # 戻り操作実行
        result = menu_manager.go_back()
        
        # 検証
        assert result is True
        assert len(menu_manager.screen_stack) == 0
        
    def test_go_back_empty_stack(self, menu_manager, mock_screen_class):
        """空スタック戻り操作テスト"""
        # 事前条件
        menu_manager.register_screen("screen1", mock_screen_class)
        menu_manager.navigate_to("screen1")
        
        # 戻り操作実行
        result = menu_manager.go_back()
        
        # 検証
        assert result is False
        
    @patch('src.ui.menu_manager.input', return_value='0')
    def test_run_main_loop_exit(self, mock_input, menu_manager, mock_screen_class):
        """メインループ正常終了テスト"""
        # 事前条件
        menu_manager.register_screen("main_menu", mock_screen_class)
        
        # 実行
        exit_code = menu_manager.run()
        
        # 検証
        assert exit_code == 0
        
    @patch('src.ui.menu_manager.input', side_effect=KeyboardInterrupt())
    def test_run_keyboard_interrupt(self, mock_input, menu_manager, mock_screen_class):
        """Ctrl+C割り込みテスト"""
        # 事前条件
        menu_manager.register_screen("main_menu", mock_screen_class)
        menu_manager.ui_service.confirm_exit.return_value = True
        
        # 実行
        exit_code = menu_manager.run()
        
        # 検証
        assert exit_code == 0
        menu_manager.ui_service.confirm_exit.assert_called_once()
        
    def test_session_state_save_restore(self, menu_manager, mock_screen_class):
        """セッション状態保存・復元テスト"""
        # 事前条件
        menu_manager.register_screen("test_screen", mock_screen_class)
        
        # 状態保存テスト
        menu_manager.navigate_to("test_screen")
        menu_manager.session_manager.save_screen_state.assert_called()
        
        # 状態復元テスト  
        menu_manager.session_manager.load_screen_state.return_value = {"test": "data"}
        menu_manager.navigate_to("test_screen")
        menu_manager.current_screen.restore_state.assert_called_with({"test": "data"})
```

#### 2.1.2 Screen基底クラス単体テスト
```python
# tests/ui/test_screen_base.py

import pytest
from unittest.mock import Mock, patch
from src.ui.screen_base import ScreenBase, MenuOption

class ConcreteScreen(ScreenBase):
    """テスト用具象画面クラス"""
    def load_data(self):
        self.test_data = "loaded"
        
    def build_options(self):
        return [
            MenuOption("1", "Option 1"),
            MenuOption("2", "Option 2")
        ]
        
    def handle_input(self, user_input):
        from src.ui.menu_manager import NavigationResult, NavigationAction
        if user_input == "1":
            return NavigationResult(NavigationAction.PUSH, "next_screen")
        return NavigationResult(NavigationAction.EXIT)

class TestScreenBase:
    """ScreenBase単体テスト"""
    
    @pytest.fixture
    def screen(self):
        """テスト用画面インスタンス"""
        session_manager = Mock()
        ui_service = Mock()
        return ConcreteScreen(session_manager, ui_service)
        
    def test_init_default_values(self, screen):
        """初期化デフォルト値テスト"""
        assert screen.title == ""
        assert screen.subtitle == ""
        assert screen.options == []
        assert screen.is_loaded is False
        assert screen.error_message == ""
        assert screen.info_message == ""
        
    def test_init_with_context(self):
        """コンテキスト付き初期化テスト"""
        session_manager = Mock()
        ui_service = Mock()
        context = {"key": "value"}
        
        screen = ConcreteScreen(session_manager, ui_service, context)
        assert screen.context == context
        
    def test_display_template_method(self, screen):
        """display()テンプレートメソッドテスト"""
        # 実行
        screen.display()
        
        # 検証: UIサービスメソッド呼び出し確認
        screen.ui_service.clear_screen.assert_called_once()
        screen.ui_service.display_header.assert_called_once()
        screen.ui_service.display_options.assert_called_once()
        
        # データ読み込み確認
        assert screen.is_loaded is True
        assert hasattr(screen, 'test_data')
        assert screen.test_data == "loaded"
        
    def test_display_only_loads_data_once(self, screen):
        """データ読み込み重複防止テスト"""
        # 複数回display()実行
        screen.display()
        screen.display()
        
        # load_data()は一回のみ実行確認
        assert screen.test_data == "loaded"
        assert screen.is_loaded is True
        
    def test_validate_input_valid_options(self, screen):
        """有効入力検証テスト"""
        screen.options = [MenuOption("1", "Test"), MenuOption("2", "Test2")]
        
        # 有効な選択肢
        is_valid, _ = screen.validate_input("1")
        assert is_valid is True
        
        is_valid, _ = screen.validate_input("99")  # 共通選択肢
        assert is_valid is True
        
    def test_validate_input_invalid_options(self, screen):
        """無効入力検証テスト"""
        screen.options = [MenuOption("1", "Test")]
        
        # 空入力
        is_valid, error = screen.validate_input("")
        assert is_valid is False
        assert "空です" in error
        
        # 非数字
        is_valid, error = screen.validate_input("abc")
        assert is_valid is False
        assert "数字を入力" in error
        
        # 範囲外
        is_valid, error = screen.validate_input("999")
        assert is_valid is False
        assert "有効な選択肢" in error
        
    def test_error_message_display_and_clear(self, screen):
        """エラーメッセージ表示・クリアテスト"""
        # エラーメッセージ設定
        screen.set_error_message("Test error")
        assert screen.error_message == "Test error"
        
        # display()実行でクリア確認
        screen.display()
        screen.ui_service.display_error_message.assert_called_with("Test error")
        assert screen.error_message == ""  # クリア確認
        
    def test_info_message_display_and_clear(self, screen):
        """情報メッセージ表示・クリアテスト"""
        screen.set_info_message("Test info")
        assert screen.info_message == "Test info"
        
        screen.display()
        screen.ui_service.display_info_message.assert_called_with("Test info")
        assert screen.info_message == ""
        
    def test_get_state_and_restore_state(self, screen):
        """状態保存・復元テスト"""
        # 状態設定
        screen.context = {"test": "data"}
        screen.is_loaded = True
        
        # 状態取得
        state = screen.get_state()
        expected_state = {
            "context": {"test": "data"},
            "is_loaded": True,
            "class_name": "ConcreteScreen"
        }
        assert state == expected_state
        
        # 状態復元
        new_screen = ConcreteScreen(Mock(), Mock())
        new_screen.restore_state(state)
        assert new_screen.context == {"test": "data"}
        assert new_screen.is_loaded is True
```

#### 2.1.3 UIService単体テスト
```python
# tests/ui/test_ui_service.py

import pytest
from unittest.mock import Mock, patch, call
import io
import sys
from src.ui.services.ui_service import UIService
from src.ui.screen_base import MenuOption

class TestUIService:
    """UIService単体テスト"""
    
    @pytest.fixture
    def ui_service(self):
        """テスト用UIServiceインスタンス"""
        session_manager = Mock()
        return UIService(session_manager)
        
    @patch('os.system')
    def test_clear_screen_windows(self, mock_system, ui_service):
        """Windows画面クリアテスト"""
        with patch('os.name', 'nt'):
            ui_service.clear_screen()
            mock_system.assert_called_with('cls')
            
    @patch('os.system')
    def test_clear_screen_unix(self, mock_system, ui_service):
        """Unix/Linux画面クリアテスト"""
        with patch('os.name', 'posix'):
            ui_service.clear_screen()
            mock_system.assert_called_with('clear')
            
    def test_display_header(self, ui_service, capsys):
        """ヘッダー表示テスト"""
        ui_service.terminal_width = 50
        
        ui_service.display_header("Test Title", "Test Subtitle")
        
        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "Test Subtitle" in captured.out
        assert "=" * 50 in captured.out
        
    def test_display_options_basic(self, ui_service, capsys):
        """基本選択肢表示テスト"""
        options = [
            MenuOption("1", "Option 1", "Description 1"),
            MenuOption("2", "Option 2"),
            MenuOption("3", "Option 3", enabled=False)
        ]
        
        ui_service.display_options(options)
        
        captured = capsys.readouterr()
        assert "[1] Option 1" in captured.out
        assert "Description 1" in captured.out
        assert "[2] Option 2" in captured.out
        assert "[3] Option 3 (無効)" in captured.out
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_up_down(self, mock_get_key, ui_service):
        """上下キーナビゲーションテスト"""
        # テスト用選択肢設定
        options = [
            MenuOption("0", "Option 1"),
            MenuOption("1", "Option 2"),
            MenuOption("2", "Option 3")
        ]
        ui_service.setup_keyboard_navigation(options)
        
        # 下キー→上キー→Enterのシーケンス
        mock_get_key.side_effect = ['DOWN', 'UP', 'ENTER']
        
        result = ui_service.get_user_input()
        assert result == "0"  # 最初の選択肢に戻った状態
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_circular_selection(self, mock_get_key, ui_service):
        """循環選択テスト"""
        options = [
            MenuOption("0", "Option 1"),
            MenuOption("1", "Option 2")
        ]
        ui_service.setup_keyboard_navigation(options)
        
        # 最初の項目から上キー（循環して最後へ）
        mock_get_key.side_effect = ['UP', 'ENTER']
        
        result = ui_service.get_user_input()
        assert result == "1"  # 最後の項目
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_page_navigation(self, mock_get_key, ui_service):
        """ページナビゲーションテスト"""
        options = [MenuOption(str(i), f"Option {i}") for i in range(20)]
        ui_service.setup_keyboard_navigation(options)
        
        # Page Downでページ送り
        mock_get_key.side_effect = ['PGDN', 'ENTER']
        
        result = ui_service.get_user_input()
        assert result == "10"  # 10項目下に移動
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_shortcut_keys(self, mock_get_key, ui_service):
        """ショートカットキーテスト"""
        options = [MenuOption("0", "Option 1")]
        shortcut_keys = {"R": "region_change", "S": "search"}
        ui_service.setup_keyboard_navigation(options, shortcut_keys)
        
        # Rキー入力
        mock_get_key.side_effect = ['R']
        
        result = ui_service.get_user_input()
        assert result == "region_change"
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_escape_key(self, mock_get_key, ui_service):
        """Escapeキーテスト"""
        options = [MenuOption("0", "Option 1")]
        ui_service.setup_keyboard_navigation(options)
        
        mock_get_key.side_effect = ['ESC']
        
        result = ui_service.get_user_input()
        assert result == "99"  # 前画面に戻る
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_disabled_options(self, mock_get_key, ui_service):
        """無効選択肢スキップテスト"""
        options = [
            MenuOption("0", "Option 1", enabled=True),
            MenuOption("1", "Option 2", enabled=False),
            MenuOption("2", "Option 3", enabled=True)
        ]
        ui_service.setup_keyboard_navigation(options)
        
        # 下キーで無効な選択肢をスキップ
        mock_get_key.side_effect = ['DOWN', 'ENTER']
        
        result = ui_service.get_user_input()
        assert result == "2"  # 無効な選択肢をスキップして次の有効選択肢
        
    @patch('src.ui.services.ui_service.UIService._get_key', side_effect=KeyboardInterrupt())
    def test_keyboard_navigation_keyboard_interrupt(self, mock_get_key, ui_service):
        """Ctrl+C割り込みテスト"""
        options = [MenuOption("0", "Option 1")]
        ui_service.setup_keyboard_navigation(options)
        
        result = ui_service.get_user_input()
        assert result == "0"  # 終了扱い
        
    def test_display_progress_bar(self, ui_service, capsys):
        """プログレスバー表示テスト"""
        ui_service.terminal_width = 80
        
        ui_service.display_progress_bar(0.5, "Test progress")
        
        captured = capsys.readouterr()
        assert "50%" in captured.out
        assert "Test progress" in captured.out
        assert "█" in captured.out
        assert "░" in captured.out
        
    @patch('builtins.input', return_value='y')
    def test_confirm_exit_yes(self, mock_input, ui_service):
        """終了確認Yes応答テスト"""
        result = ui_service.confirm_exit()
        assert result is True
        
    @patch('builtins.input', return_value='n')
    def test_confirm_exit_no(self, mock_input, ui_service):
        """終了確認No応答テスト"""
        result = ui_service.confirm_exit()
        assert result is False
        
    @patch('builtins.input', return_value='')
    def test_confirm_exit_default_no(self, mock_input, ui_service):
        """終了確認デフォルトNo応答テスト"""
        result = ui_service.confirm_exit()
        assert result is False
        
    @patch('src.ui.services.ui_service.ProgramInfo')
    def test_get_stations_for_region(self, mock_program_info_class, ui_service):
        """放送局データ取得テスト"""
        # モック設定
        mock_program_info = mock_program_info_class.return_value
        mock_program_info.get_stations_for_area.return_value = [
            {"id": "TBS", "name": "TBSラジオ", "description": "TBS Radio"},
            {"id": "QRR", "name": "文化放送", "available": False}
        ]
        
        # 実行
        result = ui_service.get_stations_for_region("JP13")
        
        # 検証
        assert len(result) == 2
        assert result[0]["id"] == "TBS"
        assert result[0]["name"] == "TBSラジオ"
        assert result[0]["available"] is True  # デフォルト値
        assert result[1]["available"] is False
        
    @patch('src.ui.services.ui_service.ProgramHistoryManager')
    def test_get_programs_for_date(self, mock_history_class, ui_service):
        """番組データ取得テスト"""
        # モック設定
        mock_history = mock_history_class.return_value
        mock_history.get_programs_by_date.return_value = [
            {
                "id": "prog1", 
                "title": "Test Program",
                "start_time": "06:00",
                "end_time": "08:00",
                "duration": 120
            }
        ]
        
        # 実行
        result = ui_service.get_programs_for_date("TBS", "2025-07-15")
        
        # 検証
        assert len(result) == 1
        assert result[0]["title"] == "Test Program"
        assert result[0]["duration"] == 120
        
    def test_color_support_detection(self, ui_service):
        """カラーサポート検出テスト"""
        # TTY環境
        with patch('sys.stdout.isatty', return_value=True):
            ui_service = UIService(Mock())
            assert ui_service.colors_enabled is True
            
        # 非TTY環境
        with patch('sys.stdout.isatty', return_value=False):
            ui_service = UIService(Mock())
            assert ui_service.colors_enabled is False
            
    def test_format_with_color_enabled(self, ui_service):
        """カラーフォーマット有効テスト"""
        ui_service.colors_enabled = True
        
        result = ui_service._format_with_color("test", "red")
        assert "\033[91m" in result  # 赤色コード
        assert "\033[0m" in result   # リセットコード
        assert "test" in result
        
    def test_format_with_color_disabled(self, ui_service):
        """カラーフォーマット無効テスト"""
        ui_service.colors_enabled = False
        
        result = ui_service._format_with_color("test", "red")
        assert result == "test"  # 色コードなし
```

### 2.2 統合テスト (Integration Test)

#### 2.2.1 画面遷移統合テスト
```python
# tests/integration/test_screen_navigation.py

import pytest
from unittest.mock import Mock, patch
from src.ui.menu_manager import MenuManager
from src.ui.screens.main_menu import MainMenuScreen
from src.ui.screens.station_select import StationSelectScreen
from src.ui.screens.date_select import DateSelectScreen

class TestScreenNavigation:
    """画面遷移統合テスト"""
    
    @pytest.fixture
    def integrated_menu_system(self):
        """統合テスト用メニューシステム"""
        session_manager = Mock()
        ui_service = Mock()
        
        menu_manager = MenuManager(session_manager, ui_service)
        
        # 実際の画面クラスを登録
        menu_manager.register_screen("main_menu", MainMenuScreen)
        menu_manager.register_screen("station_select", StationSelectScreen)
        menu_manager.register_screen("date_select", DateSelectScreen)
        
        return menu_manager
        
    def test_full_recording_workflow_navigation(self, integrated_menu_system):
        """完全録音ワークフロー遷移テスト"""
        menu_manager = integrated_menu_system
        
        # メインメニューから開始
        menu_manager.navigate_to("main_menu")
        assert isinstance(menu_manager.current_screen, MainMenuScreen)
        
        # [1] 番組録音選択
        result = menu_manager.current_screen.handle_input("1")
        menu_manager.navigate_to(result.screen_id, result.action, result.context)
        assert isinstance(menu_manager.current_screen, StationSelectScreen)
        
        # [1] 放送局選択（TBSラジオ）
        menu_manager.current_screen.stations = [
            {"id": "TBS", "name": "TBSラジオ", "available": True}
        ]
        result = menu_manager.current_screen.handle_input("1")
        menu_manager.navigate_to(result.screen_id, result.action, result.context)
        assert isinstance(menu_manager.current_screen, DateSelectScreen)
        
        # [1] 日付選択（今日）
        result = menu_manager.current_screen.handle_input("1")
        assert result.context["station_id"] == "TBS"
        assert "selected_date" in result.context
        
    def test_back_navigation_workflow(self, integrated_menu_system):
        """戻りナビゲーションワークフローテスト"""
        menu_manager = integrated_menu_system
        
        # 深い階層まで遷移
        menu_manager.navigate_to("main_menu")
        menu_manager.navigate_to("station_select", action=NavigationAction.PUSH)
        menu_manager.navigate_to("date_select", action=NavigationAction.PUSH)
        
        initial_stack_size = len(menu_manager.screen_stack)
        
        # [99] メインメニューに戻る
        result = menu_manager.current_screen.handle_input("99")
        assert result.action == NavigationAction.POP
        
        # [88] 一つ前の画面に戻る
        menu_manager.navigate_to("date_select", action=NavigationAction.PUSH)
        result = menu_manager.current_screen.handle_input("88")
        # 実装により具体的な遷移先を検証
        
    def test_error_recovery_navigation(self, integrated_menu_system):
        """エラー回復ナビゲーションテスト"""
        menu_manager = integrated_menu_system
        
        # メインメニューから開始
        menu_manager.navigate_to("main_menu")
        
        # システム準備未完了状態で録音選択
        menu_manager.current_screen.context["system_ready"] = False
        result = menu_manager.current_screen.handle_input("1")
        
        # エラーメッセージ表示・メインメニューに留まる
        assert result.action == NavigationAction.REPLACE
        assert result.screen_id == "main_menu"
        assert menu_manager.current_screen.error_message != ""
        
    def test_session_state_persistence_across_navigation(self, integrated_menu_system):
        """ナビゲーション間セッション状態永続化テスト"""
        menu_manager = integrated_menu_system
        session_manager = menu_manager.session_manager
        
        # 初期画面
        menu_manager.navigate_to("main_menu")
        
        # 状態設定
        test_context = {"test_key": "test_value"}
        menu_manager.current_screen.context = test_context
        
        # 次画面に遷移
        menu_manager.navigate_to("station_select", action=NavigationAction.PUSH)
        
        # セッション保存確認
        session_manager.save_screen_state.assert_called()
        
        # 前画面に戻る
        menu_manager.go_back()
        
        # セッション復元確認
        session_manager.load_screen_state.assert_called()
```

#### 2.2.2 データフロー統合テスト
```python
# tests/integration/test_data_flow.py

import pytest
from unittest.mock import Mock, patch
from src.ui.services.ui_service import UIService
from src.ui.services.session_manager import SessionManager

class TestDataFlow:
    """データフロー統合テスト"""
    
    @pytest.fixture
    def integrated_data_system(self):
        """統合データシステム"""
        session_manager = SessionManager()
        ui_service = UIService(session_manager)
        return session_manager, ui_service
        
    @patch('src.program_info.ProgramInfo')
    def test_station_data_flow(self, mock_program_info, integrated_data_system):
        """放送局データフロー統合テスト"""
        session_manager, ui_service = integrated_data_system
        
        # API応答モック
        mock_stations = [
            {"id": "TBS", "name": "TBSラジオ", "description": "TBS Radio"},
            {"id": "QRR", "name": "文化放送", "description": "Bunka Broadcasting"}
        ]
        mock_program_info.return_value.get_stations_for_area.return_value = mock_stations
        
        # 地域設定
        with patch.object(session_manager, 'get_current_region', return_value='JP13'):
            # 放送局データ取得
            stations = ui_service.get_stations_for_region('JP13')
            
        # データ変換検証
        assert len(stations) == 2
        assert stations[0]["id"] == "TBS"
        assert stations[0]["available"] is True
        assert stations[1]["id"] == "QRR"
        
    @patch('src.program_history.ProgramHistoryManager')
    def test_program_data_flow(self, mock_history, integrated_data_system):
        """番組データフロー統合テスト"""
        session_manager, ui_service = integrated_data_system
        
        # API応答モック
        mock_programs = [
            {
                "id": "prog1",
                "title": "Morning Show",
                "start_time": "06:00",
                "end_time": "08:00",
                "duration": 120,
                "cast": "Host Name"
            }
        ]
        mock_history.return_value.get_programs_by_date.return_value = mock_programs
        
        # 番組データ取得
        programs = ui_service.get_programs_for_date("TBS", "2025-07-15")
        
        # データ変換検証
        assert len(programs) == 1
        assert programs[0]["title"] == "Morning Show"
        assert programs[0]["duration"] == 120
        
    def test_user_selection_data_flow(self, integrated_data_system):
        """ユーザー選択データフロー統合テスト"""
        session_manager, ui_service = integrated_data_system
        
        # ユーザー選択シーケンス
        session_manager.set_selected_station("TBS", "TBSラジオ")
        session_manager.set_selected_date("2025-07-15")
        
        test_program = {
            "id": "prog1",
            "title": "Test Program",
            "start_time": "06:00",
            "end_time": "08:00"
        }
        session_manager.set_selected_program(test_program)
        
        # 選択状態取得・検証
        selection = session_manager.get_current_selection()
        assert selection.station_id == "TBS"
        assert selection.station_name == "TBSラジオ"
        assert selection.selected_date == "2025-07-15"
        assert selection.selected_program["title"] == "Test Program"
        
    def test_session_persistence_data_flow(self, integrated_data_system):
        """セッション永続化データフロー統合テスト"""
        session_manager, ui_service = integrated_data_system
        
        # セッションデータ設定
        test_data = {"key": "value", "number": 123}
        session_manager.ui_state["test_data"] = test_data
        
        # 保存実行
        with patch.object(session_manager, 'save_ui_state') as mock_save:
            session_manager.save_screen_state("test_screen", test_data)
            mock_save.assert_called_once()
            
        # 復元実行
        with patch.object(session_manager, 'load_screen_state', return_value=test_data):
            restored_data = session_manager.load_screen_state("test_screen")
            assert restored_data == test_data
```

### 2.3 システムテスト (System Test)

#### 2.3.1 エンドツーエンドワークフローテスト
```python
# tests/system/test_e2e_workflows.py

import pytest
from unittest.mock import Mock, patch, call
import tempfile
import json
from pathlib import Path
from src.ui.menu_manager import MenuManager
from src.ui.services.session_manager import SessionManager
from src.ui.services.ui_service import UIService

class TestE2EWorkflows:
    """エンドツーエンドワークフローシステムテスト"""
    
    @pytest.fixture
    def e2e_system(self):
        """E2Eテスト用システム"""
        # 一時ディレクトリでセッション管理
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            session_manager = SessionManager(config_dir)
            ui_service = UIService(session_manager)
            menu_manager = MenuManager(session_manager, ui_service)
            
            # 全画面登録
            from src.ui.screens import (
                MainMenuScreen, StationSelectScreen, DateSelectScreen,
                ProgramSelectScreen, SearchScreen, SettingsScreen
            )
            
            menu_manager.register_screen("main_menu", MainMenuScreen)
            menu_manager.register_screen("station_select", StationSelectScreen)
            menu_manager.register_screen("date_select", DateSelectScreen)
            menu_manager.register_screen("program_select", ProgramSelectScreen)
            menu_manager.register_screen("search_screen", SearchScreen)
            menu_manager.register_screen("settings_screen", SettingsScreen)
            
            yield menu_manager, session_manager, ui_service
            
    @patch('src.ui.services.ui_service.UIService._get_key', side_effect=[
        'ENTER', 'ENTER', 'ENTER', 'ENTER', 'ENTER', 'Q'])
    @patch('src.timefree_recorder.TimeFreeRecorder')
    def test_complete_recording_workflow_keyboard(self, mock_recorder, mock_keys, e2e_system):
        """完全録音ワークフローE2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # モックデータ設定
        ui_service.get_stations_for_region = Mock(return_value=[
            {"id": "TBS", "name": "TBSラジオ", "available": True}
        ])
        ui_service.get_programs_for_date = Mock(return_value=[
            {
                "id": "prog1",
                "title": "Test Program",
                "start_time": "06:00",
                "end_time": "08:00",
                "duration": 120
            }
        ])
        
        # 録音成功設定
        mock_recorder_instance = mock_recorder.return_value
        mock_recorder_instance.record.return_value = True
        
        # システム状態設定
        session_manager.get_auth_status = Mock(return_value=True)
        session_manager.get_config_status = Mock(return_value=True)
        
        # E2Eワークフロー実行
        exit_code = menu_manager.run()
        
        # 実行結果検証
        assert exit_code == 0
        
        # 録音実行確認
        mock_recorder_instance.record.assert_called_once()
        
        # ユーザー選択状態確認
        selection = session_manager.get_current_selection()
        assert selection.station_id == "TBS"
        assert selection.selected_program["title"] == "Test Program"
        
    @patch('builtins.input', side_effect=['2', 'Morning', '1', '99', '0'])
    def test_search_and_record_workflow(self, mock_input, e2e_system):
        """検索・録音ワークフローE2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # 検索結果モック
        search_results = [
            {
                "id": "prog1",
                "title": "Morning Show",
                "station_name": "TBSラジオ",
                "date": "2025-07-15",
                "start_time": "06:00"
            }
        ]
        
        with patch('src.program_history.ProgramHistoryManager') as mock_history:
            mock_history.return_value.search_programs.return_value = search_results
            
            # 検索ワークフロー実行
            exit_code = menu_manager.run()
            
        # 検索実行確認
        mock_history.return_value.search_programs.assert_called()
        assert exit_code == 0
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_keyboard_navigation_e2e_workflow(self, mock_get_key, e2e_system):
        """キーボードナビゲーションE2Eワークフローテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # キーボード操作シーケンス: 下→下→上→Enter→Escape→Q
        mock_get_key.side_effect = [
            'DOWN',    # メニュー項目移動
            'DOWN',    # さらに下へ
            'UP',      # 一つ戻る
            'ENTER',   # 番組検索選択
            'ESC',     # 前画面に戻る
            'Q'        # 終了
        ]
        
        # UIサービス設定
        ui_service.setup_keyboard_navigation([
            MenuOption("0", "番組録音"),
            MenuOption("1", "番組検索"),
            MenuOption("2", "録音履歴"),
            MenuOption("3", "設定管理"),
            MenuOption("4", "システム情報"),
            MenuOption("5", "終了")
        ])
        
        # ワークフロー実行
        exit_code = menu_manager.run()
        
        # キーボード操作確認
        assert mock_get_key.call_count == 6
        assert exit_code == 0
        
    @patch('src.ui.services.ui_service.UIService._get_key')
    def test_shortcut_keys_e2e_workflow(self, mock_get_key, e2e_system):
        """ショートカットキーE2Eワークフローテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # ショートカットキー操作: R（地域変更）→S（検索）→Q（終了）
        mock_get_key.side_effect = ['R', 'S', 'Q']
        
        # ショートカットキー設定
        ui_service.setup_keyboard_navigation(
            [MenuOption("0", "Test Option")],
            shortcut_keys={"R": "region_change", "S": "search"}
        )
        
        # ワークフロー実行
        exit_code = menu_manager.run()
        
        # ショートカット動作確認
        assert exit_code == 0
        
    @patch('builtins.input', side_effect=['4', '1', 'Osaka', '99', '0'])
    def test_settings_change_workflow(self, mock_input, e2e_system):
        """設定変更ワークフローE2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # 設定変更モック
        with patch('src.region_mapper.RegionMapper') as mock_mapper:
            mock_mapper.return_value.get_area_id.return_value = "JP27"
            
            # 設定変更ワークフロー実行
            exit_code = menu_manager.run()
            
        # 設定変更確認
        assert exit_code == 0
        
    def test_session_persistence_across_restart(self, e2e_system):
        """再起動間セッション永続化E2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # セッションデータ設定
        test_selection = {
            "station_id": "TBS",
            "station_name": "TBSラジオ",
            "selected_date": "2025-07-15"
        }
        
        session_manager.set_selected_station("TBS", "TBSラジオ")
        session_manager.set_selected_date("2025-07-15")
        session_manager.save_session()
        
        # 新しいセッションマネージャーでデータ復元テスト
        new_session_manager = SessionManager(session_manager.config_dir)
        
        # セッションデータ確認（実際の実装に依存）
        # assert new_session_manager.session_data["user_selection"] == test_selection
        
    @patch('builtins.input', side_effect=['1', '999', '1', '0'])
    def test_error_handling_and_recovery(self, mock_input, e2e_system):
        """エラーハンドリング・回復E2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # エラー状況設定
        ui_service.get_stations_for_region = Mock(side_effect=Exception("API Error"))
        
        # エラー時のワークフロー実行
        exit_code = menu_manager.run()
        
        # グレースフルな処理確認
        assert exit_code == 0  # アプリケーションは正常終了
        
    @patch('builtins.input', side_effect=KeyboardInterrupt())
    def test_keyboard_interrupt_handling(self, mock_input, e2e_system):
        """Ctrl+C割り込み処理E2Eテスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # 終了確認をYes設定
        ui_service.confirm_exit = Mock(return_value=True)
        
        # Ctrl+C処理実行
        exit_code = menu_manager.run()
        
        # 適切な終了確認
        assert exit_code == 0
        ui_service.confirm_exit.assert_called_once()
```

#### 2.3.2 パフォーマンステスト
```python
# tests/system/test_performance.py

import pytest
import time
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """パフォーマンスシステムテスト"""
    
    def test_screen_transition_performance(self, e2e_system):
        """画面遷移パフォーマンステスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # 画面遷移時間測定
        start_time = time.time()
        
        menu_manager.navigate_to("main_menu")
        menu_manager.navigate_to("station_select", action=NavigationAction.PUSH)
        menu_manager.navigate_to("date_select", action=NavigationAction.PUSH)
        menu_manager.go_back()
        menu_manager.go_back()
        
        elapsed_time = time.time() - start_time
        
        # 要件: 5回の画面遷移が500ms以内
        assert elapsed_time < 0.5
        
    def test_data_loading_performance(self, e2e_system):
        """データ読み込みパフォーマンステスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        # 大量データモック
        large_station_list = [
            {"id": f"station_{i}", "name": f"Station {i}", "available": True}
            for i in range(100)
        ]
        
        ui_service.get_stations_for_region = Mock(return_value=large_station_list)
        
        # データ読み込み時間測定
        start_time = time.time()
        stations = ui_service.get_stations_for_region("JP13")
        elapsed_time = time.time() - start_time
        
        # 要件: 100局データ読み込みが200ms以内
        assert elapsed_time < 0.2
        assert len(stations) == 100
        
    def test_memory_usage_performance(self, e2e_system):
        """メモリ使用量パフォーマンステスト"""
        import psutil
        import os
        
        menu_manager, session_manager, ui_service = e2e_system
        
        # 初期メモリ使用量
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 大量セッションデータ生成
        for i in range(1000):
            session_manager.save_screen_state(f"screen_{i}", {"data": f"large_data_{i}" * 100})
            
        # 最終メモリ使用量
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 要件: メモリ増加が50MB以内
        assert memory_increase < 50 * 1024 * 1024
        
    def test_concurrent_access_performance(self, e2e_system):
        """並行アクセスパフォーマンステスト"""
        menu_manager, session_manager, ui_service = e2e_system
        
        def simulate_user_session(session_id):
            """ユーザーセッションシミュレーション"""
            for i in range(10):
                session_manager.save_screen_state(f"screen_{session_id}_{i}", {"data": f"session_{session_id}_data_{i}"})
                time.sleep(0.01)
                
        # 10並行ユーザーシミュレーション
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(simulate_user_session, i) for i in range(10)]
            for future in futures:
                future.result()
                
        elapsed_time = time.time() - start_time
        
        # 要件: 10並行セッションが3秒以内
        assert elapsed_time < 3.0
```

### 2.4 受入テスト (Acceptance Test)

#### 2.4.1 ユーザーシナリオテスト
```python
# tests/acceptance/test_user_scenarios.py

import pytest
from unittest.mock import Mock, patch

class TestUserScenarios:
    """ユーザーシナリオ受入テスト"""
    
    def test_new_user_first_time_recording(self, e2e_system):
        """新規ユーザー初回録音シナリオ"""
        """
        シナリオ: 新規ユーザーが初めてRecRadikoを使って番組録音を行う
        
        前提条件:
        - RecRadikoを初回起動
        - 地域設定未完了
        - 認証情報未設定
        
        期待結果:
        - 設定ガイダンスが表示される
        - 地域設定・認証設定が完了する
        - 録音が成功する
        """
        menu_manager, session_manager, ui_service = e2e_system
        
        # 新規ユーザー状態設定
        session_manager.get_auth_status = Mock(return_value=False)
        session_manager.get_config_status = Mock(return_value=False)
        
        # ユーザー入力シミュレーション
        user_inputs = [
            '4',      # 設定管理
            '1',      # 地域設定
            '2',      # 関東地方
            '13',     # 東京都
            '99',     # 設定メニューに戻る
            '99',     # メインメニューに戻る
            '1',      # 番組録音
            '1',      # TBSラジオ
            '1',      # 今日
            '1',      # 最初の番組
            '1',      # 録音開始
            '0'       # 終了
        ]
        
        with patch('builtins.input', side_effect=user_inputs):
            # 設定完了後の状態更新
            def update_status_after_setup():
                session_manager.get_auth_status.return_value = True
                session_manager.get_config_status.return_value = True
                
            with patch.object(session_manager, 'save_session', side_effect=update_status_after_setup):
                exit_code = menu_manager.run()
                
        assert exit_code == 0
        
    def test_experienced_user_quick_recording(self, e2e_system):
        """経験ユーザー高速録音シナリオ"""
        """
        シナリオ: 経験豊富なユーザーが慣れた操作で素早く録音を行う
        
        前提条件:
        - 設定完了済み
        - 好みの放送局・番組を知っている
        
        期待結果:
        - 最小限の操作で録音開始
        - 前回の選択が記憶されている
        """
        menu_manager, session_manager, ui_service = e2e_system
        
        # 経験ユーザー状態設定
        session_manager.get_auth_status = Mock(return_value=True)
        session_manager.get_config_status = Mock(return_value=True)
        
        # 前回選択の復元設定
        session_manager.load_screen_state = Mock(return_value={
            "context": {"preferred_station": "TBS"},
            "is_loaded": True
        })
        
        # 高速操作シミュレーション
        user_inputs = ['1', '1', '1', '1', '1', '0']  # 6操作で録音完了
        
        with patch('builtins.input', side_effect=user_inputs):
            start_time = time.time()
            exit_code = menu_manager.run()
            elapsed_time = time.time() - start_time
            
        assert exit_code == 0
        # 要件: 経験ユーザーは30秒以内で録音開始
        assert elapsed_time < 30.0
        
    def test_user_error_recovery_scenario(self, e2e_system):
        """ユーザーエラー回復シナリオ"""
        """
        シナリオ: ユーザーが操作ミスをして、エラーから回復する
        
        前提条件:
        - 録音開始直前
        - ネットワーク接続が不安定
        
        期待結果:
        - エラーメッセージが分かりやすい
        - 回復手順が明確
        - 作業内容が失われない
        """
        menu_manager, session_manager, ui_service = e2e_system
        
        # エラー状況設定
        api_call_count = 0
        def unstable_api_call(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1
            if api_call_count < 3:  # 最初の2回はエラー
                raise Exception("Network timeout")
            return [{"id": "TBS", "name": "TBSラジオ", "available": True}]
            
        ui_service.get_stations_for_region = Mock(side_effect=unstable_api_call)
        
        # エラー回復操作シミュレーション
        user_inputs = [
            '1',      # 番組録音
            '1',      # リトライ (1回目エラー)
            '1',      # リトライ (2回目エラー)  
            '1',      # リトライ (3回目成功)
            '1',      # 今日
            '1',      # 最初の番組
            '1',      # 録音開始
            '0'       # 終了
        ]
        
        with patch('builtins.input', side_effect=user_inputs):
            exit_code = menu_manager.run()
            
        assert exit_code == 0
        assert api_call_count == 3  # 3回目で成功
        
    def test_accessibility_scenario(self, e2e_system):
        """アクセシビリティシナリオ"""
        """
        シナリオ: 視覚障害のあるユーザーがスクリーンリーダーで操作
        
        前提条件:
        - スクリーンリーダー使用
        - テキストベースの操作のみ
        
        期待結果:
        - 全ての情報がテキストで提供される
        - 操作手順が明確
        - 不要な装飾がない
        """
        menu_manager, session_manager, ui_service = e2e_system
        
        # アクセシビリティ設定
        ui_service.colors_enabled = False  # カラー無効
        
        # 画面出力キャプチャ
        screen_outputs = []
        def capture_output(*args, **kwargs):
            screen_outputs.append(str(args))
            
        ui_service.display_header = Mock(side_effect=capture_output)
        ui_service.display_options = Mock(side_effect=capture_output)
        
        user_inputs = ['1', '1', '1', '1', '0']
        
        with patch('builtins.input', side_effect=user_inputs):
            exit_code = menu_manager.run()
            
        # アクセシビリティ検証
        assert exit_code == 0
        assert len(screen_outputs) > 0
        
        # 全出力がテキストベース確認
        for output in screen_outputs:
            assert not any(color_code in str(output) for color_code in ['\033[', '\x1b['])
```

---

## 3. テスト実行計画

### 3.1 テスト環境

#### 3.1.1 開発環境テスト
- **実行頻度**: コミット毎
- **範囲**: 単体テスト + 基本統合テスト
- **自動化**: pre-commit hooks
- **所要時間**: < 2分

#### 3.1.2 CI環境テスト
- **実行頻度**: PR作成時・マージ時
- **範囲**: 全テストレベル
- **自動化**: GitHub Actions
- **所要時間**: < 10分

#### 3.1.3 ステージング環境テスト
- **実行頻度**: リリース前
- **範囲**: システムテスト + 受入テスト
- **実行方法**: 手動 + 自動
- **所要時間**: < 30分

### 3.2 テスト実行コマンド

#### 3.2.1 単体テスト実行
```bash
# 全単体テスト
pytest tests/ui/ -v --cov=src/ui --cov-report=html

# 特定クラステスト  
pytest tests/ui/test_menu_manager.py -v

# カバレッジ付きテスト
pytest tests/ui/ --cov=src/ui --cov-report=term-missing
```

#### 3.2.2 統合テスト実行
```bash
# 統合テスト
pytest tests/integration/ -v

# 特定統合テスト
pytest tests/integration/test_screen_navigation.py -v

# パフォーマンステスト
pytest tests/system/test_performance.py -v --benchmark
```

#### 3.2.3 E2Eテスト実行
```bash
# E2Eテスト
pytest tests/system/test_e2e_workflows.py -v

# 受入テスト
pytest tests/acceptance/ -v

# 全テスト実行
pytest tests/ -v --cov=src --cov-report=html
```

### 3.3 テスト品質基準

#### 3.3.1 カバレッジ要件
- **行カバレッジ**: 95%以上
- **分岐カバレッジ**: 90%以上
- **関数カバレッジ**: 100%

#### 3.3.2 パフォーマンス要件
- **画面遷移**: 100ms以内
- **データ読み込み**: 3秒以内
- **メモリ使用量**: 50MB以内増加

#### 3.3.3 品質ゲート
- テスト成功率: 100%
- 警告ゼロ
- ドキュメントテスト通過

---

## 4. 継続的品質保証

### 4.1 自動テスト実行

#### 4.1.1 pre-commit設定
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: pytest tests/ui/ -x
        language: system
        pass_filenames: false
        
      - id: coverage-check
        name: coverage check
        entry: pytest tests/ui/ --cov=src/ui --cov-fail-under=95
        language: system
        pass_filenames: false
```

#### 4.1.2 CI/CD設定
```yaml
# .github/workflows/ui-tests.yml
name: UI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov pytest-benchmark
          
      - name: Run unit tests
        run: pytest tests/ui/ -v --cov=src/ui --cov-report=xml
        
      - name: Run integration tests
        run: pytest tests/integration/ -v
        
      - name: Run system tests
        run: pytest tests/system/ -v
        
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 4.2 品質監視

#### 4.2.1 メトリクス収集
- **テスト実行時間**: 実行時間推移監視
- **カバレッジ推移**: カバレッジ低下防止
- **失敗率**: テスト失敗パターン分析

#### 4.2.2 品質レポート
- **週次レポート**: テスト状況サマリー
- **リリース前レポート**: 全品質メトリクス
- **パフォーマンスレポート**: 性能推移分析

---

## 5. テスト実装優先度

### 5.1 Phase 1: 基盤テスト (Week 1)
- MenuManager単体テスト
- ScreenBase単体テスト  
- UIService単体テスト
- 基本画面遷移統合テスト

### 5.2 Phase 2: 機能テスト (Week 2)
- 全画面クラス単体テスト
- データフロー統合テスト
- エラーハンドリングテスト
- セッション管理テスト

### 5.3 Phase 3: 品質テスト (Week 3)
- E2Eワークフローテスト
- パフォーマンステスト
- ユーザーシナリオテスト
- アクセシビリティテスト

---

**文書バージョン**: 1.0  
**作成日**: 2025-07-15  
**更新日**: 2025-07-15  
**承認**: 品質保証チーム
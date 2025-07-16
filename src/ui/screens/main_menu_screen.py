"""
Main Menu Screen for RecRadiko Keyboard Navigation UI

Provides main menu interface with keyboard navigation for RecRadiko timefree recording.
Handles menu selection and navigation to specific workflows.

Based on UI_SPECIFICATION.md:
- Main menu with keyboard navigation
- Recording workflow entry point
- Settings and help access
- Clean exit handling
"""

import os
import logging
from typing import Optional, List
from src.ui.screen_base import ScreenBase


class MainMenuScreen(ScreenBase):
    """
    Main menu screen for RecRadiko application
    
    Provides main navigation hub with options for:
    - Starting recording workflow
    - Viewing recording history
    - Accessing settings
    - Getting help
    - Exiting application
    """
    
    def __init__(self):
        """Initialize main menu screen"""
        super().__init__()
        self.set_title("RecRadiko - メインメニュー")
        self.menu_options = [
            "番組を録音する",
            "設定を変更",
            "ヘルプを表示",
            "終了"
        ]
        
    def display_content(self) -> None:
        """Display main menu content"""
        print("\nRecRadiko タイムフリー録音システム")
        print("=" * 40)
        print("\n以下のオプションから選択してください:\n")
        
        self.ui_service.set_menu_items(self.menu_options)
        self.ui_service.display_menu_with_highlight()
        
    def run_main_menu_loop(self) -> Optional[str]:
        """
        Run main menu interaction loop
        
        Returns:
            Screen name to navigate to, or None to stay/exit
        """
        while True:
            self.show()
            
            selected_option = self.ui_service.get_user_selection()
            
            if selected_option is None:
                # User cancelled (Escape key)
                return None
                
            result = self.handle_menu_selection(selected_option)
            
            if result is not None:
                return result
                
    def handle_menu_selection(self, selection: str) -> Optional[str]:
        """
        Handle menu selection and return navigation target
        
        Args:
            selection: Selected menu option
            
        Returns:
            Screen name to navigate to, or None to stay on main menu
        """
        if selection == "番組を録音する":
            self.start_recording_flow()
            return "station_select"
            
        elif selection == "設定を変更":
            self.show_settings()
            return "settings"
            
        elif selection == "ヘルプを表示":
            self.ui_service.display_help()
            print("\nRecRadiko ヘルプ")
            print("=" * 20)
            print("1. ↑/↓キー: メニュー項目の移動")
            print("2. Enterキー: 選択確定")
            print("3. Escキー: 前の画面に戻る")
            print("4. Qキー: アプリケーション終了")
            print("\n録音手順:")
            print("1. 放送局を選択")
            print("2. 録音日付を選択")
            print("3. 番組を選択して録音開始")
            print("\n任意のキーを押して続行...")
            self.ui_service.keyboard_handler.get_key()
            return None  # Stay on main menu
            
        elif selection == "終了":
            return "exit"
            
        else:
            self.ui_service.display_error(f"未知の選択: {selection}")
            return None
            
    def start_recording_flow(self) -> None:
        """Start the recording workflow"""
        print("\n録音ワークフローを開始します...")
        print("放送局選択画面に移動します。")
        
        
    def show_settings(self) -> None:
        """Show settings (prepare for navigation to settings screen)"""
        print("\n設定画面に移動します...")
        
    def confirm_exit(self) -> bool:
        """
        Confirm application exit
        
        Returns:
            True if user confirms exit, False otherwise
        """
        return self.ui_service.confirm_action("RecRadikoを終了しますか？")
        
    def on_back(self) -> None:
        """Handle back navigation (not applicable for main menu)"""
        # Main menu is the root screen, so back action shows exit confirmation
        if self.confirm_exit():
            # Signal exit to menu manager
            pass
            
    def get_current_selection_info(self) -> str:
        """
        Get information about current selection
        
        Returns:
            Information string about selected option
        """
        current_item = self.ui_service.get_current_item()
        
        if current_item == "番組を録音する":
            return "放送局 → 日付 → 番組の順で選択して録音を開始します"
        elif current_item == "設定を変更":
            return "地域設定、品質設定などを変更できます"
        elif current_item == "ヘルプを表示":
            return "キーボード操作方法と使用手順を表示します"
        elif current_item == "終了":
            return "RecRadikoアプリケーションを終了します"
        else:
            return ""
            
    def display_welcome_message(self) -> None:
        """Display welcome message for first-time users"""
        print("\n🎵 RecRadiko タイムフリー録音システムへようこそ！")
        print("=" * 50)
        print("\n📻 過去1週間のラジオ番組を高品質で録音できます")
        print("⚡ 10分番組を約5秒で録音完了（実時間の1/110高速処理）")
        print("🎯 MP3 256kbps, ID3タグ付き高品質出力")
        print("\n初回利用の方は「設定を変更」で地域を設定してください。")
        print("使い方が分からない場合は「ヘルプを表示」をご確認ください。")
        print("\n" + "=" * 50)
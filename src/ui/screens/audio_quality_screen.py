"""
Audio Quality Selection Screen for RecRadiko

Provides keyboard navigation interface for audio quality selection.
Supports various audio formats, bitrates, and sample rates.
"""

import sys
import os
from typing import List, Optional, Dict, Tuple
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.utils.base import LoggerMixin
from src.utils.config_utils import ConfigManager


class AudioQualityScreen(ScreenBase):
    """音質設定画面
    
    音声フォーマット、ビットレート、サンプルレートを選択可能
    """
    
    def __init__(self, config_file: str = "config.json"):
        super().__init__()
        self.set_title("音質設定")
        self.ui_service = UIService()
        
        # 統一設定管理を使用
        self.config_manager = ConfigManager(config_file)
        
        # 音質オプションを定義（Phase 8拡張: 4→8オプション）
        self.audio_options = [
            {
                "display": "MP3 128kbps, 44kHz",
                "format": "mp3",
                "bitrate": 128,
                "sample_rate": 44100,
                "description": "標準品質 - ファイルサイズ小"
            },
            {
                "display": "MP3 256kbps, 48kHz", 
                "format": "mp3",
                "bitrate": 256,
                "sample_rate": 48000,
                "description": "高品質 - 推奨設定"
            },
            {
                "display": "MP3 320kbps, 48kHz",
                "format": "mp3",
                "bitrate": 320,
                "sample_rate": 48000,
                "description": "超高品質 - 最高固定ビットレート"
            },
            {
                "display": "MP3 VBR V0, 48kHz",
                "format": "mp3",
                "bitrate": "VBR_V0",
                "sample_rate": 48000,
                "description": "可変最高品質 - 平均~245kbps"
            },
            {
                "display": "AAC 128kbps, 44kHz",
                "format": "aac",
                "bitrate": 128,
                "sample_rate": 44100,
                "description": "AAC標準品質"
            },
            {
                "display": "AAC 256kbps, 48kHz",
                "format": "aac", 
                "bitrate": 256,
                "sample_rate": 48000,
                "description": "AAC高品質"
            },
            {
                "display": "AAC 320kbps, 48kHz",
                "format": "aac",
                "bitrate": 320,
                "sample_rate": 48000,
                "description": "AAC超高品質 - 最高固定ビットレート"
            },
            {
                "display": "AAC VBR ~256kbps, 48kHz",
                "format": "aac",
                "bitrate": "VBR_HQ",
                "sample_rate": 48000,
                "description": "AAC可変高品質 - 平均~256kbps"
            }
        ]
        
    def display_header(self) -> None:
        """画面ヘッダーを表示"""
        print(f"\n=== {self.title} ===")
        print()
    
    def display_content(self) -> None:
        """画面コンテンツを表示（継承要求のため維持、実際はワークフローで使用しない）"""
        # このメソッドは使用されません。
        # 実際の表示は_display_current_info()と_setup_menu_items()で行います。
        pass
    
    def _display_current_info(self) -> None:
        """現在の設定情報を表示"""
        print("\n🎵 録音音質を選択してください")
        print("=" * 50)
        
        # 現在の設定を表示
        current_config = self.config_manager.load_config({})
        current_audio = current_config.get("audio", {})
        current_format = current_audio.get("format", "mp3")
        current_bitrate = current_audio.get("bitrate", 256)
        current_sample_rate = current_audio.get("sample_rate", 48000)
        
        # 現在の設定を人間が読める形式で表示
        if isinstance(current_bitrate, str):  # VBRオプション
            if current_bitrate == "VBR_V0":
                current_display = f"{current_format.upper()} VBR V0, {current_sample_rate//1000}kHz"
            elif current_bitrate == "VBR_HQ":
                current_display = f"{current_format.upper()} VBR ~256kbps, {current_sample_rate//1000}kHz"
            else:
                current_display = f"{current_format.upper()} {current_bitrate}, {current_sample_rate//1000}kHz"
        else:  # 固定ビットレート
            current_display = f"{current_format.upper()} {current_bitrate}kbps, {current_sample_rate//1000}kHz"
        print(f"現在の設定: {current_display}")
        print("")
    
    def _setup_menu_items(self) -> None:
        """メニューアイテムを設定"""
        # 現在の設定を取得
        current_config = self.config_manager.load_config({})
        current_audio = current_config.get("audio", {})
        current_format = current_audio.get("format", "mp3")
        current_bitrate = current_audio.get("bitrate", 256)
        current_sample_rate = current_audio.get("sample_rate", 48000)
        
        menu_items = []
        for option in self.audio_options:
            # 現在の設定かどうかをチェック（VBR対応）
            is_current = (
                option["format"] == current_format and
                option["bitrate"] == current_bitrate and
                option["sample_rate"] == current_sample_rate
            )
            
            if is_current:
                menu_items.append(f"{option['display']} ← 現在の設定")
            else:
                menu_items.append(f"{option['display']}")
        
        menu_items.append("🔙 設定画面に戻る")
        self.ui_service.set_menu_items(menu_items)
    
    def _handle_selection(self, selected_option: str) -> str:
        """選択項目に基づく処理"""
        if selected_option == "🔙 設定画面に戻る":
            return "back"
        
        # 選択された音質オプションを検索
        selected_audio = None
        for option in self.audio_options:
            if selected_option.startswith(option["display"]):
                selected_audio = option
                break
        
        if selected_audio:
            return self._update_audio_setting(selected_audio)
        
        return "continue"
    
    def _update_audio_setting(self, audio_option: Dict) -> str:
        """音質設定を更新"""
        try:
            # 現在の設定を読み込み
            config = self.config_manager.load_config({})
            
            # 音質設定を更新
            old_audio = config.get("audio", {})
            old_format = old_audio.get("format", "mp3")
            old_bitrate = old_audio.get("bitrate", 256)
            old_sample_rate = old_audio.get("sample_rate", 48000)
            
            config["audio"] = {
                "format": audio_option["format"],
                "bitrate": audio_option["bitrate"],
                "sample_rate": audio_option["sample_rate"]
            }
            
            # 設定を保存
            if self.config_manager.save_config(config):
                self.logger.info(f"音質設定更新: {old_format} {old_bitrate}kbps/{old_sample_rate}Hz → {audio_option['format']} {audio_option['bitrate']}kbps/{audio_option['sample_rate']}Hz")
                
                # 成功メッセージ表示
                print(f"\n✅ 音質設定を更新しました")
                print(f"   {audio_option['display']}")
                print(f"   {audio_option['description']}")
                print("\n設定画面に戻ります...")
                
                # 少し待ってから戻る
                import time
                time.sleep(1.5)
                
                return "success"
            else:
                self.logger.error(f"音質設定保存失敗: {audio_option['display']}")
                print(f"\n❌ 設定の保存に失敗しました")
                print("設定画面に戻ります...")
                
                import time
                time.sleep(1.5)
                
                return "back"
                
        except Exception as e:
            self.logger.error(f"音質設定更新エラー: {e}")
            print(f"\n❌ 設定の更新中にエラーが発生しました: {e}")
            print("設定画面に戻ります...")
            
            import time
            time.sleep(1.5)
            
            return "back"
    
    def run_audio_quality_workflow(self) -> bool:
        """音質設定ワークフローを実行"""
        try:
            self.logger.info("音質設定画面開始")
            
            while True:
                # ヘッダー情報を表示（UIServiceによるメニュー表示前に）
                print('\033[2J\033[H', end='')  # 画面クリア
                self.display_header()
                self._display_current_info()
                
                # メニューアイテムを設定
                self._setup_menu_items()
                
                # ユーザー選択を取得（UIServiceが標準的なメニュー表示を行う）
                selected_option = self.ui_service.get_user_selection()
                
                if selected_option is None:
                    # Escapeキーまたはキャンセル
                    self.logger.info("音質設定画面終了")
                    return False
                
                # 選択に基づく処理
                result = self._handle_selection(selected_option)
                
                if result == "success":
                    self.logger.info("音質設定更新完了")
                    return True
                elif result == "back":
                    self.logger.info("音質設定画面終了")
                    return False
                # "continue"の場合は画面再描画
                
        except KeyboardInterrupt:
            print("\n\n音質設定をキャンセルしました")
            return False
        except Exception as e:
            self.logger.error(f"音質設定画面エラー: {e}")
            print(f"\n❌ エラーが発生しました: {e}")
            return False


def main():
    """テスト用メイン関数"""
    screen = AudioQualityScreen()
    screen.run_audio_quality_workflow()


if __name__ == "__main__":
    main()
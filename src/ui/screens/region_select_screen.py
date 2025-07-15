"""
Region Selection Screen for RecRadiko

Provides keyboard navigation interface for region/prefecture selection.
Supports all 47 prefectures with organized display by regions.
"""

import sys
import os
from typing import List, Optional, Dict, Tuple
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.region_mapper import RegionMapper
from src.utils.base import LoggerMixin
from src.utils.config_utils import ConfigManager


class RegionSelectScreen(ScreenBase):
    """地域選択画面
    
    47都道府県を地方別に整理して表示し、キーボードナビゲーションで選択可能
    """
    
    def __init__(self, config_file: str = "config.json"):
        super().__init__()
        self.set_title("地域選択")
        self.ui_service = UIService()
        self.region_mapper = RegionMapper()
        
        # 統一設定管理を使用
        self.config_manager = ConfigManager(config_file)
        self.current_region = None
        
        # 地方別の都道府県リスト
        self.regions_by_area = self._organize_prefectures_by_region()
        self.current_view = "region_list"  # region_list or prefecture_list
        self.selected_region_name = None
        self.selected_prefecture = None
        
    def _organize_prefectures_by_region(self) -> Dict[str, List[Tuple[str, str]]]:
        """都道府県を地方別に整理"""
        regions = {}
        
        for area_id, region_info in RegionMapper.REGION_INFO.items():
            region_name = region_info.region_name
            prefecture_name = region_info.prefecture_ja
            
            if region_name not in regions:
                regions[region_name] = []
            
            regions[region_name].append((prefecture_name, area_id))
        
        # 各地方内で都道府県をソート
        for region_name in regions:
            regions[region_name].sort(key=lambda x: x[0])
        
        return regions
    
    def display_content(self) -> None:
        """画面コンテンツを表示"""
        if self.current_view == "region_list":
            self._display_region_list()
        else:
            self._display_prefecture_list()
    
    def _display_region_list(self) -> None:
        """地方一覧を表示"""
        print("\n📍 地域を選択してください")
        print("=" * 50)
        
        # 現在の設定を表示
        current_config = self.config_manager.load_config({})
        current_area_id = current_config.get("area_id", "JP13")
        current_region_info = self.region_mapper.get_region_info(current_area_id)
        
        if current_region_info:
            print(f"現在の設定: {current_region_info.prefecture_ja} ({current_area_id})")
            print("")
        
        # 地方一覧を表示
        region_names = list(self.regions_by_area.keys())
        region_names.sort()  # 地方名でソート
        
        menu_items = []
        for region_name in region_names:
            prefecture_count = len(self.regions_by_area[region_name])
            menu_items.append(f"{region_name} ({prefecture_count}都道府県)")
        
        menu_items.append("🔙 設定画面に戻る")
        
        self.ui_service.set_menu_items(menu_items)
        self.ui_service.display_menu_with_highlight()
        
        print("\n操作方法:")
        print("↑↓キー: 地方選択")
        print("Enter: 地方内の都道府県を表示")
        print("ESC: 設定画面に戻る")
    
    def _display_prefecture_list(self) -> None:
        """選択された地方の都道府県一覧を表示"""
        if not self.selected_region_name:
            return
        
        print(f"\n📍 {self.selected_region_name}の都道府県を選択してください")
        print("=" * 50)
        
        # 現在の設定を表示
        current_config = self.config_manager.load_config({})
        current_area_id = current_config.get("area_id", "JP13")
        current_region_info = self.region_mapper.get_region_info(current_area_id)
        
        if current_region_info:
            print(f"現在の設定: {current_region_info.prefecture_ja} ({current_area_id})")
            print("")
        
        # 都道府県一覧を表示
        prefectures = self.regions_by_area[self.selected_region_name]
        menu_items = []
        
        for prefecture_name, area_id in prefectures:
            # 現在の設定にマーク
            if area_id == current_area_id:
                menu_items.append(f"{prefecture_name} ({area_id}) ← 現在の設定")
            else:
                menu_items.append(f"{prefecture_name} ({area_id})")
        
        menu_items.append("🔙 地方一覧に戻る")
        
        self.ui_service.set_menu_items(menu_items)
        self.ui_service.display_menu_with_highlight()
        
        print("\n操作方法:")
        print("↑↓キー: 都道府県選択")
        print("Enter: この都道府県に設定")
        print("ESC: 地方一覧に戻る")
    
    def handle_input(self, key: str) -> Optional[str]:
        """キー入力処理"""
        if key == "escape":
            if self.current_view == "prefecture_list":
                # 都道府県一覧から地方一覧へ戻る
                self.current_view = "region_list"
                self.selected_region_name = None
                return "refresh"
            else:
                # 地方一覧から設定画面へ戻る
                return "back"
        
        elif key == "enter":
            if self.current_view == "region_list":
                return self._handle_region_selection()
            else:
                return self._handle_prefecture_selection()
        
        elif key in ["up", "down"]:
            self.ui_service.handle_navigation(key)
            return "refresh"
        
        return None
    
    def _handle_region_selection(self) -> Optional[str]:
        """地方選択の処理"""
        selected_index = self.ui_service.get_selected_index()
        region_names = list(self.regions_by_area.keys())
        region_names.sort()
        
        if selected_index < len(region_names):
            # 地方選択 → 都道府県一覧へ
            self.selected_region_name = region_names[selected_index]
            self.current_view = "prefecture_list"
            self.ui_service.reset_selection()  # 選択位置をリセット
            return "refresh"
        else:
            # 「戻る」選択
            return "back"
    
    def _handle_prefecture_selection(self) -> Optional[str]:
        """都道府県選択の処理"""
        selected_index = self.ui_service.get_selected_index()
        prefectures = self.regions_by_area[self.selected_region_name]
        
        if selected_index < len(prefectures):
            # 都道府県選択 → 設定更新
            prefecture_name, area_id = prefectures[selected_index]
            return self._update_region_setting(prefecture_name, area_id)
        else:
            # 「戻る」選択
            self.current_view = "region_list"
            self.selected_region_name = None
            self.ui_service.reset_selection()
            return "refresh"
    
    def _update_region_setting(self, prefecture_name: str, area_id: str) -> str:
        """地域設定を更新"""
        try:
            # 現在の設定を読み込み
            config = self.config_manager.load_config({})
            
            # 地域設定を更新
            old_area_id = config.get("area_id", "JP13")
            old_prefecture = config.get("prefecture", "")
            
            config["area_id"] = area_id
            config["prefecture"] = prefecture_name
            
            # 設定を保存
            if self.config_manager.save_config(config):
                self.logger.info(f"地域設定更新: {old_prefecture}({old_area_id}) → {prefecture_name}({area_id})")
                
                # 成功メッセージ表示
                print(f"\n✅ 地域設定を更新しました")
                print(f"   {prefecture_name} ({area_id})")
                print("\n設定画面に戻ります...")
                
                # 少し待ってから戻る
                import time
                time.sleep(1.5)
                
                return "back"
            else:
                self.logger.error(f"地域設定保存失敗: {prefecture_name}({area_id})")
                print(f"\n❌ 設定の保存に失敗しました")
                print("設定画面に戻ります...")
                
                import time
                time.sleep(1.5)
                
                return "back"
                
        except Exception as e:
            self.logger.error(f"地域設定更新エラー: {e}")
            print(f"\n❌ 設定の更新中にエラーが発生しました: {e}")
            print("設定画面に戻ります...")
            
            import time
            time.sleep(1.5)
            
            return "back"
    
    def run_region_selection_workflow(self) -> bool:
        """地域選択ワークフローを実行"""
        try:
            self.logger.info("地域選択画面開始")
            
            while True:
                # 画面をクリア
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # ヘッダー表示
                self.display_header()
                
                # コンテンツ表示
                self.display_content()
                
                # キー入力待ち
                key = self.ui_service.get_key_input()
                
                # キー入力処理
                result = self.handle_input(key)
                
                if result == "back":
                    self.logger.info("地域選択画面終了")
                    return True
                elif result == "refresh":
                    continue  # 画面再描画
                
        except KeyboardInterrupt:
            print("\n\n地域選択をキャンセルしました")
            return False
        except Exception as e:
            self.logger.error(f"地域選択画面エラー: {e}")
            print(f"\n❌ エラーが発生しました: {e}")
            return False


def main():
    """テスト用メイン関数"""
    screen = RegionSelectScreen()
    screen.run_region_selection_workflow()


if __name__ == "__main__":
    main()
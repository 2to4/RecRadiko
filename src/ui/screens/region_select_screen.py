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
    
    def display_header(self) -> None:
        """画面ヘッダーを表示"""
        print(f"\n=== {self.title} ===")
        print()
    
    def display_content(self) -> None:
        """画面コンテンツを表示（継承要求のため維持、実際はワークフローで使用しない）"""
        # このメソッドは使用されません。
        # 実際の表示は_display_current_info()と_setup_menu_items()で行います。
        pass
    
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
                
                return "success"
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
    
    def _handle_selection(self, selected_option: str) -> str:
        """選択項目に基づく処理"""
        if selected_option == "🔙 設定画面に戻る":
            return "back"
        
        if self.current_view == "region_list":
            # 地方選択の処理
            if selected_option.endswith("都道府県)"):
                # 地方名を抽出
                region_name = selected_option.split(" (")[0]
                self.selected_region_name = region_name
                self.current_view = "prefecture_list"
                return "continue"
            else:
                return "back"
        
        elif self.current_view == "prefecture_list":
            # 都道府県選択の処理
            if selected_option == "🔙 地方一覧に戻る":
                self.current_view = "region_list"
                self.selected_region_name = None
                return "continue"
            else:
                # 都道府県が選択された
                # "県名 (JP##)" または "県名 (JP##) ← 現在の設定" の形式
                prefecture_info = selected_option.split(" (")[0]
                area_id_part = selected_option.split(" (")[1].split(")")[0]
                
                return self._update_region_setting(prefecture_info, area_id_part)
        
        return "continue"
    
    def _display_current_info(self) -> None:
        """現在の設定情報とナビゲーション情報を表示"""
        if self.current_view == "region_list":
            print("\n📍 地域を選択してください")
        else:
            print(f"\n📍 {self.selected_region_name}の都道府県を選択してください")
        
        print("=" * 50)
        
        # 現在の設定を表示
        current_config = self.config_manager.load_config({})
        current_area_id = current_config.get("area_id", "JP13")
        current_region_info = self.region_mapper.get_region_info(current_area_id)
        
        if current_region_info:
            print(f"現在の設定: {current_region_info.prefecture_ja} ({current_area_id})")
            print("")
    
    def _setup_menu_items(self) -> None:
        """現在のビューに応じてメニューアイテムを設定"""
        if self.current_view == "region_list":
            # 地方一覧を設定
            region_names = list(self.regions_by_area.keys())
            region_names.sort()
            
            menu_items = []
            for region_name in region_names:
                prefecture_count = len(self.regions_by_area[region_name])
                menu_items.append(f"{region_name} ({prefecture_count}都道府県)")
            
            menu_items.append("🔙 設定画面に戻る")
            self.ui_service.set_menu_items(menu_items)
            
        else:
            # 都道府県一覧を設定
            prefectures = self.regions_by_area[self.selected_region_name]
            current_config = self.config_manager.load_config({})
            current_area_id = current_config.get("area_id", "JP13")
            
            menu_items = []
            for prefecture_name, area_id in prefectures:
                if area_id == current_area_id:
                    menu_items.append(f"{prefecture_name} ({area_id}) ← 現在の設定")
                else:
                    menu_items.append(f"{prefecture_name} ({area_id})")
            
            menu_items.append("🔙 地方一覧に戻る")
            self.ui_service.set_menu_items(menu_items)
    
    def run_region_selection_workflow(self) -> bool:
        """地域選択ワークフローを実行"""
        try:
            self.logger.info("地域選択画面開始")
            
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
                    if self.current_view == "prefecture_list":
                        # 都道府県一覧から地方一覧へ戻る
                        self.current_view = "region_list"
                        self.selected_region_name = None
                        continue
                    else:
                        # 地方一覧から設定画面へ戻る
                        self.logger.info("地域選択画面終了")
                        return False
                
                # 選択に基づく処理
                result = self._handle_selection(selected_option)
                
                if result == "success":
                    self.logger.info("地域設定更新完了")
                    return True
                elif result == "back":
                    self.logger.info("地域選択画面終了")
                    return False
                # "continue"の場合は画面再描画
                
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
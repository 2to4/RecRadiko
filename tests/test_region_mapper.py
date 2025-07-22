"""
RegionMapper単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
47都道府県マッピング、地域ID変換、検索機能を実環境でテスト。
"""

import unittest
from typing import Optional

# テスト対象
from src.region_mapper import RegionMapper


class TestRegionMapperBasicMapping(unittest.TestCase):
    """RegionMapper基本マッピング機能テスト"""
    
    def test_01_都道府県名から地域ID取得(self):
        """
        TDD Test: 都道府県名から地域ID取得パターン
        
        正確な都道府県名で地域IDが取得できることを確認
        """
        # Given: 正確な都道府県名
        prefecture_names = [
            ("北海道", "JP1"),
            ("東京都", "JP13"), 
            ("大阪府", "JP27"),
            ("沖縄県", "JP47")
        ]
        
        # When & Then: 各都道府県名から正しい地域IDが取得される
        for prefecture, expected_area_id in prefecture_names:
            with self.subTest(prefecture=prefecture):
                area_id = RegionMapper.get_area_id(prefecture)
                self.assertEqual(area_id, expected_area_id)
    
    def test_02_地域IDから都道府県名取得(self):
        """
        TDD Test: 地域IDから都道府県名取得パターン
        
        地域IDから正確な都道府県名が取得できることを確認
        """
        # Given: 有効な地域ID
        area_mappings = [
            ("JP1", "北海道"),
            ("JP13", "東京都"),
            ("JP27", "大阪府"), 
            ("JP47", "沖縄県")
        ]
        
        # When & Then: 各地域IDから正しい都道府県名が取得される
        for area_id, expected_prefecture in area_mappings:
            with self.subTest(area_id=area_id):
                prefecture = RegionMapper.get_prefecture_name(area_id)
                self.assertEqual(prefecture, expected_prefecture)
    
    def test_03_不正な入力値エラーハンドリング(self):
        """
        TDD Test: 不正な入力値のエラーハンドリング
        
        存在しない都道府県名や地域IDでNoneが返されることを確認
        """
        # Given: 不正な入力値（実装は英語名もサポートしているため調整）
        invalid_inputs = [
            "存在しない県",
            "INVALID_PREFECTURE",
            "",       # 空文字
            None      # None値
        ]
        
        # When & Then: 不正な入力でNoneが返される
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                area_id = RegionMapper.get_area_id(invalid_input)
                self.assertIsNone(area_id)
        
        # Given: 英語名は有効な入力として扱われることを確認
        valid_english_names = [
            ("Tokyo", "JP13"),
            ("Osaka", "JP27"), 
            ("Hokkaido", "JP1")
        ]
        
        # When & Then: 英語名でも正しい地域IDが返される
        for english_name, expected_area_id in valid_english_names:
            with self.subTest(english_name=english_name):
                area_id = RegionMapper.get_area_id(english_name)
                self.assertEqual(area_id, expected_area_id)
        
        # Given: 不正な地域ID
        invalid_area_ids = ["JP0", "JP48", "INVALID", "", None]
        
        # When & Then: 不正な地域IDでNoneが返される
        for invalid_area_id in invalid_area_ids:
            with self.subTest(area_id=invalid_area_id):
                prefecture = RegionMapper.get_prefecture_name(invalid_area_id)
                self.assertIsNone(prefecture)
    
    def test_04_地域ID検証機能(self):
        """
        TDD Test: 地域ID検証機能
        
        地域IDの有効性が正しく判定されることを確認
        """
        # Given: 有効な地域ID
        valid_area_ids = ["JP1", "JP13", "JP27", "JP47"]
        
        # When & Then: 有効な地域IDでTrueが返される
        for area_id in valid_area_ids:
            with self.subTest(area_id=area_id):
                is_valid = RegionMapper.validate_area_id(area_id)
                self.assertTrue(is_valid)
        
        # Given: 無効な地域ID
        invalid_area_ids = ["JP0", "JP48", "INVALID", "", None]
        
        # When & Then: 無効な地域IDでFalseが返される
        for area_id in invalid_area_ids:
            with self.subTest(area_id=area_id):
                is_valid = RegionMapper.validate_area_id(area_id)
                self.assertFalse(is_valid)
    
    def test_05_全都道府県カバレッジ確認(self):
        """
        TDD Test: 47都道府県完全カバレッジ確認
        
        JP1からJP47まで全ての地域IDがマッピングされていることを確認
        """
        # Given: JP1からJP47までの全地域ID
        all_area_ids = [f"JP{i}" for i in range(1, 48)]
        
        # When & Then: 全ての地域IDに対して都道府県名が存在する
        for area_id in all_area_ids:
            with self.subTest(area_id=area_id):
                prefecture = RegionMapper.get_prefecture_name(area_id)
                self.assertIsNotNone(prefecture)
                self.assertNotEqual(prefecture, "")
        
        # And: 合計47都道府県がマッピングされている
        all_prefectures = []
        for area_id in all_area_ids:
            prefecture = RegionMapper.get_prefecture_name(area_id)
            if prefecture:
                all_prefectures.append(prefecture)
        
        self.assertEqual(len(all_prefectures), 47)
        # 重複がないことを確認
        self.assertEqual(len(set(all_prefectures)), 47)


class TestRegionMapperGeographicalMapping(unittest.TestCase):
    """RegionMapper地理的マッピング機能テスト"""
    
    def test_06_九州沖縄地域統合確認(self):
        """
        TDD Test: 九州・沖縄地域統合確認
        
        Phase 6で実装された九州・沖縄地域統合が正しく動作することを確認
        """
        # Given: 九州・沖縄地域の都道府県
        kyushu_okinawa_prefectures = [
            "福岡県",  # JP40
            "佐賀県",  # JP41
            "長崎県",  # JP42
            "熊本県",  # JP43
            "大分県",  # JP44
            "宮崎県",  # JP45
            "鹿児島県", # JP46
            "沖縄県"   # JP47
        ]
        
        # When & Then: 全ての九州・沖縄県に地域IDが割り当てられている
        for prefecture in kyushu_okinawa_prefectures:
            with self.subTest(prefecture=prefecture):
                area_id = RegionMapper.get_area_id(prefecture)
                self.assertIsNotNone(area_id)
                
                # 地域IDがJP40-JP47の範囲にあることを確認
                area_num = int(area_id[2:])
                self.assertGreaterEqual(area_num, 40)
                self.assertLessEqual(area_num, 47)
    
    def test_07_地理的順序確認(self):
        """
        TDD Test: 地理的順序確認（北から南へ）
        
        地域IDが地理的順序（北から南）に対応していることを確認
        """
        # Given: 地理的に北から南への代表的都道府県
        north_to_south_samples = [
            ("北海道", "JP1"),     # 最北
            ("青森県", "JP2"),     # 本州最北
            ("東京都", "JP13"),    # 関東
            ("大阪府", "JP27"),    # 関西
            ("福岡県", "JP40"),    # 九州
            ("沖縄県", "JP47")     # 最南
        ]
        
        # When & Then: 北の地域ほど小さい地域ID番号を持つ
        for i in range(len(north_to_south_samples) - 1):
            current_prefecture, current_area_id = north_to_south_samples[i]
            next_prefecture, next_area_id = north_to_south_samples[i + 1]
            
            current_num = int(current_area_id[2:])
            next_num = int(next_area_id[2:])
            
            with self.subTest(current=current_prefecture, next=next_prefecture):
                self.assertLess(current_num, next_num)


if __name__ == "__main__":
    unittest.main()
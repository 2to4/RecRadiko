"""
RegionMapper（地域IDマッピング）の単体テスト

47都道府県すべてのマッピングテストと、エラーケースのテストを実施
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# テスト対象のインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from region_mapper import RegionMapper, RegionInfo


class TestRegionMapper(unittest.TestCase):
    """RegionMapperクラスの単体テスト"""

    def test_all_47_prefectures_japanese_names(self):
        """47都道府県すべての日本語名マッピングテスト"""
        # 47都道府県の日本語名と期待される地域ID
        prefecture_mapping = {
            # 北海道・東北地方
            "北海道": "JP1",
            "青森": "JP2", "青森県": "JP2",
            "岩手": "JP3", "岩手県": "JP3",
            "宮城": "JP4", "宮城県": "JP4",
            "秋田": "JP5", "秋田県": "JP5",
            "山形": "JP6", "山形県": "JP6",
            "福島": "JP7", "福島県": "JP7",
            
            # 関東地方
            "茨城": "JP8", "茨城県": "JP8",
            "栃木": "JP9", "栃木県": "JP9",
            "群馬": "JP10", "群馬県": "JP10",
            "埼玉": "JP11", "埼玉県": "JP11",
            "千葉": "JP12", "千葉県": "JP12",
            "東京": "JP13", "東京都": "JP13",
            "神奈川": "JP14", "神奈川県": "JP14",
            
            # 中部地方
            "新潟": "JP15", "新潟県": "JP15",
            "富山": "JP16", "富山県": "JP16",
            "石川": "JP17", "石川県": "JP17",
            "福井": "JP18", "福井県": "JP18",
            "山梨": "JP19", "山梨県": "JP19",
            "長野": "JP20", "長野県": "JP20",
            "岐阜": "JP21", "岐阜県": "JP21",
            "静岡": "JP22", "静岡県": "JP22",
            "愛知": "JP23", "愛知県": "JP23",
            
            # 近畿地方
            "三重": "JP24", "三重県": "JP24",
            "滋賀": "JP25", "滋賀県": "JP25",
            "京都": "JP26", "京都府": "JP26",
            "大阪": "JP27", "大阪府": "JP27",
            "兵庫": "JP28", "兵庫県": "JP28",
            "奈良": "JP29", "奈良県": "JP29",
            "和歌山": "JP30", "和歌山県": "JP30",
            
            # 中国地方
            "鳥取": "JP31", "鳥取県": "JP31",
            "島根": "JP32", "島根県": "JP32",
            "岡山": "JP33", "岡山県": "JP33",
            "広島": "JP34", "広島県": "JP34",
            "山口": "JP35", "山口県": "JP35",
            
            # 四国地方
            "徳島": "JP36", "徳島県": "JP36",
            "香川": "JP37", "香川県": "JP37",
            "愛媛": "JP38", "愛媛県": "JP38",
            "高知": "JP39", "高知県": "JP39",
            
            # 九州・沖縄地方
            "福岡": "JP40", "福岡県": "JP40",
            "佐賀": "JP41", "佐賀県": "JP41",
            "長崎": "JP42", "長崎県": "JP42",
            "熊本": "JP43", "熊本県": "JP43",
            "大分": "JP44", "大分県": "JP44",
            "宮崎": "JP45", "宮崎県": "JP45",
            "鹿児島": "JP46", "鹿児島県": "JP46",
            "沖縄": "JP47", "沖縄県": "JP47",
        }
        
        failed_mappings = []
        
        for prefecture, expected_area_id in prefecture_mapping.items():
            with self.subTest(prefecture=prefecture):
                result = RegionMapper.get_area_id(prefecture)
                if result != expected_area_id:
                    failed_mappings.append(f"{prefecture} -> {result} (期待値: {expected_area_id})")
                self.assertEqual(result, expected_area_id, 
                    f"日本語名マッピング失敗: {prefecture} -> {result} (期待値: {expected_area_id})")
        
        # 失敗した場合は詳細を表示
        if failed_mappings:
            self.fail(f"日本語名マッピングテストで失敗: {failed_mappings}")

    def test_all_47_prefectures_english_names(self):
        """47都道府県すべての英語名マッピングテスト"""
        # 47都道府県の英語名と期待される地域ID
        english_mapping = {
            # 北海道・東北地方
            "Hokkaido": "JP1", "hokkaido": "JP1",
            "Aomori": "JP2", "aomori": "JP2",
            "Iwate": "JP3", "iwate": "JP3",
            "Miyagi": "JP4", "miyagi": "JP4",
            "Akita": "JP5", "akita": "JP5",
            "Yamagata": "JP6", "yamagata": "JP6",
            "Fukushima": "JP7", "fukushima": "JP7",
            
            # 関東地方
            "Ibaraki": "JP8", "ibaraki": "JP8",
            "Tochigi": "JP9", "tochigi": "JP9",
            "Gunma": "JP10", "gunma": "JP10",
            "Saitama": "JP11", "saitama": "JP11",
            "Chiba": "JP12", "chiba": "JP12",
            "Tokyo": "JP13", "tokyo": "JP13",
            "Kanagawa": "JP14", "kanagawa": "JP14",
            
            # 中部地方
            "Niigata": "JP15", "niigata": "JP15",
            "Toyama": "JP16", "toyama": "JP16",
            "Ishikawa": "JP17", "ishikawa": "JP17",
            "Fukui": "JP18", "fukui": "JP18",
            "Yamanashi": "JP19", "yamanashi": "JP19",
            "Nagano": "JP20", "nagano": "JP20",
            "Gifu": "JP21", "gifu": "JP21",
            "Shizuoka": "JP22", "shizuoka": "JP22",
            "Aichi": "JP23", "aichi": "JP23",
            
            # 近畿地方
            "Mie": "JP24", "mie": "JP24",
            "Shiga": "JP25", "shiga": "JP25",
            "Kyoto": "JP26", "kyoto": "JP26",
            "Osaka": "JP27", "osaka": "JP27",
            "Hyogo": "JP28", "hyogo": "JP28",
            "Nara": "JP29", "nara": "JP29",
            "Wakayama": "JP30", "wakayama": "JP30",
            
            # 中国地方
            "Tottori": "JP31", "tottori": "JP31",
            "Shimane": "JP32", "shimane": "JP32",
            "Okayama": "JP33", "okayama": "JP33",
            "Hiroshima": "JP34", "hiroshima": "JP34",
            "Yamaguchi": "JP35", "yamaguchi": "JP35",
            
            # 四国地方
            "Tokushima": "JP36", "tokushima": "JP36",
            "Kagawa": "JP37", "kagawa": "JP37",
            "Ehime": "JP38", "ehime": "JP38",
            "Kochi": "JP39", "kochi": "JP39",
            
            # 九州・沖縄地方
            "Fukuoka": "JP40", "fukuoka": "JP40",
            "Saga": "JP41", "saga": "JP41",
            "Nagasaki": "JP42", "nagasaki": "JP42",
            "Kumamoto": "JP43", "kumamoto": "JP43",
            "Oita": "JP44", "oita": "JP44",
            "Miyazaki": "JP45", "miyazaki": "JP45",
            "Kagoshima": "JP46", "kagoshima": "JP46",
            "Okinawa": "JP47", "okinawa": "JP47",
        }
        
        failed_mappings = []
        
        for prefecture, expected_area_id in english_mapping.items():
            with self.subTest(prefecture=prefecture):
                result = RegionMapper.get_area_id(prefecture)
                if result != expected_area_id:
                    failed_mappings.append(f"{prefecture} -> {result} (期待値: {expected_area_id})")
                self.assertEqual(result, expected_area_id,
                    f"英語名マッピング失敗: {prefecture} -> {result} (期待値: {expected_area_id})")
        
        # 失敗した場合は詳細を表示
        if failed_mappings:
            self.fail(f"英語名マッピングテストで失敗: {failed_mappings}")

    def test_all_47_prefectures_reverse_mapping(self):
        """47都道府県すべての逆引きマッピングテスト（地域ID -> 都道府県名）"""
        # 47都道府県の地域IDと期待される日本語名
        reverse_mapping = {
            # 北海道・東北地方
            "JP1": "北海道",
            "JP2": "青森県", "JP3": "岩手県", "JP4": "宮城県",
            "JP5": "秋田県", "JP6": "山形県", "JP7": "福島県",
            
            # 関東地方
            "JP8": "茨城県", "JP9": "栃木県", "JP10": "群馬県",
            "JP11": "埼玉県", "JP12": "千葉県", "JP13": "東京都", "JP14": "神奈川県",
            
            # 中部地方
            "JP15": "新潟県", "JP16": "富山県", "JP17": "石川県", "JP18": "福井県",
            "JP19": "山梨県", "JP20": "長野県", "JP21": "岐阜県", "JP22": "静岡県", "JP23": "愛知県",
            
            # 近畿地方
            "JP24": "三重県", "JP25": "滋賀県", "JP26": "京都府", "JP27": "大阪府",
            "JP28": "兵庫県", "JP29": "奈良県", "JP30": "和歌山県",
            
            # 中国地方
            "JP31": "鳥取県", "JP32": "島根県", "JP33": "岡山県",
            "JP34": "広島県", "JP35": "山口県",
            
            # 四国地方
            "JP36": "徳島県", "JP37": "香川県", "JP38": "愛媛県", "JP39": "高知県",
            
            # 九州・沖縄地方
            "JP40": "福岡県", "JP41": "佐賀県", "JP42": "長崎県", "JP43": "熊本県",
            "JP44": "大分県", "JP45": "宮崎県", "JP46": "鹿児島県", "JP47": "沖縄県",
        }
        
        failed_mappings = []
        
        for area_id, expected_prefecture in reverse_mapping.items():
            with self.subTest(area_id=area_id):
                result = RegionMapper.get_prefecture_name(area_id)
                if result != expected_prefecture:
                    failed_mappings.append(f"{area_id} -> {result} (期待値: {expected_prefecture})")
                self.assertEqual(result, expected_prefecture,
                    f"逆引きマッピング失敗: {area_id} -> {result} (期待値: {expected_prefecture})")
        
        # 失敗した場合は詳細を表示
        if failed_mappings:
            self.fail(f"逆引きマッピングテストで失敗: {failed_mappings}")

    def test_invalid_prefecture_names(self):
        """無効な都道府県名のテスト"""
        # 完全に無効な名前（空白除去後も無効）
        truly_invalid_names = [
            "",  # 空文字
            " ",  # スペースのみ
            "存在しない県",  # 存在しない都道府県
            "Unknown Prefecture",  # 存在しない英語名
            "新東京",  # 間違った都道府県名
            "大阪市",  # 市名（都道府県名ではない）
            "東京区",  # 不正な東京の表記
            "北海",  # 不完全な都道府県名
            "123",  # 数字
            "東京県",  # 間違った接尾辞
            "大阪都",  # 間違った接尾辞
            "北海道府",  # 間違った接尾辞
            "TOKYO-TO",  # 大文字だが存在しないパターン
            "おおさか",  # ひらがな
            "トウキョウ",  # カタカナ
            "東　京",  # 全角スペース入り（間に空白）
            "東京・大阪",  # 複数都道府県
            "関東",  # 地方名
            "九州",  # 地方名
            "日本",  # 国名
            "null",  # null文字列
            "None",  # None文字列
            "undefined",  # undefined文字列
        ]
        
        # 空白文字が除去されると有効になる名前（ユーザビリティのため許可）
        whitespace_valid_names = [
            "東京\n",  # 改行文字入り（strip後は「東京」）
            "東京\t",  # タブ文字入り（strip後は「東京」）
        ]
        
        # 完全に無効な名前のテスト
        for invalid_name in truly_invalid_names:
            with self.subTest(invalid_name=repr(invalid_name)):
                result = RegionMapper.get_area_id(invalid_name)
                self.assertIsNone(result, 
                    f"無効な都道府県名'{invalid_name}'に対してNone以外が返されました: {result}")
        
        # 空白除去により有効になる名前のテスト（ユーザビリティ確認）
        for valid_name in whitespace_valid_names:
            with self.subTest(valid_name=repr(valid_name)):
                result = RegionMapper.get_area_id(valid_name)
                self.assertEqual(result, "JP13", 
                    f"空白除去により有効な都道府県名'{valid_name}'が正しく認識されませんでした")

    def test_none_and_empty_inputs(self):
        """None値と空入力のテスト"""
        # None値のテスト（実際にはNoneが渡されることはないが、安全性のため）
        result = RegionMapper.get_area_id("")
        self.assertIsNone(result)
        
        # 空白のみの入力
        result = RegionMapper.get_area_id("   ")
        self.assertIsNone(result)

    def test_invalid_area_ids(self):
        """無効な地域IDのテスト"""
        invalid_area_ids = [
            "",  # 空文字
            " ",  # スペースのみ
            "JP0",  # 範囲外（小）
            "JP48",  # 範囲外（大）
            "JP99",  # 範囲外
            "JP999",  # 範囲外
            "US13",  # 間違った国コード
            "JP",  # 不完全
            "13",  # 番号のみ
            "Tokyo",  # 都道府県名
            "japan13",  # 間違った形式
            "JP-13",  # ハイフン入り
            "JP_13",  # アンダースコア入り
            "jp13",  # 小文字
            "Jp13",  # 大文字小文字混在
            "JP013",  # ゼロパディング
            "JP13.0",  # 小数点
            "JP13A",  # 文字混在
            "NULL",  # NULL文字列
            "undefined",  # undefined
        ]
        
        for invalid_area_id in invalid_area_ids:
            with self.subTest(area_id=repr(invalid_area_id)):
                # 都道府県名取得テスト
                result = RegionMapper.get_prefecture_name(invalid_area_id)
                self.assertIsNone(result,
                    f"無効な地域ID'{invalid_area_id}'に対してNone以外が返されました: {result}")
                
                # 地域情報取得テスト
                info = RegionMapper.get_region_info(invalid_area_id)
                self.assertIsNone(info,
                    f"無効な地域ID'{invalid_area_id}'に対してNone以外が返されました: {info}")
                
                # 検証テスト
                is_valid = RegionMapper.validate_area_id(invalid_area_id)
                self.assertFalse(is_valid,
                    f"無効な地域ID'{invalid_area_id}'がvalidと判定されました")

    def test_region_info_completeness(self):
        """地域情報の完全性テスト"""
        # 全47都道府県の地域情報が正しく設定されているかテスト
        for i in range(1, 48):
            area_id = f"JP{i}"
            with self.subTest(area_id=area_id):
                info = RegionMapper.get_region_info(area_id)
                self.assertIsNotNone(info, f"地域情報が取得できません: {area_id}")
                self.assertEqual(info.area_id, area_id)
                self.assertIsNotNone(info.prefecture_ja, f"日本語名が設定されていません: {area_id}")
                self.assertIsNotNone(info.prefecture_en, f"英語名が設定されていません: {area_id}")
                self.assertIsNotNone(info.region_name, f"地方名が設定されていません: {area_id}")
                self.assertIsInstance(info.major_stations, list, f"主要放送局がリストではありません: {area_id}")
                self.assertGreater(len(info.prefecture_ja), 0, f"日本語名が空です: {area_id}")
                self.assertGreater(len(info.prefecture_en), 0, f"英語名が空です: {area_id}")

    def test_major_stations_data(self):
        """主要放送局データのテスト"""
        # 主要都市圏の放送局データが正しく設定されているかテスト
        major_cities = {
            "JP13": ["TBS", "QRR", "LFR", "INT", "FMT", "FMJ", "JORF"],  # 東京
            "JP27": ["OBC", "MBS", "ABC", "FM-OSAKA", "FM802"],  # 大阪
            "JP1": ["HBC", "STV", "AIR-G'"],  # 北海道
            "JP40": ["RKB", "KBC", "FM-FUKUOKA", "LOVEFM"],  # 福岡
        }
        
        for area_id, expected_stations in major_cities.items():
            with self.subTest(area_id=area_id):
                info = RegionMapper.get_region_info(area_id)
                self.assertIsNotNone(info)
                self.assertEqual(info.major_stations, expected_stations,
                    f"主要放送局リストが期待値と異なります: {area_id}")

    def test_search_functionality(self):
        """検索機能のテスト"""
        # 正常な検索
        tokyo_results = RegionMapper.search_prefecture("東京")
        self.assertEqual(len(tokyo_results), 1)
        self.assertEqual(tokyo_results[0]["area_id"], "JP13")
        self.assertEqual(tokyo_results[0]["prefecture_ja"], "東京都")
        
        # 英語名での検索
        osaka_results = RegionMapper.search_prefecture("osaka")
        self.assertEqual(len(osaka_results), 1)
        self.assertEqual(osaka_results[0]["area_id"], "JP27")
        
        # 存在しない名前での検索
        invalid_results = RegionMapper.search_prefecture("存在しない")
        self.assertEqual(len(invalid_results), 0)
        
        # 空文字での検索
        empty_results = RegionMapper.search_prefecture("")
        self.assertEqual(len(empty_results), 0)

    def test_list_all_prefectures(self):
        """全都道府県リスト機能のテスト"""
        all_prefectures = RegionMapper.list_all_prefectures()
        
        # 47都道府県すべてが含まれているかテスト
        self.assertEqual(len(all_prefectures), 47, "都道府県数が47ではありません")
        
        # 特定の都道府県が含まれているかテスト
        expected_prefectures = ["北海道", "東京都", "大阪府", "沖縄県"]
        for prefecture in expected_prefectures:
            self.assertIn(prefecture, all_prefectures,
                f"{prefecture}が都道府県リストに含まれていません")
        
        # 地域IDが正しく対応しているかテスト
        self.assertEqual(all_prefectures["東京都"], "JP13")
        self.assertEqual(all_prefectures["大阪府"], "JP27")
        self.assertEqual(all_prefectures["北海道"], "JP1")
        self.assertEqual(all_prefectures["沖縄県"], "JP47")

    def test_validation_function(self):
        """地域ID検証機能のテスト"""
        # 有効な地域ID
        valid_ids = [f"JP{i}" for i in range(1, 48)]
        for area_id in valid_ids:
            with self.subTest(area_id=area_id):
                self.assertTrue(RegionMapper.validate_area_id(area_id),
                    f"有効な地域ID {area_id} が無効と判定されました")
        
        # 無効な地域ID
        invalid_ids = ["JP0", "JP48", "JP99", "US13", "INVALID", "", "JP"]
        for area_id in invalid_ids:
            with self.subTest(area_id=area_id):
                self.assertFalse(RegionMapper.validate_area_id(area_id),
                    f"無効な地域ID {area_id} が有効と判定されました")

    def test_default_area_id(self):
        """デフォルト地域ID機能のテスト"""
        default_id = RegionMapper.get_default_area_id()
        self.assertEqual(default_id, "JP13", "デフォルト地域IDが東京(JP13)ではありません")
        self.assertTrue(RegionMapper.validate_area_id(default_id),
            "デフォルト地域IDが無効です")

    def test_case_sensitivity_and_variations(self):
        """大文字小文字の区別と表記バリエーションのテスト"""
        # 東京のバリエーション
        tokyo_variations = [
            "東京", "東京都", "Tokyo", "tokyo", "TOKYO", "ToKyO"
        ]
        for variation in tokyo_variations:
            with self.subTest(variation=variation):
                result = RegionMapper.get_area_id(variation)
                self.assertEqual(result, "JP13",
                    f"東京のバリエーション '{variation}' が正しくマッピングされませんでした")
        
        # 大阪のバリエーション
        osaka_variations = [
            "大阪", "大阪府", "Osaka", "osaka", "OSAKA", "OsAkA"
        ]
        for variation in osaka_variations:
            with self.subTest(variation=variation):
                result = RegionMapper.get_area_id(variation)
                self.assertEqual(result, "JP27",
                    f"大阪のバリエーション '{variation}' が正しくマッピングされませんでした")

    def test_edge_cases_and_special_characters(self):
        """エッジケースと特殊文字のテスト"""
        # strip()で除去される特殊文字（有効になる）
        strip_removable_cases = [
            "東京\r\n",    # 改行文字
            "東京\t",      # タブ文字
            "東京\u3000",  # 全角スペース（Pythonのstrip()で除去される）
            "東京\u00A0",  # ノーブレークスペース（Pythonのstrip()で除去される）
        ]
        
        # strip()で除去されない特殊文字（無効のまま）
        non_strip_cases = [
            "\u200B東京",  # ゼロ幅スペース
        ]
        
        # strip()で除去される文字のテスト
        for case in strip_removable_cases:
            with self.subTest(case=repr(case)):
                result = RegionMapper.get_area_id(case)
                self.assertEqual(result, "JP13",
                    f"strip()により除去される特殊文字を含む入力 {repr(case)} が正しく認識されませんでした")
        
        # strip()で除去されない文字のテスト
        for case in non_strip_cases:
            with self.subTest(case=repr(case)):
                result = RegionMapper.get_area_id(case)
                self.assertIsNone(result,
                    f"strip()で除去されない特殊文字を含む入力 {repr(case)} が誤って認識されました")

    def test_performance_with_large_input(self):
        """大量入力でのパフォーマンステスト"""
        # 1000回の検索で性能問題がないことを確認
        import time
        
        start_time = time.time()
        for _ in range(1000):
            RegionMapper.get_area_id("東京")
            RegionMapper.get_area_id("Osaka")
            RegionMapper.get_prefecture_name("JP13")
            RegionMapper.validate_area_id("JP27")
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0,
            f"1000回の検索に{execution_time:.2f}秒かかりました（1秒以内が期待値）")


if __name__ == '__main__':
    # テスト実行時の詳細出力
    unittest.main(verbosity=2)
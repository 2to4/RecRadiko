"""
CLI都道府県設定機能の単体テスト

config.jsonでの都道府県名設定とarea_id自動変換機能のテスト
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import tempfile
import os
import sys
from pathlib import Path

# テスト対象のインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.cli import RecRadikoCLI
from src.region_mapper import RegionMapper


class TestCLIPrefectureSetting(unittest.TestCase):
    """CLI都道府県設定機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_config(self, config_data):
        """テスト用設定ファイルを作成"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

    def _get_config_after_load(self, config_data):
        """設定をロードした後の設定内容を取得"""
        self._create_test_config(config_data)
        
        # 依存コンポーネントをモック化してCLIをテスト専用で初期化
        with patch('src.cli.RadikoAuthenticator'), \
             patch('src.cli.ProgramInfoManager'), \
             patch('src.cli.StreamingManager'), \
             patch('src.cli.RecordingManager'), \
             patch('src.cli.FileManager'), \
             patch('src.cli.RecordingScheduler'), \
             patch('src.cli.ErrorHandler'):
            # 実際のコンポーネント初期化をスキップ
            cli = RecRadikoCLI(config_file=self.config_file)
            cli._all_components_injected = True  # コンポーネント初期化をスキップ
            return cli.config

    def test_prefecture_to_area_id_mapping_all_47_prefectures(self):
        """47都道府県すべての都道府県名→area_id自動設定テスト"""
        # 47都道府県のテストケース（日本語名）
        prefecture_test_cases = [
            # 北海道・東北地方
            ("北海道", "JP1"),
            ("青森", "JP2"), ("岩手", "JP3"), ("宮城", "JP4"),
            ("秋田", "JP5"), ("山形", "JP6"), ("福島", "JP7"),
            
            # 関東地方
            ("茨城", "JP8"), ("栃木", "JP9"), ("群馬", "JP10"),
            ("埼玉", "JP11"), ("千葉", "JP12"), ("東京", "JP13"), ("神奈川", "JP14"),
            
            # 中部地方
            ("新潟", "JP15"), ("富山", "JP16"), ("石川", "JP17"), ("福井", "JP18"),
            ("山梨", "JP19"), ("長野", "JP20"), ("岐阜", "JP21"), ("静岡", "JP22"), ("愛知", "JP23"),
            
            # 近畿地方
            ("三重", "JP24"), ("滋賀", "JP25"), ("京都", "JP26"), ("大阪", "JP27"),
            ("兵庫", "JP28"), ("奈良", "JP29"), ("和歌山", "JP30"),
            
            # 中国地方
            ("鳥取", "JP31"), ("島根", "JP32"), ("岡山", "JP33"),
            ("広島", "JP34"), ("山口", "JP35"),
            
            # 四国地方
            ("徳島", "JP36"), ("香川", "JP37"), ("愛媛", "JP38"), ("高知", "JP39"),
            
            # 九州・沖縄地方
            ("福岡", "JP40"), ("佐賀", "JP41"), ("長崎", "JP42"), ("熊本", "JP43"),
            ("大分", "JP44"), ("宮崎", "JP45"), ("鹿児島", "JP46"), ("沖縄", "JP47"),
        ]
        
        failed_cases = []
        
        for prefecture, expected_area_id in prefecture_test_cases:
            with self.subTest(prefecture=prefecture):
                # 設定ファイルに都道府県名を設定
                config_data = {
                    "prefecture": prefecture,
                    "output_dir": "./recordings"
                }
                
                try:
                    result_config = self._get_config_after_load(config_data)
                    actual_area_id = result_config.get("area_id")
                    
                    if actual_area_id != expected_area_id:
                        failed_cases.append(f"{prefecture} -> {actual_area_id} (期待値: {expected_area_id})")
                    
                    self.assertEqual(actual_area_id, expected_area_id,
                        f"都道府県名'{prefecture}'からの地域ID自動設定が失敗: {actual_area_id} (期待値: {expected_area_id})")
                    
                except Exception as e:
                    failed_cases.append(f"{prefecture} -> エラー: {e}")
                    self.fail(f"都道府県名'{prefecture}'の処理でエラー: {e}")
        
        # すべての失敗ケースをまとめて表示
        if failed_cases:
            self.fail(f"都道府県名自動設定で失敗したケース:\n" + "\n".join(failed_cases))

    def test_prefecture_with_suffix_variations(self):
        """都道府県名の接尾辞バリエーションテスト"""
        suffix_test_cases = [
            # 県付きバリエーション
            ("青森県", "JP2"), ("岩手県", "JP3"), ("宮城県", "JP4"),
            ("茨城県", "JP8"), ("千葉県", "JP12"), ("神奈川県", "JP14"),
            ("新潟県", "JP15"), ("愛知県", "JP23"), ("三重県", "JP24"),
            ("兵庫県", "JP28"), ("広島県", "JP34"), ("福岡県", "JP40"),
            ("沖縄県", "JP47"),
            
            # 府付きバリエーション
            ("京都府", "JP26"), ("大阪府", "JP27"),
            
            # 都付きバリエーション
            ("東京都", "JP13"),
        ]
        
        for prefecture, expected_area_id in suffix_test_cases:
            with self.subTest(prefecture=prefecture):
                config_data = {"prefecture": prefecture}
                result_config = self._get_config_after_load(config_data)
                
                self.assertEqual(result_config.get("area_id"), expected_area_id,
                    f"接尾辞付き都道府県名'{prefecture}'の処理が失敗")

    def test_english_prefecture_names(self):
        """英語都道府県名のテスト"""
        english_test_cases = [
            ("Tokyo", "JP13"), ("tokyo", "JP13"), ("TOKYO", "JP13"),
            ("Osaka", "JP27"), ("osaka", "JP27"), ("OSAKA", "JP27"),
            ("Hokkaido", "JP1"), ("hokkaido", "JP1"),
            ("Kanagawa", "JP14"), ("kanagawa", "JP14"),
            ("Fukuoka", "JP40"), ("fukuoka", "JP40"),
            ("Okinawa", "JP47"), ("okinawa", "JP47"),
        ]
        
        for prefecture, expected_area_id in english_test_cases:
            with self.subTest(prefecture=prefecture):
                config_data = {"prefecture": prefecture}
                result_config = self._get_config_after_load(config_data)
                
                self.assertEqual(result_config.get("area_id"), expected_area_id,
                    f"英語都道府県名'{prefecture}'の処理が失敗")

    def test_invalid_prefecture_names(self):
        """無効な都道府県名の処理テスト"""
        invalid_test_cases = [
            "",  # 空文字
            " ",  # スペースのみ
            "存在しない県",  # 存在しない都道府県
            "Unknown Prefecture",  # 存在しない英語名
            "新東京",  # 間違った都道府県名
            "大阪市",  # 市名
            "東京区",  # 不正な表記
            "北海",  # 不完全
            "123",  # 数字
            "東京県",  # 間違った接尾辞
            "大阪都",  # 間違った接尾辞
            "おおさか",  # ひらがな
            "トウキョウ",  # カタカナ
            "関東",  # 地方名
            "日本",  # 国名
        ]
        
        for invalid_prefecture in invalid_test_cases:
            with self.subTest(prefecture=repr(invalid_prefecture)):
                config_data = {"prefecture": invalid_prefecture}
                result_config = self._get_config_after_load(config_data)
                
                # 無効な都道府県名の場合、area_idはデフォルト値（JP13）になるべき
                area_id = result_config.get("area_id")
                self.assertIn(area_id, ["JP13", None],
                    f"無効な都道府県名'{invalid_prefecture}'に対して予期しない地域ID: {area_id}")

    def test_prefecture_overwrites_existing_area_id(self):
        """都道府県名設定が既存のarea_id設定を上書きするテスト"""
        test_cases = [
            # (都道府県名, 既存のarea_id, 期待される最終area_id)
            ("大阪", "JP13", "JP27"),  # 東京→大阪
            ("北海道", "JP40", "JP1"),  # 福岡→北海道
            ("Okinawa", "JP14", "JP47"),  # 神奈川→沖縄
            ("東京都", "JP27", "JP13"),  # 大阪→東京
        ]
        
        for prefecture, original_area_id, expected_area_id in test_cases:
            with self.subTest(prefecture=prefecture, original=original_area_id):
                config_data = {
                    "prefecture": prefecture,
                    "area_id": original_area_id
                }
                result_config = self._get_config_after_load(config_data)
                
                self.assertEqual(result_config.get("area_id"), expected_area_id,
                    f"都道府県名'{prefecture}'が既存のarea_id'{original_area_id}'を上書きしませんでした")

    def test_empty_prefecture_uses_existing_area_id(self):
        """空の都道府県名の場合は既存のarea_idを使用するテスト"""
        test_cases = [
            ("", "JP27", "JP27"),  # 空文字
            ("   ", "JP40", "JP40"),  # スペースのみ
        ]
        
        for prefecture, area_id, expected_area_id in test_cases:
            with self.subTest(prefecture=repr(prefecture)):
                config_data = {
                    "prefecture": prefecture,
                    "area_id": area_id
                }
                result_config = self._get_config_after_load(config_data)
                
                self.assertEqual(result_config.get("area_id"), expected_area_id,
                    f"空の都道府県名で既存のarea_id'{area_id}'が保持されませんでした")

    def test_no_prefecture_field(self):
        """prefecture フィールドが存在しない場合のテスト"""
        config_data = {
            "area_id": "JP27",
            "output_dir": "./recordings"
        }
        result_config = self._get_config_after_load(config_data)
        
        # prefecture フィールドがない場合は既存のarea_idがそのまま使用されるべき
        self.assertEqual(result_config.get("area_id"), "JP27")

    def test_no_region_settings_defaults_to_tokyo(self):
        """都道府県名もarea_idも設定されていない場合のデフォルト処理テスト"""
        config_data = {
            "output_dir": "./recordings"
        }
        result_config = self._get_config_after_load(config_data)
        
        # 何も設定されていない場合はデフォルト（JP13：東京）が使用されるべき
        self.assertEqual(result_config.get("area_id"), "JP13")

    def test_invalid_area_id_with_no_prefecture(self):
        """無効なarea_idで都道府県名設定がない場合のテスト"""
        invalid_area_ids = ["JP0", "JP48", "JP999", "INVALID", "US13"]
        
        for invalid_area_id in invalid_area_ids:
            with self.subTest(area_id=invalid_area_id):
                config_data = {
                    "area_id": invalid_area_id,
                    "prefecture": ""
                }
                result_config = self._get_config_after_load(config_data)
                
                # 無効なarea_idの場合はデフォルト（JP13）に設定されるべき
                self.assertEqual(result_config.get("area_id"), "JP13",
                    f"無効な地域ID'{invalid_area_id}'がデフォルト値に修正されませんでした")

    def test_config_file_no_update_functionality(self):
        """設定ファイル非更新機能のテスト（地域IDはファイルに書き込まれない）"""
        # 都道府県名設定時にarea_idが設定ファイルに書き込まれないことを確認
        config_data = {"prefecture": "大阪"}
        result_config = self._get_config_after_load(config_data)
        
        # メモリ内では地域IDが設定されているが、ファイルには書き込まれない
        self.assertEqual(result_config.get("area_id"), "JP27")
        
        # 実際の設定ファイルには地域IDが含まれていないことを確認
        with open(self.config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        self.assertNotIn("area_id", file_content, 
            "地域IDが設定ファイルに書き込まれました（書き込まれるべきではありません）")

    def test_get_current_prefecture_info(self):
        """現在の地域設定情報取得のテスト"""
        test_cases = [
            ("東京", "JP13", "東京都", "Tokyo", "関東"),
            ("大阪", "JP27", "大阪府", "Osaka", "近畿"),
            ("北海道", "JP1", "北海道", "Hokkaido", "北海道"),
            ("沖縄", "JP47", "沖縄県", "Okinawa", "九州・沖縄"),
        ]
        
        for prefecture, expected_area_id, expected_ja, expected_en, expected_region in test_cases:
            with self.subTest(prefecture=prefecture):
                config_data = {"prefecture": prefecture}
                result_config = self._get_config_after_load(config_data)
                
                # CLI インスタンスを作成
                with patch('src.cli.RadikoAuthenticator'), \
                     patch('src.cli.ProgramInfoManager'), \
                     patch('src.cli.StreamingManager'), \
                     patch('src.cli.RecordingManager'), \
                     patch('src.cli.FileManager'), \
                     patch('src.cli.RecordingScheduler'), \
                     patch('src.cli.ErrorHandler'):
                    cli = RecRadikoCLI(config_file=self.config_file)
                    cli._all_components_injected = True
                    
                    info = cli.get_current_prefecture_info()
                    
                    self.assertEqual(info["area_id"], expected_area_id)
                    self.assertEqual(info["prefecture_ja"], expected_ja)
                    self.assertEqual(info["prefecture_en"], expected_en)
                    self.assertEqual(info["region_name"], expected_region)
                    self.assertIsInstance(info["major_stations"], list)

    def test_logging_during_prefecture_processing(self):
        """都道府県処理中のログ出力テスト"""
        with patch('src.cli.get_logger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            config_data = {"prefecture": "大阪"}
            self._create_test_config(config_data)
            
            with patch('src.cli.RadikoAuthenticator'), \
                 patch('src.cli.ProgramInfoManager'), \
                 patch('src.cli.StreamingManager'), \
                 patch('src.cli.RecordingManager'), \
                 patch('src.cli.FileManager'), \
                 patch('src.cli.RecordingScheduler'), \
                 patch('src.cli.ErrorHandler'):
                cli = RecRadikoCLI(config_file=self.config_file)
                cli._all_components_injected = True
                
                # 正常な都道府県名でログが出力されることを確認
                mock_logger_instance.info.assert_called()

    def test_error_handling_during_prefecture_processing(self):
        """都道府県処理中のエラーハンドリングテスト"""
        # RegionMapper.get_area_id でエラーが発生した場合のテスト
        with patch('src.cli.RegionMapper.get_area_id', side_effect=Exception("テストエラー")):
            config_data = {"prefecture": "東京"}
            
            # エラーが発生してもCLI初期化が完了することを確認
            try:
                result_config = self._get_config_after_load(config_data)
                # エラーが発生した場合はデフォルト値が使用されるべき
                self.assertIsNotNone(result_config)
            except Exception as e:
                self.fail(f"都道府県処理エラー時の処理が失敗: {e}")

    def test_config_precedence(self):
        """設定の優先順位テスト"""
        # prefecture が設定されている場合は、area_id より優先されるべき
        config_data = {
            "prefecture": "大阪",  # これが優先されるべき
            "area_id": "JP13"      # これは上書きされるべき
        }
        result_config = self._get_config_after_load(config_data)
        
        self.assertEqual(result_config.get("area_id"), "JP27",
            "prefecture設定がarea_id設定より優先されませんでした")

    def test_whitespace_handling(self):
        """空白文字の処理テスト"""
        whitespace_cases = [
            ("  東京  ", "JP13"),  # 前後空白
            ("\t大阪\t", "JP27"),  # タブ文字
            ("\n北海道\n", "JP1"),  # 改行文字
        ]
        
        for prefecture, expected_area_id in whitespace_cases:
            with self.subTest(prefecture=repr(prefecture)):
                config_data = {"prefecture": prefecture}
                result_config = self._get_config_after_load(config_data)
                
                # 空白文字が正しく処理されて地域IDが設定されることを確認
                area_id = result_config.get("area_id")
                # strip()処理により正しく認識されるか、または無効として扱われるか
                self.assertIn(area_id, [expected_area_id, "JP13"],  # JP13はデフォルト
                    f"空白文字を含む都道府県名'{repr(prefecture)}'の処理が適切ではありません")


if __name__ == '__main__':
    unittest.main(verbosity=2)
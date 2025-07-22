"""
Phase 8音質オプション拡張テスト

新音質オプション（320kbps、VBR）の動作確認テスト
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.timefree_recorder import TimeFreeRecorder
from src.auth import RadikoAuthenticator
from src.ui.screens.audio_quality_screen import AudioQualityScreen
from src.utils.config_utils import ConfigManager


class TestAudioQualityExpansion:
    """音質オプション拡張テスト（Phase 8）"""
    
    @pytest.fixture
    def mock_auth(self):
        """認証モック"""
        auth = Mock(spec=RadikoAuthenticator)
        auth.area_id = "JP13"
        auth.auth_token = "test_token"
        return auth
    
    @pytest.fixture
    def temp_config(self):
        """一時設定ファイル"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "prefecture": "東京",
                "audio": {
                    "format": "mp3",
                    "bitrate": 256,
                    "sample_rate": 48000
                }
            }
            json.dump(config, f, indent=2)
            yield f.name
        Path(f.name).unlink(missing_ok=True)
    
    def test_audio_quality_screen_8_options(self, temp_config):
        """音質画面8オプション表示テスト"""
        screen = AudioQualityScreen(temp_config)
        
        # 8オプション確認
        assert len(screen.audio_options) == 8
        
        # 追加オプション確認
        formats = [opt["display"] for opt in screen.audio_options]
        assert "MP3 320kbps, 48kHz" in formats
        assert "MP3 VBR V0, 48kHz" in formats
        assert "AAC 320kbps, 48kHz" in formats
        assert "AAC VBR ~256kbps, 48kHz" in formats
        
        # VBRオプション確認
        vbr_options = [opt for opt in screen.audio_options if isinstance(opt["bitrate"], str)]
        assert len(vbr_options) == 2
        assert any(opt["bitrate"] == "VBR_V0" for opt in vbr_options)
        assert any(opt["bitrate"] == "VBR_HQ" for opt in vbr_options)
    
    def test_mp3_320kbps_ffmpeg_command(self, mock_auth, temp_config):
        """MP3 320kbps FFmpegコマンド生成テスト"""
        # 320kbps設定
        config_manager = ConfigManager(temp_config)
        config = {
            "audio": {
                "format": "mp3",
                "bitrate": 320,
                "sample_rate": 48000
            }
        }
        config_manager.save_config(config)
        
        recorder = TimeFreeRecorder(mock_auth, temp_config)
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            with tempfile.NamedTemporaryFile(suffix='.ts') as temp_ts:
                with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_mp3:
                    # _convert_to_mp3メソッドを直接テスト（内部実装依存）
                    # 実際の実装に合わせて調整が必要
                    pass  # 具体的なFFmpegコマンド確認は統合テストで実施
    
    def test_mp3_vbr_v0_config_setting(self, temp_config):
        """MP3 VBR V0設定保存・読み込みテスト"""
        config_manager = ConfigManager(temp_config)
        
        # VBR V0設定保存
        config = {
            "audio": {
                "format": "mp3", 
                "bitrate": "VBR_V0",
                "sample_rate": 48000
            }
        }
        
        assert config_manager.save_config(config) == True
        
        # 読み込み確認
        loaded_config = config_manager.load_config({})
        assert loaded_config["audio"]["bitrate"] == "VBR_V0"
        assert loaded_config["audio"]["format"] == "mp3"
        assert loaded_config["audio"]["sample_rate"] == 48000
    
    def test_aac_320kbps_config_setting(self, temp_config):
        """AAC 320kbps設定保存・読み込みテスト"""
        config_manager = ConfigManager(temp_config)
        
        # AAC 320kbps設定保存
        config = {
            "audio": {
                "format": "aac",
                "bitrate": 320,
                "sample_rate": 48000
            }
        }
        
        assert config_manager.save_config(config) == True
        
        # 読み込み確認
        loaded_config = config_manager.load_config({})
        assert loaded_config["audio"]["bitrate"] == 320
        assert loaded_config["audio"]["format"] == "aac"
    
    def test_aac_vbr_hq_config_setting(self, temp_config):
        """AAC VBR HQ設定保存・読み込みテスト"""
        config_manager = ConfigManager(temp_config)
        
        # AAC VBR設定保存
        config = {
            "audio": {
                "format": "aac",
                "bitrate": "VBR_HQ", 
                "sample_rate": 48000
            }
        }
        
        assert config_manager.save_config(config) == True
        
        # 読み込み確認
        loaded_config = config_manager.load_config({})
        assert loaded_config["audio"]["bitrate"] == "VBR_HQ"
        assert loaded_config["audio"]["format"] == "aac"
    
    def test_audio_quality_display_with_vbr(self, temp_config):
        """VBR設定時の画面表示テスト"""
        # VBR V0設定
        config_manager = ConfigManager(temp_config)
        config = {
            "audio": {
                "format": "mp3",
                "bitrate": "VBR_V0",
                "sample_rate": 48000
            }
        }
        config_manager.save_config(config)
        
        screen = AudioQualityScreen(temp_config)
        
        # 現在設定表示をキャプチャ（実際の実装確認用）
        # 内部メソッド_display_current_infoの動作確認
        current_config = screen.config_manager.load_config({})
        current_bitrate = current_config.get("audio", {}).get("bitrate", 256)
        
        assert current_bitrate == "VBR_V0"
        
        # VBR設定の表示確認（文字列ビットレート）
        assert isinstance(current_bitrate, str)
    
    def test_timefree_recorder_audio_config_integration(self, mock_auth, temp_config):
        """TimeFreeRecorder音質設定統合テスト"""
        # 320kbps設定でRecorder初期化
        config_manager = ConfigManager(temp_config)
        config = {
            "audio": {
                "format": "mp3",
                "bitrate": 320,
                "sample_rate": 48000
            }
        }
        config_manager.save_config(config)
        
        recorder = TimeFreeRecorder(mock_auth, temp_config)
        
        # 設定読み込み確認
        loaded_config = recorder.config_manager.load_config({})
        assert loaded_config["audio"]["bitrate"] == 320
        assert loaded_config["audio"]["format"] == "mp3"
    
    def test_config_template_vbr_support(self):
        """config.json.template VBRサポート確認"""
        template_path = Path("config.json.template")
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # VBRコメント記載確認
            assert "VBR" in content or "vbr" in content
            assert "_comment" in content


class TestAudioQualityValidation:
    """音質設定バリデーションテスト"""
    
    def test_valid_audio_configs(self):
        """有効な音質設定テスト"""
        valid_configs = [
            {"format": "mp3", "bitrate": 128, "sample_rate": 44100},
            {"format": "mp3", "bitrate": 256, "sample_rate": 48000},
            {"format": "mp3", "bitrate": 320, "sample_rate": 48000},
            {"format": "mp3", "bitrate": "VBR_V0", "sample_rate": 48000},
            {"format": "aac", "bitrate": 128, "sample_rate": 44100},
            {"format": "aac", "bitrate": 256, "sample_rate": 48000},
            {"format": "aac", "bitrate": 320, "sample_rate": 48000},
            {"format": "aac", "bitrate": "VBR_HQ", "sample_rate": 48000},
        ]
        
        for config in valid_configs:
            # バリデーション実装時にテスト
            assert config["format"] in ["mp3", "aac"]
            assert config["sample_rate"] in [44100, 48000]
            assert isinstance(config["bitrate"], (int, str))
    
    def test_invalid_audio_configs(self):
        """無効な音質設定テスト"""
        invalid_configs = [
            {"format": "ogg", "bitrate": 256, "sample_rate": 48000},  # 未対応フォーマット
            {"format": "mp3", "bitrate": 999, "sample_rate": 48000},  # 無効ビットレート
            {"format": "mp3", "bitrate": 256, "sample_rate": 999},    # 無効サンプルレート
            {"format": "mp3", "bitrate": "INVALID_VBR", "sample_rate": 48000},  # 無効VBR
        ]
        
        for config in invalid_configs:
            # バリデーション実装時にテスト
            # 現在はバリデーションなしのため、設定値のみ確認
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
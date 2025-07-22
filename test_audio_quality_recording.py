#!/usr/bin/env python3
"""
Phase 8音質設定録音テストスクリプト

新しい音質オプション（320kbps、VBR）での実際の録音テストを実行し、
録音ファイルの再生可能性を確認します。
"""

import asyncio
import sys
import os
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.timefree_recorder import TimeFreeRecorder
from src.auth import RadikoAuthenticator
from src.program_info import Program
from src.utils.config_utils import ConfigManager


class AudioQualityRecordingTester:
    """音質設定録音テスター"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="audio_test_"))
        print(f"テスト録音ファイル保存先: {self.temp_dir}")
        
        # テスト用音質設定リスト
        self.audio_configs = [
            {
                "name": "MP3 320kbps",
                "format": "mp3",
                "bitrate": 320,
                "sample_rate": 48000,
                "expected_ext": ".mp3"
            },
            {
                "name": "MP3 VBR V0",
                "format": "mp3", 
                "bitrate": "VBR_V0",
                "sample_rate": 48000,
                "expected_ext": ".mp3"
            },
            {
                "name": "AAC 320kbps",
                "format": "aac",
                "bitrate": 320,
                "sample_rate": 48000,
                "expected_ext": ".aac"
            },
            {
                "name": "AAC VBR HQ",
                "format": "aac",
                "bitrate": "VBR_HQ", 
                "sample_rate": 48000,
                "expected_ext": ".aac"
            }
        ]
    
    def create_test_config(self, audio_config: Dict[str, Any]) -> str:
        """テスト用設定ファイル作成"""
        config_file = self.temp_dir / f"config_{audio_config['name'].replace(' ', '_').lower()}.json"
        
        config = {
            "prefecture": "東京",
            "audio": {
                "format": audio_config["format"],
                "bitrate": audio_config["bitrate"],
                "sample_rate": audio_config["sample_rate"]
            },
            "log_level": "INFO"
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return str(config_file)
    
    def create_test_program_info(self) -> Program:
        """テスト用番組情報作成（短時間録音用）"""
        # 現在時刻の5分前から30秒間の番組を作成（実際にはダミーデータ）
        now = datetime.now()
        start_time = now - timedelta(minutes=5)  # 5分前
        end_time = start_time + timedelta(seconds=30)  # 30秒間
        
        program_info = Program(
            id=f"test_{start_time.strftime('%Y%m%d%H%M')}",
            station_id="TBS",
            title="音質テスト録音",
            start_time=start_time,
            end_time=end_time,
            duration=1,  # 1分（30秒だと0分になるため）
            description="Phase 8音質設定テスト用録音",
            performers=["テストアーティスト"],
            genre="テスト"
        )
        
        return program_info
    
    async def test_audio_config(self, audio_config: Dict[str, Any]) -> Dict[str, Any]:
        """個別音質設定テスト実行"""
        print(f"\n🎵 {audio_config['name']} テスト開始...")
        
        result = {
            "config_name": audio_config['name'],
            "success": False,
            "file_path": None,
            "file_size": 0,
            "duration_seconds": 0,
            "codec_info": None,
            "playable": False,
            "error_message": None
        }
        
        try:
            # テスト設定ファイル作成
            config_file = self.create_test_config(audio_config)
            
            # 認証（実際の認証を使用）
            auth = RadikoAuthenticator()
            auth_info = auth.authenticate()  # 同期関数
            
            if not auth_info or not auth_info.auth_token:
                result["error_message"] = "認証失敗: トークン取得できず"
                return result
            
            # TimeFreeRecorder初期化
            recorder = TimeFreeRecorder(auth, config_file)
            
            # テスト番組情報作成
            program_info = self.create_test_program_info()
            
            # 録音ファイルパス設定
            output_filename = f"test_{audio_config['name'].replace(' ', '_').lower()}{audio_config['expected_ext']}"
            output_path = str(self.temp_dir / output_filename)
            
            print(f"録音開始: {output_path}")
            
            # 実際の録音実行（短時間テスト）
            recording_result = await recorder.record_program(program_info, output_path)
            
            if recording_result.success:
                result["success"] = True
                result["file_path"] = output_path
                result["file_size"] = recording_result.file_size_bytes
                result["duration_seconds"] = recording_result.recording_duration_seconds
                
                # ファイル存在確認
                if Path(output_path).exists():
                    # 音声コーデック情報取得
                    codec_info = await self.get_audio_codec_info(output_path)
                    result["codec_info"] = codec_info
                    
                    # 再生可能性テスト
                    playable = await self.test_playability(output_path)
                    result["playable"] = playable
                    
                    print(f"✅ 録音成功: {Path(output_path).name}")
                    print(f"   ファイルサイズ: {result['file_size']:,} bytes")
                    print(f"   録音時間: {result['duration_seconds']:.1f}秒")
                    print(f"   コーデック: {codec_info}")
                    print(f"   再生可能: {'✅' if playable else '❌'}")
                else:
                    result["error_message"] = "録音ファイルが作成されませんでした"
            else:
                result["error_message"] = f"録音失敗: {recording_result.error_messages}"
                
        except Exception as e:
            result["error_message"] = f"テスト実行エラー: {str(e)}"
            print(f"❌ エラー: {str(e)}")
            
        return result
    
    async def get_audio_codec_info(self, file_path: str) -> str:
        """音声コーデック情報取得"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json as json_lib
                probe_data = json_lib.loads(stdout.decode())
                
                audio_stream = None
                for stream in probe_data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                if audio_stream:
                    codec = audio_stream.get('codec_name', 'unknown')
                    bitrate = audio_stream.get('bit_rate', 'N/A')
                    sample_rate = audio_stream.get('sample_rate', 'N/A')
                    
                    if bitrate != 'N/A':
                        bitrate_kbps = int(bitrate) // 1000
                        return f"{codec.upper()} {bitrate_kbps}kbps {sample_rate}Hz"
                    else:
                        return f"{codec.upper()} VBR {sample_rate}Hz"
                        
            return "コーデック情報取得失敗"
            
        except Exception as e:
            return f"ffprobeエラー: {str(e)}"
    
    async def test_playability(self, file_path: str) -> bool:
        """ファイル再生可能性テスト"""
        try:
            # ffplayでファイルをテスト再生（1秒間のみ）
            cmd = [
                'ffplay',
                '-nodisp',  # 画面表示なし
                '-autoexit',  # 自動終了
                '-t', '1',  # 1秒間のみ
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # ffplayが正常終了すれば再生可能
            return process.returncode == 0
            
        except Exception as e:
            print(f"再生テストエラー: {str(e)}")
            return False
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """全音質設定テスト実行"""
        print("🎵 Phase 8音質設定録音テスト開始")
        print("=" * 60)
        
        for audio_config in self.audio_configs:
            result = await self.test_audio_config(audio_config)
            self.test_results.append(result)
            
            # 少し待つ
            await asyncio.sleep(2)
        
        return self.test_results
    
    def print_summary(self):
        """テスト結果サマリー表示"""
        print("\n" + "=" * 60)
        print("🎵 Phase 8音質設定録音テスト結果サマリー")
        print("=" * 60)
        
        success_count = 0
        playable_count = 0
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            playable = "✅" if result['playable'] else "❌"
            
            print(f"\n{status} {result['config_name']}")
            
            if result['success']:
                success_count += 1
                if result['playable']:
                    playable_count += 1
                    
                print(f"   📁 {Path(result['file_path']).name}")
                print(f"   📊 {result['file_size']:,} bytes, {result['duration_seconds']:.1f}s")
                print(f"   🎧 {result['codec_info']}")
                print(f"   ▶️  再生可能: {playable}")
            else:
                print(f"   ❌ {result['error_message']}")
        
        print(f"\n📊 テスト結果:")
        print(f"   録音成功: {success_count}/{len(self.test_results)}")
        print(f"   再生可能: {playable_count}/{len(self.test_results)}")
        print(f"   成功率: {success_count/len(self.test_results)*100:.1f}%")
        
        if success_count == len(self.test_results) and playable_count == len(self.test_results):
            print("\n🎉 全音質設定テスト成功！Phase 8音質拡張完了確認！")
        else:
            print(f"\n⚠️  一部テスト失敗。要確認。")
        
        print(f"\nテストファイル保存先: {self.temp_dir}")
    
    def cleanup(self):
        """テンプファイル削除"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"テンプファイル削除完了: {self.temp_dir}")
        except Exception as e:
            print(f"テンプファイル削除失敗: {e}")


async def main():
    """メイン関数"""
    tester = AudioQualityRecordingTester()
    
    try:
        # 全テスト実行
        results = await tester.run_all_tests()
        
        # 結果表示
        tester.print_summary()
        
        # テストファイルは残しておく（手動確認用）
        keep_files = input("\nテストファイルを保持しますか？ (y/n): ").lower() == 'y'
        if not keep_files:
            tester.cleanup()
            
    except KeyboardInterrupt:
        print("\n\nテスト中断")
        tester.cleanup()
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
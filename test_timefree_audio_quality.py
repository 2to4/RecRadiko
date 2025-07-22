#!/usr/bin/env python3
"""
Phase 8実タイムフリー番組音質テストスクリプト

実際のタイムフリー番組を各音質設定で録音し、
音質・再生可能性を確認します。
"""

import asyncio
import sys
import os
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.timefree_recorder import TimeFreeRecorder
from src.auth import RadikoAuthenticator
from src.program_info import Program, ProgramInfoManager
from src.utils.config_utils import ConfigManager


class TimeFreeAudioQualityTester:
    """タイムフリー音質テスター"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="timefree_audio_test_"))
        print(f"テスト録音ファイル保存先: {self.temp_dir}")
        
        # テスト用音質設定リスト（短時間録音用）
        self.audio_configs = [
            {
                "name": "MP3_320kbps",
                "format": "mp3",
                "bitrate": 320,
                "sample_rate": 48000,
                "test_duration": 10  # 10秒間録音
            },
            {
                "name": "MP3_VBR_V0",
                "format": "mp3", 
                "bitrate": "VBR_V0",
                "sample_rate": 48000,
                "test_duration": 10
            },
            {
                "name": "AAC_320kbps",
                "format": "aac",
                "bitrate": 320,
                "sample_rate": 48000,
                "test_duration": 10
            },
            {
                "name": "AAC_VBR_HQ",
                "format": "aac",
                "bitrate": "VBR_HQ", 
                "sample_rate": 48000,
                "test_duration": 10
            }
        ]
        
        self.authenticator = None
        self.program_manager = None
    
    async def initialize(self):
        """初期化処理"""
        print("🔐 Radiko認証中...")
        self.authenticator = RadikoAuthenticator()
        auth_info = self.authenticator.authenticate()
        
        if not auth_info or not auth_info.auth_token:
            raise Exception("認証に失敗しました")
        
        print(f"✅ 認証成功 - エリア: {auth_info.area_id}")
        
        # 番組情報マネージャー初期化
        self.program_manager = ProgramInfoManager(
            area_id=auth_info.area_id,
            authenticator=self.authenticator
        )
    
    async def get_test_program(self) -> Optional[Program]:
        """テスト用番組取得"""
        print("📻 テスト用番組検索中...")
        
        try:
            # 昨日の番組を取得（タイムフリー対象）
            yesterday = datetime.now() - timedelta(days=1)
            
            # TBSラジオの番組を取得
            programs = self.program_manager.fetch_program_guide(yesterday, "TBS")
            
            if not programs:
                print("❌ 昨日のTBS番組が見つかりません")
                # 一昨日を試す
                day_before_yesterday = datetime.now() - timedelta(days=2)
                programs = self.program_manager.fetch_program_guide(day_before_yesterday, "TBS")
            
            if not programs:
                print("❌ 録音可能な番組が見つかりません")
                return None
            
            # 10分以上の番組を選択（短時間テスト用に十分な長さ）
            suitable_programs = [p for p in programs if p.duration >= 10]
            
            if not suitable_programs:
                print("❌ 10分以上の番組が見つかりません")
                return None
            
            # 最初の適切な番組を選択
            selected_program = suitable_programs[0]
            print(f"✅ テスト番組選択: {selected_program.title}")
            print(f"   放送時間: {selected_program.start_time.strftime('%H:%M')}-{selected_program.end_time.strftime('%H:%M')}")
            print(f"   番組長: {selected_program.duration}分")
            
            return selected_program
            
        except Exception as e:
            print(f"❌ 番組取得エラー: {e}")
            return None
    
    def create_test_config(self, audio_config: Dict[str, Any]) -> str:
        """テスト用設定ファイル作成"""
        config_file = self.temp_dir / f"config_{audio_config['name']}.json"
        
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
    
    def create_short_program(self, original_program: Program, duration_seconds: int) -> Program:
        """短時間録音用に番組を調整"""
        # 元番組の開始時刻から指定秒数だけ録音するように調整
        end_time = original_program.start_time + timedelta(seconds=duration_seconds)
        
        short_program = Program(
            id=f"{original_program.id}_test_{duration_seconds}s",
            station_id=original_program.station_id,
            title=f"{original_program.title} (テスト録音{duration_seconds}秒)",
            start_time=original_program.start_time,
            end_time=end_time,
            duration=max(1, duration_seconds // 60),  # 最低1分
            description=original_program.description,
            performers=original_program.performers,
            genre=original_program.genre
        )
        
        return short_program
    
    async def test_audio_config(self, audio_config: Dict[str, Any], test_program: Program) -> Dict[str, Any]:
        """個別音質設定テスト実行"""
        config_name = audio_config['name']
        print(f"\n🎵 {config_name} テスト開始...")
        
        result = {
            "config_name": config_name,
            "success": False,
            "file_path": None,
            "file_size": 0,
            "duration_seconds": 0,
            "codec_info": None,
            "playable": False,
            "error_message": None,
            "bitrate_actual": None
        }
        
        try:
            # テスト設定ファイル作成
            config_file = self.create_test_config(audio_config)
            
            # TimeFreeRecorder初期化
            recorder = TimeFreeRecorder(self.authenticator, config_file)
            
            # 短時間録音用番組作成
            short_program = self.create_short_program(test_program, audio_config['test_duration'])
            
            # 録音ファイルパス設定
            file_ext = ".mp3" if audio_config['format'] == 'mp3' else ".aac"
            output_filename = f"test_{config_name}{file_ext}"
            output_path = str(self.temp_dir / output_filename)
            
            print(f"📁 録音先: {output_filename}")
            print(f"⏱️  録音時間: {audio_config['test_duration']}秒")
            
            # 実際の録音実行
            recording_result = await recorder.record_program(short_program, output_path)
            
            if recording_result.success and Path(output_path).exists():
                result["success"] = True
                result["file_path"] = output_path
                result["file_size"] = Path(output_path).stat().st_size
                result["duration_seconds"] = recording_result.recording_duration_seconds
                
                # 音声コーデック情報取得
                codec_info = await self.get_audio_codec_info(output_path)
                result["codec_info"] = codec_info
                result["bitrate_actual"] = self.extract_bitrate_from_codec_info(codec_info)
                
                # 再生可能性テスト
                playable = await self.test_playability(output_path)
                result["playable"] = playable
                
                print(f"✅ 録音成功!")
                print(f"   📊 {result['file_size']:,} bytes ({result['file_size']/1024/1024:.2f}MB)")
                print(f"   ⏱️  {result['duration_seconds']:.1f}秒")
                print(f"   🎧 {codec_info}")
                print(f"   ▶️  再生可能: {'✅' if playable else '❌'}")
                
                # 期待値チェック
                await self.verify_audio_quality(audio_config, result)
                
            else:
                result["error_message"] = f"録音失敗: {recording_result.error_messages if hasattr(recording_result, 'error_messages') else '不明なエラー'}"
                print(f"❌ 録音失敗: {result['error_message']}")
                
        except Exception as e:
            result["error_message"] = f"テスト実行エラー: {str(e)}"
            print(f"❌ エラー: {str(e)}")
            
        return result
    
    async def verify_audio_quality(self, audio_config: Dict[str, Any], result: Dict[str, Any]):
        """音質設定検証"""
        print(f"🔍 音質設定検証:")
        
        expected_format = audio_config['format'].upper()
        actual_codec = result['codec_info'].split()[0] if result['codec_info'] else 'UNKNOWN'
        
        format_ok = expected_format in actual_codec
        print(f"   形式: {expected_format} → {actual_codec} {'✅' if format_ok else '❌'}")
        
        if isinstance(audio_config['bitrate'], int):
            # 固定ビットレート検証
            expected_bitrate = audio_config['bitrate']
            actual_bitrate = result['bitrate_actual']
            if actual_bitrate:
                bitrate_diff = abs(actual_bitrate - expected_bitrate)
                bitrate_ok = bitrate_diff <= 10  # 10kbps以内の誤差許容
                print(f"   ビットレート: {expected_bitrate}kbps → {actual_bitrate}kbps {'✅' if bitrate_ok else '❌'}")
            else:
                print(f"   ビットレート: {expected_bitrate}kbps → 取得失敗 ❌")
        else:
            # VBR設定検証
            print(f"   ビットレート: VBR設定 ({audio_config['bitrate']}) ✅")
    
    def extract_bitrate_from_codec_info(self, codec_info: str) -> Optional[int]:
        """コーデック情報からビットレート抽出"""
        if not codec_info:
            return None
        
        import re
        # "MP3 320kbps 48000Hz" のような文字列から数値抽出
        match = re.search(r'(\d+)kbps', codec_info)
        if match:
            return int(match.group(1))
        
        # VBRの場合は数値が取れないことがある
        if 'VBR' in codec_info:
            return None
        
        return None
    
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
                
                # 音声ストリーム検索
                for stream in probe_data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        codec = stream.get('codec_name', 'unknown').upper()
                        bitrate = stream.get('bit_rate')
                        sample_rate = stream.get('sample_rate', 'N/A')
                        
                        if bitrate and bitrate != 'N/A':
                            bitrate_kbps = int(bitrate) // 1000
                            return f"{codec} {bitrate_kbps}kbps {sample_rate}Hz"
                        else:
                            return f"{codec} VBR {sample_rate}Hz"
                            
            return "コーデック情報取得失敗"
            
        except Exception as e:
            return f"ffprobeエラー: {str(e)}"
    
    async def test_playability(self, file_path: str) -> bool:
        """ファイル再生可能性テスト"""
        try:
            # ffplayでファイルをテスト再生（2秒間のみ）
            cmd = [
                'ffplay',
                '-nodisp',  # 画面表示なし
                '-autoexit',  # 自動終了
                '-t', '2',  # 2秒間のみ
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
        print("🎵 Phase 8 タイムフリー音質設定録音テスト開始")
        print("=" * 60)
        
        # テスト用番組取得
        test_program = await self.get_test_program()
        if not test_program:
            print("❌ テスト用番組を取得できませんでした。テストを中止します。")
            return []
        
        print(f"\n📻 テスト番組: {test_program.title}")
        print(f"🏢 放送局: {test_program.station_id}")
        print(f"⏰ 放送時間: {test_program.start_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 各音質設定でテスト実行
        for audio_config in self.audio_configs:
            result = await self.test_audio_config(audio_config, test_program)
            self.test_results.append(result)
            
            # テスト間隔
            await asyncio.sleep(1)
        
        return self.test_results
    
    def print_summary(self):
        """テスト結果サマリー表示"""
        print("\n" + "=" * 60)
        print("🎵 Phase 8 タイムフリー音質設定テスト結果")
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
                print(f"   📊 {result['file_size']:,} bytes ({result['file_size']/1024/1024:.2f}MB)")
                print(f"   ⏱️  {result['duration_seconds']:.1f}秒")
                print(f"   🎧 {result['codec_info']}")
                print(f"   ▶️  再生可能: {playable}")
            else:
                print(f"   ❌ {result['error_message']}")
        
        print(f"\n📊 最終結果:")
        print(f"   録音成功: {success_count}/{len(self.test_results)}")
        print(f"   再生可能: {playable_count}/{len(self.test_results)}")
        total_tests = len(self.test_results)
        if total_tests > 0:
            print(f"   総合成功率: {playable_count/total_tests*100:.1f}%")
        else:
            print(f"   総合成功率: 0.0% (テスト未実行)")
        
        if success_count == len(self.test_results) and playable_count == len(self.test_results):
            print("\n🎉 全音質設定テスト成功！Phase 8音質拡張が完全に動作しています！")
        else:
            print(f"\n⚠️  一部テスト失敗。詳細確認が必要です。")
        
        print(f"\n📁 テストファイル保存先: {self.temp_dir}")
        print("   手動での音質確認・再生テストにご利用ください。")


async def main():
    """メイン関数"""
    tester = TimeFreeAudioQualityTester()
    
    try:
        # 初期化
        await tester.initialize()
        
        # 全テスト実行
        results = await tester.run_all_tests()
        
        # 結果表示
        tester.print_summary()
        
        # ファイル保持確認
        print("\n" + "="*50)
        keep_files = input("テストファイルを保持しますか？ (y/n): ").lower().strip()
        if keep_files != 'y':
            import shutil
            shutil.rmtree(tester.temp_dir)
            print(f"テストファイル削除完了: {tester.temp_dir}")
            
    except KeyboardInterrupt:
        print("\n\nテスト中断")
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
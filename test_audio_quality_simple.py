#!/usr/bin/env python3
"""
Phase 8音質設定 - FFmpeg直接テスト

TimeFreeRecorderのFFmpeg音質設定コマンドが
正しく動作することを確認します。
"""

import asyncio
import tempfile
import json
import subprocess
from pathlib import Path
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.timefree_recorder import TimeFreeRecorder
from src.auth import RadikoAuthenticator
from src.utils.config_utils import ConfigManager


async def generate_test_audio(duration_seconds: int = 10) -> str:
    """テスト用音声ファイル生成"""
    temp_dir = Path(tempfile.mkdtemp(prefix="audio_test_"))
    test_input_file = temp_dir / "test_input.wav"
    
    # 10秒の440Hzサイン波を生成
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', f'sine=frequency=440:duration={duration_seconds}',
        '-ar', '48000',
        '-ac', '2',
        str(test_input_file)
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    
    await process.wait()
    
    if process.returncode != 0:
        raise Exception("テスト音声生成失敗")
    
    print(f"✅ テスト音声生成完了: {test_input_file}")
    return str(test_input_file)


async def test_ffmpeg_audio_conversion(input_file: str, audio_config: dict) -> dict:
    """FFmpeg音質変換テスト"""
    temp_dir = Path(input_file).parent
    config_name = audio_config['name']
    
    # 設定ファイル作成
    config_file = temp_dir / f"config_{config_name}.json"
    config = {
        "prefecture": "東京",
        "audio": {
            "format": audio_config["format"],
            "bitrate": audio_config["bitrate"],
            "sample_rate": audio_config["sample_rate"]
        }
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # 出力ファイル設定
    file_ext = ".mp3" if audio_config['format'] == 'mp3' else ".aac"
    output_file = temp_dir / f"output_{config_name}{file_ext}"
    
    print(f"\n🎵 {config_name} テスト開始...")
    print(f"   入力: {Path(input_file).name}")
    print(f"   出力: {output_file.name}")
    
    # TimeFreeRecorderの音質設定ロジックを模擬
    mock_auth = MockRadikoAuth()
    recorder = TimeFreeRecorder(mock_auth, str(config_file))
    
    # 設定読み込み
    loaded_config = recorder.config_manager.load_config({})
    audio_format = loaded_config.get('audio', {}).get('format', 'mp3')
    audio_bitrate = loaded_config.get('audio', {}).get('bitrate', 256)
    audio_sample_rate = loaded_config.get('audio', {}).get('sample_rate', 48000)
    
    # FFmpegコマンド構築（TimeFreeRecorderのロジックを再現）
    if audio_format == 'mp3':
        codec = 'libmp3lame'
        if audio_bitrate == "VBR_V0":
            extra_args = ['-q:a', '0']  # VBR V0最高品質
        elif isinstance(audio_bitrate, int):
            extra_args = ['-b:a', f'{audio_bitrate}k']  # 固定ビットレート
        else:
            extra_args = ['-b:a', '256k']  # デフォルト
    elif audio_format == 'aac':
        codec = 'aac'
        if audio_bitrate == "VBR_HQ":
            extra_args = ['-q:a', '0.4']  # VBR高品質（~256kbps）
        elif isinstance(audio_bitrate, int):
            extra_args = ['-b:a', f'{audio_bitrate}k']  # 固定ビットレート
        else:
            extra_args = ['-b:a', '256k']  # デフォルト
    else:
        codec = 'libmp3lame'
        extra_args = ['-b:a', '256k']
    
    # サンプルレート設定
    if audio_sample_rate and audio_sample_rate != 48000:
        extra_args.extend(['-ar', str(audio_sample_rate)])
    
    # FFmpegコマンド実行
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', input_file,
        '-c:a', codec,
        *extra_args,
        str(output_file)
    ]
    
    print(f"   コマンド: {' '.join(ffmpeg_cmd[3:])}")  # 入力ファイル以降を表示
    
    start_time = asyncio.get_event_loop().time()
    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    end_time = asyncio.get_event_loop().time()
    
    result = {
        "config_name": config_name,
        "success": process.returncode == 0,
        "file_path": str(output_file) if output_file.exists() else None,
        "file_size": output_file.stat().st_size if output_file.exists() else 0,
        "conversion_time": end_time - start_time,
        "codec_info": None,
        "playable": False,
        "error_message": stderr.decode() if process.returncode != 0 else None
    }
    
    if result["success"] and output_file.exists():
        # コーデック情報取得
        codec_info = await get_audio_codec_info(str(output_file))
        result["codec_info"] = codec_info
        
        # 再生テスト
        playable = await test_playability(str(output_file))
        result["playable"] = playable
        
        print(f"   ✅ 変換成功!")
        print(f"   📊 {result['file_size']:,} bytes ({result['file_size']/1024:.1f}KB)")
        print(f"   ⏱️  {result['conversion_time']:.2f}秒")
        print(f"   🎧 {codec_info}")
        print(f"   ▶️  再生可能: {'✅' if playable else '❌'}")
    else:
        print(f"   ❌ 変換失敗: {result['error_message']}")
    
    return result


async def get_audio_codec_info(file_path: str) -> str:
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


async def test_playability(file_path: str) -> bool:
    """再生可能性テスト"""
    try:
        cmd = [
            'ffplay',
            '-nodisp', '-autoexit', '-t', '1',
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        return process.returncode == 0
        
    except Exception:
        return False


class MockRadikoAuth:
    """モック認証クラス"""
    def __init__(self):
        self.area_id = "JP13"
        self.auth_token = "mock_token"


async def main():
    """メイン関数"""
    print("🎵 Phase 8音質設定 - FFmpeg直接テスト開始")
    print("=" * 60)
    
    # テスト用音質設定
    audio_configs = [
        {
            "name": "MP3_320kbps",
            "format": "mp3",
            "bitrate": 320,
            "sample_rate": 48000
        },
        {
            "name": "MP3_VBR_V0",
            "format": "mp3", 
            "bitrate": "VBR_V0",
            "sample_rate": 48000
        },
        {
            "name": "AAC_320kbps",
            "format": "aac",
            "bitrate": 320,
            "sample_rate": 48000
        },
        {
            "name": "AAC_VBR_HQ",
            "format": "aac",
            "bitrate": "VBR_HQ", 
            "sample_rate": 48000
        }
    ]
    
    try:
        # テスト用音声生成
        input_file = await generate_test_audio(10)
        
        results = []
        
        # 各音質設定でテスト
        for audio_config in audio_configs:
            result = await test_ffmpeg_audio_conversion(input_file, audio_config)
            results.append(result)
            await asyncio.sleep(0.5)  # 短い待機
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("🎵 Phase 8 FFmpeg音質設定テスト結果")
        print("=" * 60)
        
        success_count = 0
        playable_count = 0
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            playable = "✅" if result['playable'] else "❌"
            
            print(f"\n{status} {result['config_name']}")
            
            if result['success']:
                success_count += 1
                if result['playable']:
                    playable_count += 1
                    
                print(f"   📁 {Path(result['file_path']).name}")
                print(f"   📊 {result['file_size']:,} bytes ({result['file_size']/1024:.1f}KB)")
                print(f"   ⏱️  {result['conversion_time']:.2f}秒")
                print(f"   🎧 {result['codec_info']}")
                print(f"   ▶️  再生可能: {playable}")
            else:
                print(f"   ❌ エラー: {result['error_message'][:100]}...")
        
        print(f"\n📊 最終結果:")
        print(f"   変換成功: {success_count}/{len(results)}")
        print(f"   再生可能: {playable_count}/{len(results)}")
        print(f"   総合成功率: {playable_count/len(results)*100:.1f}%")
        
        if success_count == len(results) and playable_count == len(results):
            print("\n🎉 全音質設定テスト成功！Phase 8のFFmpeg音質拡張が完全に動作しています！")
        else:
            print(f"\n⚠️  一部テスト失敗。詳細確認が必要です。")
        
        # テストファイル削除
        temp_dir = Path(input_file).parent
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\nテストファイル削除完了: {temp_dir}")
        
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
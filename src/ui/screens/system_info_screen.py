"""
System Information Screen for RecRadiko

Provides system status information, recording statistics, and diagnostics
with keyboard navigation interface.
"""

import json
import os
import sys
import subprocess
import shutil
import platform
import psutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.utils.base import LoggerMixin


class SystemChecker(LoggerMixin):
    """System status and requirements checker"""
    
    def __init__(self, config_dir: str = "~/.recradiko"):
        super().__init__()
        self.config_dir = Path(config_dir).expanduser()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "authentication": self.check_authentication_status(),
            "api_connection": self.check_api_connection(),
            "ffmpeg": self.check_ffmpeg_availability(),
            "python_version": self.get_python_version(),
            "dependencies": self.check_dependencies(),
            "disk_space": self.get_disk_space_info(),
            "memory": self.get_memory_info()
        }
    
    def check_authentication_status(self) -> Dict[str, Any]:
        """Check authentication status"""
        try:
            # Check for auth token file or config
            auth_file = self.config_dir / "auth_token"
            config_file = self.config_dir / "config.json"
            
            if auth_file.exists():
                # Check token age
                token_age = time.time() - auth_file.stat().st_mtime
                if token_age < 3600:  # 1 hour
                    return {
                        "status": "active",
                        "message": "認証済み",
                        "expires_in": int(3600 - token_age)
                    }
                else:
                    return {
                        "status": "expired",
                        "message": "認証期限切れ",
                        "expires_in": 0
                    }
            elif config_file.exists():
                return {
                    "status": "configured",
                    "message": "設定済み（認証が必要）",
                    "expires_in": 0
                }
            else:
                return {
                    "status": "not_configured",
                    "message": "未設定",
                    "expires_in": 0
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"認証状態確認エラー: {e}",
                "expires_in": 0
            }
    
    def check_api_connection(self) -> Dict[str, Any]:
        """Check API connection status"""
        try:
            import requests
            start_time = time.time()
            
            # Test basic connectivity to Radiko
            response = requests.get("https://radiko.jp", timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "message": "API接続正常",
                    "response_time": round(response_time, 2)
                }
            else:
                return {
                    "status": "error",
                    "message": f"API接続エラー (HTTP {response.status_code})",
                    "response_time": round(response_time, 2)
                }
        except ImportError:
            return {
                "status": "error",
                "message": "requestsライブラリが見つかりません",
                "response_time": 0
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"接続テストエラー: {e}",
                "response_time": 0
            }
    
    def check_ffmpeg_availability(self) -> Dict[str, Any]:
        """Check FFmpeg availability"""
        try:
            # Try to find ffmpeg
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                return {
                    "available": False,
                    "version": None,
                    "path": None,
                    "message": "FFmpegが見つかりません"
                }
            
            # Get version info
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse version from output
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                version = version_match.group(1) if version_match else "Unknown"
                
                return {
                    "available": True,
                    "version": version,
                    "path": ffmpeg_path,
                    "message": f"FFmpeg {version} 利用可能"
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "path": ffmpeg_path,
                    "message": "FFmpegの実行に失敗しました"
                }
        except Exception as e:
            return {
                "available": False,
                "version": None,
                "path": None,
                "message": f"FFmpegチェックエラー: {e}"
            }
    
    def get_python_version(self) -> str:
        """Get Python version information"""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def get_python_info(self) -> Dict[str, Any]:
        """Get detailed Python information"""
        return {
            "version": self.get_python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "architecture": platform.architecture()[0]
        }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check Python dependencies"""
        required_deps = [
            "requests",
            "psutil",
            "pathlib",
            "datetime"
        ]
        
        optional_deps = [
            "m3u8",
            "cryptography",
            "readline"
        ]
        
        installed = []
        missing = []
        details = {}
        
        for dep in required_deps + optional_deps:
            try:
                __import__(dep)
                installed.append(dep)
                details[dep] = {"status": "installed", "required": dep in required_deps}
            except ImportError:
                missing.append(dep)
                details[dep] = {"status": "missing", "required": dep in required_deps}
        
        return {
            "installed": installed,
            "missing": missing,
            "details": details
        }
    
    def get_disk_space_info(self) -> Dict[str, Any]:
        """Get disk space information"""
        try:
            disk_usage = psutil.disk_usage(str(self.config_dir.parent))
            return {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": round((disk_usage.used / disk_usage.total) * 100, 1)
            }
        except Exception as e:
            return {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent": 0,
                "error": str(e)
            }
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": round(memory.percent, 1)
            }
        except Exception as e:
            return {
                "total": 0,
                "available": 0,
                "used": 0,
                "percent": 0,
                "error": str(e)
            }
    
    def check_system_requirements(self) -> Dict[str, Any]:
        """Check system requirements"""
        requirements = {
            "python": {
                "required": "3.8+",
                "current": self.get_python_version(),
                "satisfied": sys.version_info >= (3, 8)
            },
            "disk_space": {
                "required": "1GB",
                "required_bytes": 1024 * 1024 * 1024,  # 1GB
                "satisfied": False
            },
            "memory": {
                "required": "512MB",
                "required_bytes": 512 * 1024 * 1024,  # 512MB
                "satisfied": False
            },
            "dependencies": {
                "required": ["requests", "psutil"],
                "satisfied": False
            }
        }
        
        # Check disk space
        disk_info = self.get_disk_space_info()
        requirements["disk_space"]["available"] = disk_info["free"]
        requirements["disk_space"]["satisfied"] = disk_info["free"] > requirements["disk_space"]["required_bytes"]
        
        # Check memory
        memory_info = self.get_memory_info()
        requirements["memory"]["available"] = memory_info["available"]
        requirements["memory"]["satisfied"] = memory_info["available"] > requirements["memory"]["required_bytes"]
        
        # Check dependencies
        deps_info = self.check_dependencies()
        missing_required = [dep for dep in requirements["dependencies"]["required"] if dep in deps_info["missing"]]
        requirements["dependencies"]["satisfied"] = len(missing_required) == 0
        requirements["dependencies"]["missing"] = missing_required
        
        return requirements


class RecordingStatsManager(LoggerMixin):
    """Recording statistics manager"""
    
    def __init__(self, config_dir: str = "~/.recradiko"):
        super().__init__()
        self.config_dir = Path(config_dir).expanduser()
        self.recordings_dir = self.config_dir / "recordings"
    
    def get_recording_statistics(self) -> Dict[str, Any]:
        """Get comprehensive recording statistics"""
        try:
            if not self.recordings_dir.exists():
                return {
                    "total_recordings": 0,
                    "total_size": 0,
                    "total_duration": 0,
                    "average_size": 0,
                    "success_rate": 0,
                    "recent_recordings": []
                }
            
            # Get all recording files
            recording_files = list(self.recordings_dir.glob("*.mp3")) + \
                             list(self.recordings_dir.glob("*.aac")) + \
                             list(self.recordings_dir.glob("*.m4a"))
            
            if not recording_files:
                return {
                    "total_recordings": 0,
                    "total_size": 0,
                    "total_duration": 0,
                    "average_size": 0,
                    "success_rate": 0,
                    "recent_recordings": []
                }
            
            # Calculate statistics
            total_recordings = len(recording_files)
            total_size = sum(f.stat().st_size for f in recording_files)
            average_size = total_size / total_recordings if total_recordings > 0 else 0
            
            # Get recent recordings
            recent_recordings = self.get_recent_recordings(10)
            
            # Calculate success rate (assume all existing files are successful)
            success_rate = 100.0
            
            return {
                "total_recordings": total_recordings,
                "total_size": total_size,
                "total_duration": 0,  # Would need audio analysis for actual duration
                "average_size": average_size,
                "success_rate": success_rate,
                "recent_recordings": recent_recordings
            }
        except Exception as e:
            self.logger.error(f"Error getting recording statistics: {e}")
            return {
                "total_recordings": 0,
                "total_size": 0,
                "total_duration": 0,
                "average_size": 0,
                "success_rate": 0,
                "recent_recordings": []
            }
    
    def get_recording_count(self) -> int:
        """Get total number of recordings"""
        try:
            if not self.recordings_dir.exists():
                return 0
            
            recording_files = list(self.recordings_dir.glob("*.mp3")) + \
                             list(self.recordings_dir.glob("*.aac")) + \
                             list(self.recordings_dir.glob("*.m4a"))
            
            return len(recording_files)
        except Exception as e:
            self.logger.error(f"Error getting recording count: {e}")
            return 0
    
    def get_total_recording_size(self) -> int:
        """Get total size of all recordings"""
        try:
            if not self.recordings_dir.exists():
                return 0
            
            recording_files = list(self.recordings_dir.glob("*.mp3")) + \
                             list(self.recordings_dir.glob("*.aac")) + \
                             list(self.recordings_dir.glob("*.m4a"))
            
            return sum(f.stat().st_size for f in recording_files)
        except Exception as e:
            self.logger.error(f"Error getting total recording size: {e}")
            return 0
    
    def get_recent_recordings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent recordings list"""
        try:
            if not self.recordings_dir.exists():
                return []
            
            recording_files = list(self.recordings_dir.glob("*.mp3")) + \
                             list(self.recordings_dir.glob("*.aac")) + \
                             list(self.recordings_dir.glob("*.m4a"))
            
            # Sort by modification time (newest first)
            recording_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            recent = []
            for file in recording_files[:limit]:
                stat = file.stat()
                recent.append({
                    "filename": file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return recent
        except Exception as e:
            self.logger.error(f"Error getting recent recordings: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                "used": memory.used,
                "total": memory.total,
                "percent": round(memory.percent, 1)
            }
            
            # Disk usage
            disk_usage = psutil.disk_usage(str(self.config_dir.parent))
            disk_info = {
                "used": disk_usage.used,
                "total": disk_usage.total,
                "percent": round((disk_usage.used / disk_usage.total) * 100, 1)
            }
            
            # Network status (simplified)
            network_status = {
                "connected": True,  # Simplified check
                "interface": "Unknown"
            }
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_usage,
                "disk_usage": disk_info,
                "network_status": network_status
            }
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {
                "cpu_usage": 0,
                "memory_usage": {"used": 0, "total": 0, "percent": 0},
                "disk_usage": {"used": 0, "total": 0, "percent": 0},
                "network_status": {"connected": False, "interface": "Unknown"}
            }


class LogManager(LoggerMixin):
    """Log file manager"""
    
    def __init__(self, config_dir: str = "~/.recradiko"):
        super().__init__()
        self.config_dir = Path(config_dir).expanduser()
        self.logs_dir = self.config_dir / "logs"
    
    def get_log_info(self) -> Dict[str, Any]:
        """Get log file information"""
        try:
            log_files = self.find_log_files()
            
            if not log_files:
                return {
                    "log_files": [],
                    "total_size": 0,
                    "oldest_entry": None,
                    "newest_entry": None
                }
            
            total_size = sum(info["size"] for info in log_files)
            
            # Get oldest and newest entries
            oldest_entry = None
            newest_entry = None
            
            for log_file_info in log_files:
                try:
                    with open(log_file_info["path"], 'r') as f:
                        lines = f.readlines()
                        if lines:
                            first_line = lines[0].strip()
                            last_line = lines[-1].strip()
                            
                            if not oldest_entry:
                                oldest_entry = first_line
                            if not newest_entry:
                                newest_entry = last_line
                except Exception:
                    continue
            
            return {
                "log_files": log_files,
                "total_size": total_size,
                "oldest_entry": oldest_entry,
                "newest_entry": newest_entry
            }
        except Exception as e:
            self.logger.error(f"Error getting log info: {e}")
            return {
                "log_files": [],
                "total_size": 0,
                "oldest_entry": None,
                "newest_entry": None
            }
    
    def find_log_files(self) -> List[Dict[str, Any]]:
        """Find log files"""
        try:
            log_files = []
            
            if not self.logs_dir.exists():
                return log_files
            
            for log_file in self.logs_dir.glob("*.log"):
                try:
                    stat = log_file.stat()
                    log_files.append({
                        "path": str(log_file),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    self.logger.warning(f"Error reading log file {log_file}: {e}")
                    continue
            
            return log_files
        except Exception as e:
            self.logger.error(f"Error finding log files: {e}")
            return []
    
    def get_recent_log_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        try:
            log_files = self.find_log_files()
            if not log_files:
                return []
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda f: f["modified"], reverse=True)
            
            entries = []
            for log_file_info in log_files:
                try:
                    with open(log_file_info["path"], 'r') as f:
                        lines = f.readlines()
                        for line in reversed(lines):  # Newest first
                            if len(entries) >= limit:
                                break
                            
                            entry = self._parse_log_entry(line.strip())
                            if entry:
                                entries.append(entry)
                        
                        if len(entries) >= limit:
                            break
                except Exception as e:
                    self.logger.warning(f"Error reading log file {log_file_info['path']}: {e}")
                    continue
            
            return entries
        except Exception as e:
            self.logger.error(f"Error getting recent log entries: {e}")
            return []
    
    def get_log_entries_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get log entries by level"""
        try:
            all_entries = self.get_recent_log_entries(1000)  # Get more entries for filtering
            return [entry for entry in all_entries if entry["level"] == level]
        except Exception as e:
            self.logger.error(f"Error getting log entries by level: {e}")
            return []
    
    def get_total_log_size(self) -> int:
        """Get total size of all log files"""
        try:
            log_files = self.find_log_files()
            return sum(info["size"] for info in log_files)
        except Exception as e:
            self.logger.error(f"Error getting total log size: {e}")
            return 0
    
    def _parse_log_entry(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse log entry from line"""
        try:
            # Expected format: "2025-07-15 10:00:00 - INFO - Message"
            parts = line.split(" - ", 2)
            if len(parts) >= 3:
                timestamp = parts[0]
                level = parts[1]
                message = parts[2]
                
                return {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message
                }
        except Exception:
            pass
        
        return None


class SystemInfoScreen(ScreenBase):
    """System information screen with keyboard navigation"""
    
    def __init__(self, config_dir: str = "~/.recradiko"):
        super().__init__()
        self.set_title("システム情報")
        self.config_dir = config_dir
        self.system_checker = SystemChecker(config_dir)
        self.stats_manager = RecordingStatsManager(config_dir)
        self.log_manager = LogManager(config_dir)
        self.ui_service = UIService()
        
        self.menu_options = [
            "システム状況を表示",
            "録音統計を表示",
            "パフォーマンス情報を表示",
            "ログファイルを表示",
            "依存関係を確認",
            "システム要件を確認",
            "メインメニューに戻る"
        ]
    
    def display_content(self) -> None:
        """Display system info menu content"""
        print("\nRecRadiko システム情報")
        print("=" * 40)
        print("\n以下の情報を表示できます:\n")
        
        self.ui_service.set_menu_items(self.menu_options)
        self.ui_service.display_menu_with_highlight()
    
    def run_system_info_workflow(self) -> bool:
        """Run system info workflow"""
        try:
            while True:
                self.display_content()
                
                # Get user selection
                selected_option = self.ui_service.get_user_selection()
                if selected_option is None:
                    break
                
                # Handle selection
                if selected_option == "システム状況を表示":
                    self.show_system_status()
                elif selected_option == "録音統計を表示":
                    self.show_recording_statistics()
                elif selected_option == "パフォーマンス情報を表示":
                    self.show_performance_metrics()
                elif selected_option == "ログファイルを表示":
                    self.show_log_file()
                elif selected_option == "依存関係を確認":
                    self.show_dependencies()
                elif selected_option == "システム要件を確認":
                    self.show_system_requirements()
                elif selected_option == "メインメニューに戻る":
                    break
                else:
                    break
            
            return True
        except Exception as e:
            self.logger.error(f"System info workflow error: {e}")
            return False
    
    def show_system_status(self) -> None:
        """Show detailed system status"""
        print("\n" + "=" * 50)
        print("システム状況")
        print("=" * 50)
        
        try:
            status = self.system_checker.get_system_status()
            
            # Authentication status
            auth = status["authentication"]
            print(f"\n■ 認証状況")
            print(f"  状態: {auth['message']}")
            if auth['expires_in'] > 0:
                print(f"  有効期限: {auth['expires_in']}秒")
            
            # API connection
            api = status["api_connection"]
            print(f"\n■ API接続")
            print(f"  状態: {api['message']}")
            if api['response_time'] > 0:
                print(f"  応答時間: {api['response_time']}秒")
            
            # FFmpeg
            ffmpeg = status["ffmpeg"]
            print(f"\n■ FFmpeg")
            if ffmpeg['available']:
                print(f"  状態: ✓ 利用可能 ({ffmpeg['version']})")
                print(f"  パス: {ffmpeg['path']}")
            else:
                print(f"  状態: ✗ 利用不可")
                print(f"  メッセージ: {ffmpeg['message']}")
            
            # Python version
            python_version = status["python_version"]
            print(f"\n■ Python")
            print(f"  バージョン: {python_version}")
            
            # Dependencies
            deps = status["dependencies"]
            print(f"\n■ 依存関係")
            print(f"  インストール済み: {len(deps['installed'])}個")
            print(f"  不足: {len(deps['missing'])}個")
            
            # System resources
            disk = status["disk_space"]
            memory = status["memory"]
            print(f"\n■ システムリソース")
            print(f"  ディスク使用量: {disk['percent']}%")
            print(f"  メモリ使用量: {memory['percent']}%")
            
        except Exception as e:
            self.ui_service.display_error(f"システム状況の取得に失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def show_recording_statistics(self) -> None:
        """Show detailed recording statistics"""
        print("\n" + "=" * 50)
        print("録音統計")
        print("=" * 50)
        
        try:
            stats = self.stats_manager.get_recording_statistics()
            
            print(f"\n■ 録音統計")
            print(f"  総録音回数: {stats['total_recordings']}回")
            print(f"  総サイズ: {self._format_size(stats['total_size'])}")
            print(f"  平均サイズ: {self._format_size(stats['average_size'])}")
            print(f"  成功率: {stats['success_rate']:.1f}%")
            
            # Recent recordings
            recent = stats['recent_recordings']
            if recent:
                print(f"\n■ 最近の録音 (最新{len(recent)}件)")
                for i, recording in enumerate(recent, 1):
                    print(f"  {i}. {recording['filename']}")
                    print(f"     サイズ: {self._format_size(recording['size'])}")
                    print(f"     日時: {recording['modified']}")
            else:
                print(f"\n■ 最近の録音")
                print("  録音ファイルがありません")
            
            # Performance metrics
            metrics = self.stats_manager.get_performance_metrics()
            print(f"\n■ パフォーマンス")
            print(f"  CPU使用率: {metrics['cpu_usage']:.1f}%")
            print(f"  メモリ使用率: {metrics['memory_usage']['percent']:.1f}%")
            print(f"  ディスク使用率: {metrics['disk_usage']['percent']:.1f}%")
            
        except Exception as e:
            self.ui_service.display_error(f"録音統計の取得に失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def show_performance_metrics(self) -> None:
        """Show performance metrics"""
        print("\n" + "=" * 50)
        print("パフォーマンス情報")
        print("=" * 50)
        
        try:
            metrics = self.stats_manager.get_performance_metrics()
            
            print(f"\n■ リアルタイム性能")
            print(f"  CPU使用率: {metrics['cpu_usage']:.1f}%")
            
            memory = metrics['memory_usage']
            print(f"  メモリ使用量: {self._format_size(memory['used'])} / {self._format_size(memory['total'])}")
            print(f"  メモリ使用率: {memory['percent']:.1f}%")
            
            disk = metrics['disk_usage']
            print(f"  ディスク使用量: {self._format_size(disk['used'])} / {self._format_size(disk['total'])}")
            print(f"  ディスク使用率: {disk['percent']:.1f}%")
            
            network = metrics['network_status']
            print(f"  ネットワーク: {'接続済み' if network['connected'] else '切断'}")
            
        except Exception as e:
            self.ui_service.display_error(f"パフォーマンス情報の取得に失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def show_log_file(self) -> None:
        """Show log file contents"""
        print("\n" + "=" * 50)
        print("ログファイル")
        print("=" * 50)
        
        try:
            log_info = self.log_manager.get_log_info()
            
            print(f"\n■ ログファイル情報")
            print(f"  ファイル数: {len(log_info['log_files'])}個")
            print(f"  総サイズ: {self._format_size(log_info['total_size'])}")
            
            # Recent log entries
            recent_entries = self.log_manager.get_recent_log_entries(20)
            if recent_entries:
                print(f"\n■ 最近のログ (最新{len(recent_entries)}件)")
                for entry in recent_entries:
                    level_symbol = {
                        "INFO": "ℹ️",
                        "ERROR": "❌",
                        "WARNING": "⚠️",
                        "DEBUG": "🔍"
                    }.get(entry["level"], "📝")
                    
                    print(f"  {level_symbol} {entry['timestamp']} - {entry['message']}")
            else:
                print(f"\n■ 最近のログ")
                print("  ログエントリがありません")
            
        except Exception as e:
            self.ui_service.display_error(f"ログファイルの読み込みに失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def show_dependencies(self) -> None:
        """Show dependency information"""
        print("\n" + "=" * 50)
        print("依存関係")
        print("=" * 50)
        
        try:
            deps = self.system_checker.check_dependencies()
            
            print(f"\n■ インストール済み依存関係 ({len(deps['installed'])}個)")
            for dep in deps['installed']:
                detail = deps['details'][dep]
                required_symbol = "🔴" if detail['required'] else "🟡"
                print(f"  {required_symbol} {dep}")
            
            if deps['missing']:
                print(f"\n■ 不足している依存関係 ({len(deps['missing'])}個)")
                for dep in deps['missing']:
                    detail = deps['details'][dep]
                    required_symbol = "🔴" if detail['required'] else "🟡"
                    print(f"  {required_symbol} {dep}")
            
            print(f"\n■ 凡例")
            print(f"  🔴 必須依存関係")
            print(f"  🟡 オプション依存関係")
            
        except Exception as e:
            self.ui_service.display_error(f"依存関係の確認に失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def show_system_requirements(self) -> None:
        """Show system requirements"""
        print("\n" + "=" * 50)
        print("システム要件")
        print("=" * 50)
        
        try:
            requirements = self.system_checker.check_system_requirements()
            
            print(f"\n■ システム要件チェック")
            
            # Python requirement
            python_req = requirements["python"]
            status_symbol = "✅" if python_req["satisfied"] else "❌"
            print(f"  {status_symbol} Python: {python_req['current']} (必要: {python_req['required']})")
            
            # Disk space requirement
            disk_req = requirements["disk_space"]
            status_symbol = "✅" if disk_req["satisfied"] else "❌"
            print(f"  {status_symbol} ディスク容量: {self._format_size(disk_req['available'])} (必要: {disk_req['required']})")
            
            # Memory requirement
            memory_req = requirements["memory"]
            status_symbol = "✅" if memory_req["satisfied"] else "❌"
            print(f"  {status_symbol} メモリ: {self._format_size(memory_req['available'])} (必要: {memory_req['required']})")
            
            # Dependencies requirement
            deps_req = requirements["dependencies"]
            status_symbol = "✅" if deps_req["satisfied"] else "❌"
            print(f"  {status_symbol} 依存関係: {'満たしています' if deps_req['satisfied'] else '不足しています'}")
            if not deps_req["satisfied"]:
                print(f"    不足: {', '.join(deps_req['missing'])}")
            
        except Exception as e:
            self.ui_service.display_error(f"システム要件の確認に失敗しました: {e}")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
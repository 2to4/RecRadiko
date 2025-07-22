"""
環境検証ユーティリティ

システム環境・依存関係・設定の検証機能を提供します。
"""

import os
import sys
import platform
import subprocess
from typing import Dict, Any, List
from pathlib import Path


class EnvironmentValidator:
    """環境検証クラス
    
    システム環境、Python依存関係、アプリケーション設定の検証を行います。
    """
    
    def __init__(self):
        """初期化"""
        self.platform_info = {
            "system": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version()
        }
    
    def validate_environment(self) -> Dict[str, Any]:
        """環境全体の検証
        
        Returns:
            Dict[str, Any]: 検証結果辞書
        """
        result = {
            "valid": True,
            "platform": self.platform_info,
            "python": self._validate_python(),
            "dependencies": self._validate_dependencies(),
            "paths": self._validate_paths(),
            "permissions": self._validate_permissions()
        }
        
        # 全体の検証結果判定
        result["valid"] = all([
            result["python"]["valid"],
            result["dependencies"]["valid"],
            result["paths"]["valid"],
            result["permissions"]["valid"]
        ])
        
        return result
    
    def _validate_python(self) -> Dict[str, Any]:
        """Python環境検証"""
        try:
            python_version = sys.version_info
            valid = (
                python_version.major == 3 and 
                python_version.minor >= 8
            )
            
            return {
                "valid": valid,
                "version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "executable": sys.executable,
                "path": sys.path[:3]  # 最初の3つのパス
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _validate_dependencies(self) -> Dict[str, Any]:
        """依存関係検証"""
        required_packages = [
            "requests",
            "mutagen", 
            "tqdm",
            "cryptography"
        ]
        
        results = {}
        all_valid = True
        
        for package in required_packages:
            try:
                __import__(package)
                results[package] = {"valid": True, "status": "installed"}
            except ImportError:
                results[package] = {"valid": False, "status": "missing"}
                all_valid = False
        
        return {
            "valid": all_valid,
            "packages": results
        }
    
    def _validate_paths(self) -> Dict[str, Any]:
        """パス・ディレクトリ検証"""
        try:
            # プロジェクトルート検証
            project_root = Path(__file__).parent.parent.parent
            src_path = project_root / "src"
            tests_path = project_root / "tests"
            
            return {
                "valid": src_path.exists() and tests_path.exists(),
                "project_root": str(project_root),
                "src_exists": src_path.exists(),
                "tests_exists": tests_path.exists(),
                "current_dir": os.getcwd()
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def _validate_permissions(self) -> Dict[str, Any]:
        """権限検証"""
        try:
            # 書き込み権限テスト
            test_dir = Path.home() / "Desktop"
            writable = os.access(test_dir, os.W_OK) if test_dir.exists() else False
            
            return {
                "valid": True,
                "desktop_writable": writable,
                "home_writable": os.access(Path.home(), os.W_OK),
                "current_dir_writable": os.access(".", os.W_OK)
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """システム情報取得"""
        return {
            "platform": self.platform_info,
            "environment_variables": {
                "HOME": os.environ.get("HOME", ""),
                "PATH": os.environ.get("PATH", "")[:100] + "...",  # 最初の100文字
                "PYTHON_PATH": os.environ.get("PYTHONPATH", "")
            },
            "disk_space": self._get_disk_space(),
            "memory_info": self._get_memory_info()
        }
    
    def _get_disk_space(self) -> Dict[str, Any]:
        """ディスク容量情報取得"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            return {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "usage_percent": round((used / total) * 100, 1)
            }
        except Exception:
            return {"error": "Unable to get disk space"}
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """メモリ情報取得"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "usage_percent": memory.percent
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}


def validate_environment() -> Dict[str, Any]:
    """環境検証のための便利関数"""
    validator = EnvironmentValidator()
    return validator.validate_environment()


def get_system_info() -> Dict[str, Any]:
    """システム情報取得のための便利関数"""
    validator = EnvironmentValidator()
    return validator.get_system_info()
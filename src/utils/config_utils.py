"""
設定ファイル管理ユーティリティ

JSON設定ファイルの読み込み・保存・検証機能を統一提供します。
4つのファイル（cli.py, auth.py, error_handler.py, settings_screen.py）で
重複していたJSON処理パターンを統一しました。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from src.logging_config import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """統一設定管理クラス
    
    JSON設定ファイルの読み込み・保存・検証を統一処理します。
    
    Usage:
        config_manager = ConfigManager("config.json")
        config = config_manager.load_config(default_config)
        config_manager.save_config(config)
    """
    
    def __init__(self, config_path: Union[str, Path], encoding: str = 'utf-8', template_path: Optional[Union[str, Path]] = None):
        """初期化
        
        Args:
            config_path: 設定ファイルパス
            encoding: ファイルエンコーディング（デフォルト: utf-8）
            template_path: テンプレートファイルパス（指定時はテンプレートを使用）
        """
        self.config_path = Path(config_path)
        self.encoding = encoding
        self.template_path = Path(template_path) if template_path else None
    
    def load_template_config(self) -> Optional[Dict[str, Any]]:
        """テンプレートファイルから設定を読み込み
        
        Returns:
            テンプレート設定辞書（読み込み失敗時はNone）
        """
        if not self.template_path:
            logger.debug("テンプレートパスが指定されていません")
            return None
            
        try:
            if not self.template_path.exists():
                logger.warning(f"テンプレートファイルが存在しません: {self.template_path}")
                return None
                
            with open(self.template_path, 'r', encoding=self.encoding) as f:
                template_config = json.load(f)
            
            logger.info(f"テンプレートファイル読み込み成功: {self.template_path}")
            return template_config
            
        except json.JSONDecodeError as e:
            logger.error(f"テンプレートファイルJSON解析エラー: {self.template_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"テンプレートファイル読み込みエラー: {self.template_path} - {e}")
            return None
    
    def load_config(self, default_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """設定ファイルを読み込み
        
        Args:
            default_config: デフォルト設定辞書
            
        Returns:
            設定辞書（ファイルが存在しない場合はテンプレートまたはデフォルト設定）
        """
        if default_config is None:
            default_config = {}
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding=self.encoding) as f:
                    config = json.load(f)
                
                # デフォルト設定とマージ
                merged_config = default_config.copy()
                merged_config.update(config)
                
                logger.debug(f"設定ファイル読み込み成功: {self.config_path}")
                return merged_config
            else:
                logger.info(f"設定ファイルが存在しません: {self.config_path}")
                
                # テンプレートがある場合はテンプレートを使用
                template_config = self.load_template_config()
                if template_config:
                    # テンプレート設定とデフォルト設定をマージ
                    merged_config = default_config.copy()
                    merged_config.update(template_config)
                    
                    logger.info("テンプレートベースで設定ファイルを作成します")
                    self.save_config(merged_config)
                    return merged_config
                else:
                    # テンプレートがない場合はデフォルト設定を使用
                    logger.info("デフォルト設定を使用します")
                    if default_config:
                        self.save_config(default_config)
                    return default_config.copy()
                
        except json.JSONDecodeError as e:
            logger.error(f"設定ファイルJSON解析エラー: {self.config_path} - {e}")
            return default_config.copy()
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {self.config_path} - {e}")
            return default_config.copy()
    
    def save_config(self, config: Dict[str, Any], indent: int = 2) -> bool:
        """設定ファイルを保存
        
        Args:
            config: 保存する設定辞書
            indent: JSONインデント（デフォルト: 2）
            
        Returns:
            保存成功ならTrue
        """
        try:
            # ディレクトリ作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 一時ファイルに保存後、原子的に移動
            temp_path = self.config_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding=self.encoding) as f:
                json.dump(config, f, ensure_ascii=False, indent=indent)
            
            # 原子的に移動
            temp_path.replace(self.config_path)
            
            logger.debug(f"設定ファイル保存成功: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイル保存エラー: {self.config_path} - {e}")
            return False
    
    def backup_config(self, backup_suffix: str = '.backup') -> bool:
        """設定ファイルをバックアップ
        
        Args:
            backup_suffix: バックアップファイル接尾辞
            
        Returns:
            バックアップ成功ならTrue
        """
        try:
            if not self.config_path.exists():
                logger.warning(f"バックアップ対象ファイルが存在しません: {self.config_path}")
                return False
            
            backup_path = self.config_path.with_suffix(self.config_path.suffix + backup_suffix)
            
            import shutil
            shutil.copy2(self.config_path, backup_path)
            
            logger.info(f"設定ファイルバックアップ作成: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイルバックアップエラー: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any], required_keys: Optional[list] = None) -> bool:
        """設定データの検証
        
        Args:
            config: 検証する設定辞書
            required_keys: 必須キーのリスト
            
        Returns:
            検証成功ならTrue
        """
        try:
            if not isinstance(config, dict):
                logger.error("設定データが辞書型ではありません")
                return False
            
            if required_keys:
                missing_keys = [key for key in required_keys if key not in config]
                if missing_keys:
                    logger.error(f"必須キーが不足しています: {missing_keys}")
                    return False
            
            logger.debug("設定データ検証成功")
            return True
            
        except Exception as e:
            logger.error(f"設定データ検証エラー: {e}")
            return False
    
    def export_config(self, export_path: Union[str, Path], config: Dict[str, Any]) -> bool:
        """設定をファイルにエクスポート
        
        Args:
            export_path: エクスポート先パス
            config: エクスポートする設定辞書
            
        Returns:
            エクスポート成功ならTrue
        """
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding=self.encoding) as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"設定エクスポート成功: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"設定エクスポートエラー: {export_path} - {e}")
            return False
    
    def import_config(self, import_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """設定をファイルからインポート
        
        Args:
            import_path: インポート元パス
            
        Returns:
            インポートした設定辞書（失敗時はNone）
        """
        try:
            import_path = Path(import_path)
            
            if not import_path.exists():
                logger.error(f"インポートファイルが存在しません: {import_path}")
                return None
            
            with open(import_path, 'r', encoding=self.encoding) as f:
                config = json.load(f)
            
            logger.info(f"設定インポート成功: {import_path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"インポートファイルJSON解析エラー: {import_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"設定インポートエラー: {import_path} - {e}")
            return None


def load_json_config(config_path: Union[str, Path], 
                     default_config: Optional[Dict[str, Any]] = None,
                     encoding: str = 'utf-8',
                     template_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """JSON設定ファイルを読み込み（関数版）
    
    Args:
        config_path: 設定ファイルパス
        default_config: デフォルト設定辞書
        encoding: ファイルエンコーディング
        template_path: テンプレートファイルパス
        
    Returns:
        設定辞書
    """
    config_manager = ConfigManager(config_path, encoding, template_path)
    return config_manager.load_config(default_config)


def save_json_config(config_path: Union[str, Path], 
                     config: Dict[str, Any],
                     indent: int = 2,
                     encoding: str = 'utf-8') -> bool:
    """JSON設定ファイルを保存（関数版）
    
    Args:
        config_path: 設定ファイルパス
        config: 保存する設定辞書
        indent: JSONインデント
        encoding: ファイルエンコーディング
        
    Returns:
        保存成功ならTrue
    """
    config_manager = ConfigManager(config_path, encoding)
    return config_manager.save_config(config, indent)
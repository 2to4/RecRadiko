# 🏗️ RecRadiko 開発ガイド

> **高品質なタイムフリー専用システムの開発指針** - 2025年7月15日版

このガイドでは、RecRadikoプロジェクトへの貢献方法、開発環境のセットアップ、アーキテクチャの理解、品質基準について説明します。

## 📋 目次

1. [開発環境セットアップ](#開発環境セットアップ)
2. [アーキテクチャ概要](#アーキテクチャ概要)
3. [開発ガイドライン](#開発ガイドライン)
4. [テスト戦略](#テスト戦略)
5. [コード品質基準](#コード品質基準)
6. [貢献方法](#貢献方法)
7. [リリースプロセス](#リリースプロセス)

## 🚀 開発環境セットアップ

### 必要要件

- **Python 3.8以上**
- **Git**
- **FFmpeg**
- **VSCode**（推奨IDE）

### 1. 開発環境の構築

```bash
# 1. リポジトリをフォーク・クローン
git clone https://github.com/your-username/RecRadiko.git
cd RecRadiko

# 2. 開発ブランチに切り替え
git checkout development

# 3. 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Linux/macOS
# または
venv\Scripts\activate     # Windows

# 4. 開発用依存関係のインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. 開発用設定ファイル作成
cp config.json.template config-dev.json

# 6. 開発環境の動作確認
python RecRadiko.py --config config-dev.json --verbose
```

### 2. IDE設定（VSCode推奨）

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "files.associations": {
    "*.md": "markdown"
  }
}
```

推奨拡張機能：
- Python
- Python Docstring Generator
- GitLens
- Markdown All in One

### 3. 開発用コマンド

```bash
# テスト実行
python -m pytest tests/ -v

# 型チェック
mypy src/

# コードフォーマット
black src/ tests/

# リンター実行
pylint src/

# テストカバレッジ
pytest --cov=src tests/
```

## 🏗️ アーキテクチャ概要

### システム構成

```
RecRadiko v2.0 アーキテクチャ
├── RecRadiko.py              # メインエントリーポイント
├── src/                      # コアシステム
│   ├── cli.py               # 統一CLIシステム（キーボードUI専用）
│   ├── timefree_recorder.py # タイムフリー録音エンジン
│   ├── program_history.py   # 過去番組管理（SQLite）
│   ├── auth.py              # タイムフリー認証システム
│   ├── program_info.py      # 番組情報管理
│   ├── streaming.py         # HLS ストリーミング処理
│   ├── region_mapper.py     # 47都道府県対応
│   ├── error_handler.py     # 統一エラー処理
│   ├── logging_config.py    # ログ設定管理
│   ├── ui/                  # キーボードナビゲーションUI
│   │   ├── recording_workflow.py   # 録音ワークフロー統合
│   │   ├── screen_base.py          # 画面基底クラス
│   │   ├── performance_optimizer.py # パフォーマンス最適化
│   │   ├── screens/                # 画面実装
│   │   │   ├── main_menu_screen.py     # メインメニュー
│   │   │   ├── search_screen.py        # 検索機能
│   │   │   ├── settings_screen.py      # 設定管理
│   │   │   ├── system_info_screen.py   # システム情報
│   │   │   ├── station_select_screen.py # 放送局選択
│   │   │   ├── date_select_screen.py    # 日付選択
│   │   │   └── program_select_screen.py # 番組選択
│   │   ├── input/              # キーボード入力処理
│   │   │   └── keyboard_handler.py # クロスプラットフォーム入力
│   │   ├── services/           # UI共通サービス
│   │   │   └── ui_service.py   # UI共通ロジック
│   │   └── menu_manager.py     # メニュー管理
│   └── utils/               # 共通ユーティリティ
│       ├── config_utils.py  # 統一設定管理
│       ├── base.py          # LoggerMixin統一
│       ├── datetime_utils.py # 日時ユーティリティ
│       ├── network_utils.py  # ネットワークユーティリティ
│       └── path_utils.py     # パスユーティリティ
└── tests/                   # 実環境重視テストスイート
    ├── test_*_integration.py    # 統合テストファイル
    ├── ui/test_*.py             # UIテスト
    ├── utils/test_environment.py # 実環境テスト基盤
    └── conftest.py              # pytest設定
```

### 主要コンポーネント

#### 1. 統一CLIシステム（`src/cli.py`）
- **役割**: キーボードナビゲーションUIの起動・管理
- **特徴**: 従来の対話型CLIを完全削除、UI専用化
- **統一設定管理**: `ConfigManager`を使用したJSON設定処理

#### 2. キーボードナビゲーションUI（`src/ui/`）
- **画面ベース設計**: `ScreenBase`から派生した各画面クラス
- **ワークフロー統合**: `RecordingWorkflow`による統一フロー管理
- **パフォーマンス最適化**: <50ms応答・<100ms画面遷移

#### 3. タイムフリー録音エンジン（`src/timefree_recorder.py`）
- **並行ダウンロード**: 8セグメント同時処理
- **高速処理**: 実時間の110倍速録音実現
- **エラーハンドリング**: 完全な障害回復機能

#### 4. 統一設定管理（`src/utils/config_utils.py`）
- **JSON処理統一**: 4ファイルの重複削除（~200行削減）
- **原子的保存**: 一時ファイル→移動による安全な保存
- **検証機能**: 設定データの整合性チェック

#### 5. 実環境重視テスト（`tests/`）
- **モック使用90%削減**: 1,738個→174個
- **統合テスト重視**: 4つの包括的統合テストファイル
- **実用性検証**: 実際のファイル・設定・暗号化処理使用

## 📝 開発ガイドライン

### コード品質基準

#### 1. 型ヒント（必須）
```python
# 良い例
def process_program_info(program: ProgramInfo, 
                        output_path: Path) -> bool:
    """番組情報を処理"""
    return True

# 悪い例
def process_program_info(program, output_path):
    return True
```

#### 2. LoggerMixin使用（必須）
```python
# 良い例
from src.utils.base import LoggerMixin

class MyClass(LoggerMixin):
    def __init__(self):
        super().__init__()  # ロガー自動初期化
        self.logger.info("初期化完了")

# 悪い例
import logging

class MyClass:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
```

#### 3. 統一設定管理使用（必須）
```python
# 良い例
from src.utils.config_utils import ConfigManager

class MyScreen:
    def __init__(self):
        self.config_manager = ConfigManager("config.json")
        self.config = self.config_manager.load_config(default_config)

# 悪い例
import json

class MyScreen:
    def __init__(self):
        with open("config.json", 'r') as f:
            self.config = json.load(f)
```

#### 4. docstring規約
```python
def record_program(self, program_id: str, quality: str = "256") -> bool:
    """番組を録音する
    
    Args:
        program_id: 番組ID（例: TBS_20250715_060000）
        quality: 音質設定（128, 192, 256, 320）
        
    Returns:
        録音成功ならTrue
        
    Raises:
        RecordingError: 録音処理でエラーが発生した場合
        AuthenticationError: 認証に失敗した場合
        
    Example:
        >>> recorder = TimeFreeRecorder()
        >>> success = recorder.record_program("TBS_20250715_060000", "256")
        >>> print(success)
        True
    """
```

### ファイル・モジュール構成

#### 1. 新しい画面クラス作成
```python
# src/ui/screens/my_new_screen.py
from typing import List, Optional
from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.utils.base import LoggerMixin

class MyNewScreen(ScreenBase):
    """新しい画面の実装"""
    
    def __init__(self):
        super().__init__()
        self.set_title("新しい画面")
        self.ui_service = UIService()
    
    def display_content(self) -> None:
        """画面コンテンツの表示"""
        # 実装
        pass
    
    def handle_input(self, key: str) -> Optional[str]:
        """キー入力の処理"""
        # 実装
        return None
```

#### 2. 新しいユーティリティ関数
```python
# src/utils/my_utils.py
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def process_data(data: List[Dict[str, Any]], 
                output_path: Path) -> bool:
    """データを処理する
    
    Args:
        data: 処理するデータのリスト
        output_path: 出力先パス
        
    Returns:
        処理成功ならTrue
    """
    try:
        # 実装
        logger.info(f"データ処理完了: {len(data)}件")
        return True
    except Exception as e:
        logger.error(f"データ処理エラー: {e}")
        return False
```

### エラーハンドリング規約

#### 1. カスタム例外の使用
```python
# 良い例
class MyFeatureError(RecRadikoError):
    """マイ機能関連のエラー"""
    pass

def my_function():
    if not condition:
        raise MyFeatureError("条件が満たされていません")

# 悪い例
def my_function():
    if not condition:
        raise Exception("エラーです")
```

#### 2. ログとエラーハンドリング
```python
# 良い例
try:
    result = risky_operation()
    self.logger.info("操作成功")
    return result
except SpecificError as e:
    self.logger.error(f"特定エラー: {e}")
    return None
except Exception as e:
    self.logger.error(f"予期しないエラー: {e}")
    raise

# 悪い例
try:
    return risky_operation()
except:
    return None
```

## 🧪 テスト戦略

### テスト方針

#### 1. 実環境重視
- **モック使用最小化**: 外部API・システム操作・UI入力のみ
- **実際のファイル操作**: 一時ディレクトリでの実ファイル処理
- **実際の設定処理**: 統一設定管理の実動作確認

#### 2. 統合テスト重視
```python
# tests/test_my_integration.py
from tests.utils.test_environment import RealEnvironmentTestBase

class TestMyIntegration(RealEnvironmentTestBase):
    """統合テストの実装例"""
    
    def test_real_workflow(self, temp_env):
        """実環境でのワークフローテスト"""
        # 実際のファイル・設定を使用したテスト
        cli = self.setup_real_cli(temp_env)
        
        # 実際の処理実行
        result = cli.execute_workflow()
        
        # 実際のファイル確認
        assert temp_env.recordings_dir.exists()
        assert result == True
```

#### 3. UI テスト
```python
# tests/ui/test_my_screen.py
from unittest.mock import patch
from src.ui.screens.my_screen import MyScreen

class TestMyScreen:
    """UIテストの実装例"""
    
    @patch('src.ui.input.keyboard_handler.KeyboardHandler.get_key')
    def test_navigation(self, mock_get_key):
        """キーボードナビゲーションテスト"""
        mock_get_key.side_effect = ['down', 'enter']
        
        screen = MyScreen()
        result = screen.run()
        
        assert result == "expected_result"
```

### テスト実行

```bash
# 全テスト実行
python -m pytest tests/ -v

# 統合テスト（実環境）のみ
python -m pytest tests/test_*_integration.py -v

# UIテストのみ
python -m pytest tests/ui/ -v

# カバレッジ付きテスト
python -m pytest tests/ --cov=src --cov-report=html

# 特定テストクラス
python -m pytest tests/test_command_interface.py::TestCLIRealEnvironment -v
```

### テスト品質基準

- **カバレッジ**: 95%以上維持
- **成功率**: 95%以上（262テスト中248テスト成功）
- **実行時間**: 全テスト10分以内
- **実環境率**: モック使用10%以下

## ⚡ パフォーマンス基準

### UI応答性
- **キー操作応答**: < 50ms
- **画面遷移**: < 100ms
- **メニュー表示**: < 30ms

### 録音性能
- **録音速度**: 実時間の100倍以上
- **並行処理**: 8セグメント同時ダウンロード
- **メモリ使用**: < 500MB（長時間番組録音時）

### システム効率
- **起動時間**: < 2秒
- **設定読み込み**: < 100ms
- **キャッシュ応答**: < 50ms

## 🔄 ブランチ戦略

### ブランチ構成

```
main (本番用・安定版)
  ↑
development (開発統合)
  ↑
feature/feature-name (機能開発)
  ↑
hotfix/issue-name (緊急修正)
```

### ワークフロー

```bash
# 1. 機能開発ブランチ作成
git checkout development
git pull origin development
git checkout -b feature/keyboard-ui-enhancement

# 2. 開発・テスト
# コード作成・テスト実行

# 3. コミット
git add .
git commit -m "feat: キーボードUI機能拡張

- 新しいショートカットキー追加
- 応答速度30%向上
- テスト8個追加

🤖 Generated with Claude Code"

# 4. プッシュ・プルリクエスト
git push origin feature/keyboard-ui-enhancement
# GitHubでプルリクエスト作成
```

### コミットメッセージ規約

```
<type>: <description>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `docs`: ドキュメント更新
- `style`: コードスタイル修正

**例**:
```
feat: 設定画面に音質設定追加

- AAC 320kbps対応
- リアルタイム音質プレビュー
- 設定のエクスポート/インポート機能

Closes #123

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

## 🚀 リリースプロセス

### 1. バージョニング

セマンティックバージョニング（SemVer）を使用：
- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

例: `2.1.3`

### 2. リリース手順

```bash
# 1. development → main マージ
git checkout main
git merge development

# 2. バージョンアップ
# version in setup.py, __init__.py を更新

# 3. タグ作成
git tag -a v2.1.0 -m "Release v2.1.0: キーボードUI完全対応"

# 4. プッシュ
git push origin main
git push origin v2.1.0

# 5. リリースノート作成（GitHub）
```

### 3. リリースノートテンプレート

```markdown
## 🎉 RecRadiko v2.1.0

### ✨ 新機能
- キーボードナビゲーションUI完全対応
- 設定管理画面の統合
- 検索機能の強化

### 🐛 バグ修正
- 録音ファイル名の文字化け修正
- メモリリーク問題の解消

### ⚡ パフォーマンス改善
- UI応答速度30%向上
- 録音速度20%高速化

### 🧪 品質向上
- テスト262個95%成功
- 型ヒント100%対応完了

### 💔 Breaking Changes
- 従来の対話型CLIモードを削除
- 設定ファイル形式の一部変更

### 📊 統計
- コード行数: 15,000+行
- テストカバレッジ: 95%
- UI画面数: 4画面
```

## 🤝 貢献方法

### 1. 貢献の種類

#### コードコントリビューション
- 新機能開発
- バグ修正
- パフォーマンス改善
- テスト追加

#### ドキュメンテーション
- ユーザーマニュアル改善
- API ドキュメント作成
- チュートリアル作成

#### 品質向上
- テストケース追加
- コードレビュー
- パフォーマンス分析

### 2. 貢献プロセス

```bash
# 1. Fork & Clone
git clone https://github.com/your-username/RecRadiko.git

# 2. Issue確認・作成
# GitHubで Issue を確認または作成

# 3. ブランチ作成
git checkout -b feature/issue-123-new-feature

# 4. 開発
# コード作成・テスト・ドキュメント更新

# 5. 品質チェック
python -m pytest tests/ -v
mypy src/
black src/ tests/
pylint src/

# 6. プルリクエスト
# GitHub でプルリクエスト作成
```

### 3. プルリクエスト基準

#### 必須項目
- [ ] すべてのテストが成功（95%以上）
- [ ] 型ヒント完備
- [ ] docstring記載
- [ ] 新機能には対応するテスト追加
- [ ] ドキュメント更新（必要な場合）

#### レビュー観点
- **機能性**: 要件を満たしているか
- **性能**: パフォーマンス基準を満たしているか
- **品質**: コード品質基準に準拠しているか
- **テスト**: 適切なテストが追加されているか
- **設計**: アーキテクチャに適合しているか

## 📞 サポート・連絡先

### 開発者向けサポート
- **GitHub Discussions**: [開発者フォーラム](https://github.com/your-repo/RecRadiko/discussions)
- **GitHub Issues**: [バグ報告・機能要望](https://github.com/your-repo/RecRadiko/issues)

### ドキュメント
- **API Reference**: [詳細API仕様](API_REFERENCE.md)
- **アーキテクチャ設計**: [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md)
- **テスト仕様**: [TEST_DESIGN.md](TEST_DESIGN.md)

### 開発環境ヘルプ
- **設定問題**: [環境設定ガイド](ENVIRONMENT_SETUP.md)
- **IDE設定**: [IDE設定ガイド](IDE_CONFIGURATION.md)

---

**🏗️ このガイドは RecRadiko v2.0.0 (2025年7月15日) 対応版です**

**Happy Coding! 🎉**
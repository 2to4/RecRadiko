# RecRadiko 設定ファイルガイド

## 概要

RecRadiko v2.0では設定が大幅に簡素化され、必要最小限の設定のみで動作するようになりました。

## 設定ファイル (config.json)

### 基本設定

```json
{
  "version": "2.0",
  "prefecture": "東京",
  "audio": {
    "format": "mp3",
    "bitrate": 256,
    "sample_rate": 48000
  },
  "recording": {
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "notification": {
    "type": "macos_standard",
    "enabled": true
  },
  "system": {
    "log_level": "INFO",
    "user_agent": "RecRadiko/2.0"
  }
}
```

### 設定項目説明

#### prefecture (地域設定)
- **説明**: 録音可能な地域を指定
- **値**: 47都道府県名（例: "東京", "大阪", "北海道"）
- **変更方法**: UI設定画面または config.json 直接編集

#### audio (音質設定)
- **format**: 音声形式 ("mp3" または "aac")
- **bitrate**: ビットレート (128, 256, 320)
- **sample_rate**: サンプルレート (44100, 48000)
- **変更方法**: UI設定画面推奨

#### recording (録音設定)
- **timeout_seconds**: セグメントダウンロードタイムアウト (秒)
- **max_retries**: 失敗時の再試行回数

#### notification (通知設定)
- **type**: 通知タイプ ("無効", "macos_standard", "sound", "email")
- **enabled**: 通知有効/無効

#### system (システム設定)
- **log_level**: ログレベル ("DEBUG", "INFO", "WARNING", "ERROR")
- **user_agent**: HTTPリクエスト時のUser-Agent文字列

## 自動化済み設定 (設定不要)

以下の項目は Phase 5 で自動化され、設定不要になりました：

### 📁 保存先 (固定)
- **パス**: `~/Desktop/RecRadiko/`
- **自動作成**: フォルダが存在しない場合は自動作成
- **変更不可**: UIから変更できません（固定設定）

### 🎵 ID3タグ (常時実行)
- **自動埋め込み**: 全録音ファイルにID3タグを自動付与
- **含まれる情報**: 番組名、出演者、放送局、放送日、ジャンル、説明
- **設定不要**: 常に実行されます

### 📄 ページング (最適化済み)
- **1ページあたり**: 20項目表示
- **自動調整**: 30項目以下は全表示
- **メニュー操作**: 「前のページ」「次のページ」選択

## 設定ファイルの作成

### 初回セットアップ
```bash
# テンプレートをコピー
cp config.json.template config.json

# 必要に応じて都道府県名を編集
nano config.json
```

### UI設定画面での変更
RecRadiko起動後、「設定を変更する」から以下が変更可能：
- 地域設定 (47都道府県対応)
- 音質設定 (専用画面)
- 通知設定
- 設定のエクスポート/インポート

## 下位互換性

Phase 5では多くの設定項目が削除されましたが、既存の設定ファイルは自動的に新形式に変換されます。不要な設定項目は無視され、システムは正常に動作します。

## 推奨設定

**一般用途**:
```json
{
  "prefecture": "東京",
  "audio": {
    "format": "mp3",
    "bitrate": 256,
    "sample_rate": 48000
  }
}
```

**高音質録音**:
```json
{
  "prefecture": "東京", 
  "audio": {
    "format": "mp3",
    "bitrate": 320,
    "sample_rate": 48000
  }
}
```

**最小設定** (デフォルトで十分な場合):
```json
{
  "prefecture": "東京"
}
```

## トラブルシューティング

### 設定ファイルエラー
- JSON形式が正しいか確認
- 不要な設定項目は削除
- テンプレートからコピーし直す

### 地域設定エラー
- 都道府県名が正しいか確認
- UI設定画面から選択推奨

### 音質設定エラー
- サポートされている値を使用
- UI設定画面での変更推奨

---

**更新日**: 2025年7月16日  
**対応版本**: RecRadiko v2.0 (Phase 5)
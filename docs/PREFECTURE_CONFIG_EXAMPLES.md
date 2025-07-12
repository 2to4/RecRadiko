# 都道府県設定の使用例

## 基本的な設定方法

`config.json` の `prefecture` フィールドに都道府県名を設定すると、自動的に対応する地域IDが設定されます。

### 設定例

```json
{
  "prefecture": "大阪"
}
```

上記のように設定すると、`prefecture` の値から自動的にメモリ内で `area_id` が `JP27` に設定されます。（設定ファイルには `area_id` は保存されません）

## 対応する都道府県名

### 日本語名での設定

```json
{
  "prefecture": "東京"
}
```

```json
{
  "prefecture": "東京都"
}
```

### 英語名での設定

```json
{
  "prefecture": "Tokyo"
}
```

```json
{
  "prefecture": "tokyo"
}
```

## 地方別設定例

### 関東地方

```json
// 東京都
{
  "prefecture": "東京",
  "output_dir": "./recordings/tokyo"
}

// 神奈川県
{
  "prefecture": "神奈川",
  "output_dir": "./recordings/kanagawa"
}

// 千葉県
{
  "prefecture": "Chiba",
  "output_dir": "./recordings/chiba"
}
```

### 関西地方

```json
// 大阪府
{
  "prefecture": "大阪",
  "output_dir": "./recordings/osaka"
}

// 京都府
{
  "prefecture": "Kyoto",
  "output_dir": "./recordings/kyoto"
}

// 兵庫県
{
  "prefecture": "兵庫",
  "output_dir": "./recordings/hyogo"
}
```

### 中部地方

```json
// 愛知県
{
  "prefecture": "愛知",
  "output_dir": "./recordings/aichi"
}

// 静岡県
{
  "prefecture": "Shizuoka",
  "output_dir": "./recordings/shizuoka"
}
```

### 九州地方

```json
// 福岡県
{
  "prefecture": "福岡",
  "output_dir": "./recordings/fukuoka"
}

// 沖縄県
{
  "prefecture": "沖縄",
  "output_dir": "./recordings/okinawa"
}
```

## 完全な設定例

### 大阪府での設定

```json
{
  "_comment": "大阪府でのRecRadiko設定例（area_id JP27 に自動変換）",
  "prefecture": "大阪",
  "premium_username": "",
  "premium_password": "",
  "output_dir": "./recordings/osaka",
  "default_format": "mp3",
  "default_bitrate": 128,
  "max_concurrent_recordings": 4,
  "auto_cleanup_enabled": true,
  "retention_days": 30,
  "min_free_space_gb": 10.0,
  "notification_enabled": true,
  "notification_minutes": [5, 1],
  "log_level": "INFO",
  "log_file": "recradiko_osaka.log",
  "max_log_size_mb": 100,
  "request_timeout": 30,
  "max_retries": 3
}
```

### 北海道での設定

```json
{
  "_comment": "北海道でのRecRadiko設定例（area_id JP1 に自動変換）",
  "prefecture": "北海道",
  "premium_username": "",
  "premium_password": "",
  "output_dir": "./recordings/hokkaido",
  "default_format": "aac",
  "default_bitrate": 64,
  "max_concurrent_recordings": 2,
  "auto_cleanup_enabled": true,
  "retention_days": 60,
  "min_free_space_gb": 5.0,
  "notification_enabled": true,
  "notification_minutes": [10, 2],
  "log_level": "DEBUG",
  "log_file": "recradiko_hokkaido.log",
  "max_log_size_mb": 50,
  "request_timeout": 45,
  "max_retries": 5
}
```

## CLIコマンドでの確認方法

### 現在の地域設定確認

```bash
# 対話型モードで実行
python RecRadiko.py

# コマンド入力
show-region
```

出力例：
```
現在の地域設定:
----------------------------------------
地域ID:         JP27
都道府県名:     大阪府
英語名:         Osaka
地方:           近畿
主要放送局:     OBC, MBS, ABC, FM-OSAKA, FM802

地域設定の変更方法:
----------------------------------------
config.jsonの 'prefecture' フィールドに都道府県名を設定してください
例: "prefecture": "大阪" または "prefecture": "Osaka"
```

### 全都道府県一覧確認

```bash
# 対話型モードで実行
python RecRadiko.py

# コマンド入力
list-prefectures
```

出力例：
```
利用可能な都道府県一覧:
==================================================

【北海道】
--------------------
  北海道     (JP1) / Hokkaido      (HBC, STV, AIR-G')

【関東】
--------------------
  茨城県     (JP8) / Ibaraki       (IBS)
  栃木県     (JP9) / Tochigi       (CRT)
  群馬県     (JP10) / Gunma        (FM-GUNMA)
  埼玉県     (JP11) / Saitama      (NACK5)
  千葉県     (JP12) / Chiba        (CRO, bayfm)
  東京都     (JP13) / Tokyo        (TBS, QRR, LFR...)
  神奈川県   (JP14) / Kanagawa     (YBS, FMN)

設定例:
  "prefecture": "大阪"     # 日本語名
  "prefecture": "Osaka"    # 英語名
  "prefecture": "osaka"    # 小文字でも可
```

## エラー対処方法

### 不明な都道府県名の場合

```json
{
  "prefecture": "存在しない県"
}
```

この場合、ログに以下のメッセージが出力されます：

```
WARNING - 不明な都道府県名: '存在しない県' - 利用可能な都道府県名を確認してください
```

### 設定の優先順位

1. **推奨**: `prefecture` フィールドが設定されている場合：
   - 都道府県名から地域IDをメモリ内で自動設定
   - 設定ファイルには `area_id` は保存されません（クリーンな設定維持）

2. **後方互換性**: `prefecture` フィールドが未設定の場合：
   - 既存の `area_id` フィールドの値を使用（レガシー設定サポート）
   - `area_id` も無効な場合はデフォルト（JP13：東京）を使用

**💡 ヒント**: 新規設定では `prefecture` フィールドの使用を強く推奨します。

## トラブルシューティング

### Q: 設定を変更したのに反映されない

A: 以下を確認してください：

1. `config.json` のJSON形式が正しいか
2. 都道府県名のスペルが正しいか
3. RecRadikoを再起動したか

### Q: 対応していない地域はある？

A: 全47都道府県に対応しています。`list-prefectures` コマンドで確認できます。

### Q: 英語名と日本語名の両方設定できる？

A: `prefecture` フィールドには1つの値のみ設定してください。日本語名または英語名のどちらかを使用してください。

## 実用的な設定パターン

### パターン1: シンプル設定

```json
{
  "prefecture": "東京",
  "default_format": "mp3"
}
```

### パターン2: 地域別出力ディレクトリ

```json
{
  "prefecture": "大阪",
  "output_dir": "./recordings/osaka",
  "log_file": "recradiko_osaka.log"
}
```

### パターン3: 地方局対応設定

```json
{
  "prefecture": "沖縄",
  "output_dir": "./recordings/okinawa",
  "request_timeout": 60,
  "max_retries": 5
}
```

これらの設定例を参考に、お住まいの地域に合わせてRecRadikoを設定してください。
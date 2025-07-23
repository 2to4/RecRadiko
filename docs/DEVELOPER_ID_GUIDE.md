# Developer ID証明書取得ガイド

## 📋 概要

Developer ID証明書は、Mac App Store以外でmacOSアプリケーションを配布するための必須証明書です。Gatekeeperの警告なしにアプリを配布できるようになります。

## 💰 費用と要件

### Apple Developer Program
- **年会費**: $99 USD（約14,000円）
- **更新**: 毎年必要
- **個人/法人**: 両方対応
- **支払い方法**: クレジットカード

### 必要なもの
1. **Apple ID**: iCloudで使用しているものでOK
2. **クレジットカード**: Visa、MasterCard、American Express対応
3. **身分証明書**: 
   - 個人の場合: 運転免許証、パスポートなど
   - 法人の場合: 登記簿謄本、法人番号など

## 🚀 申請手順

### Step 1: Apple Developer Programに登録

1. **Apple Developer サイトにアクセス**
   ```
   https://developer.apple.com/programs/
   ```

2. **「Enroll」をクリック**
   - 右上の「Enroll」ボタンをクリック

3. **Apple IDでサインイン**
   - 既存のApple IDを使用
   - 2ファクタ認証が必要

4. **Entity Type選択**
   - **Individual**: 個人開発者（推奨）
   - **Organization**: 法人・団体

5. **個人情報入力**
   - 氏名（英語表記）
   - 住所（英語表記）
   - 電話番号

6. **利用規約同意**
   - Apple Developer Program License Agreementに同意

7. **支払い情報入力**
   - クレジットカード情報
   - 請求先住所

8. **申請完了**
   - 通常24-48時間で承認
   - メールで通知が届く

### Step 2: Developer ID証明書の生成

1. **Apple Developer アカウントにログイン**
   ```
   https://developer.apple.com/account/
   ```

2. **Certificates, Identifiers & Profiles**
   - 左メニューから選択

3. **Certificates** → **+ボタン**
   - 新しい証明書を作成

4. **Developer ID Application**
   - 「Developer ID Application」を選択
   - これがアプリケーション署名用証明書

5. **CSR (Certificate Signing Request) 作成**
   
   **macOSのキーチェーンアクセスで作成:**
   ```
   1. キーチェーンアクセス.app を開く
   2. メニュー → キーチェーンアクセス → 証明書アシスタント → 認証局に証明書を要求
   3. ユーザーのメールアドレス: Apple IDのメール
   4. 通称: 任意の名前（例: RecRadiko Developer ID）
   5. CAのメールアドレス: 空白
   6. 要求の処理: ディスクに保存 & 公開鍵と秘密鍵のペアを作成
   7. 鍵のサイズ: 2048ビット
   8. アルゴリズム: RSA
   9. 「続ける」でCSRファイルを保存
   ```

6. **CSRファイルをアップロード**
   - 作成したCSRファイルを選択してアップロード

7. **証明書をダウンロード**
   - 生成された証明書(.cer)をダウンロード
   - ダブルクリックでキーチェーンに追加

### Step 3: Xcode設定（オプション）

1. **Xcode** → **Preferences** → **Accounts**
2. **Apple IDを追加**
3. **Manage Certificates**
4. **Developer ID Application証明書を確認**

## 🔧 証明書の確認方法

### ターミナルで確認
```bash
# 利用可能な証明書を確認
security find-identity -v -p codesigning

# Developer ID証明書を確認
security find-identity -v -p codesigning | grep "Developer ID Application"
```

### キーチェーンアクセスで確認
1. キーチェーンアクセス.app を開く
2. 「ログイン」キーチェーンを選択
3. 「証明書」カテゴリを選択
4. 「Developer ID Application: (あなたの名前)」を確認

## 🎯 RecRadikoでの使用方法

### 証明書名の確認
```bash
security find-identity -v -p codesigning
```

出力例:
```
1) ABC123DEF456... "Developer ID Application: Futoshi Yoshida (TEAM123456)"
```

### 署名コマンド
```bash
# メイン署名
codesign --force --deep --sign "Developer ID Application: Futoshi Yoshida (TEAM123456)" \
  --options runtime \
  --entitlements entitlements.plist \
  dist/RecRadiko.app

# 署名確認
codesign --verify --verbose=2 dist/RecRadiko.app

# Gatekeeper確認
spctl --assess --verbose dist/RecRadiko.app
```

## 🚨 Notarization（公証）について

Developer ID証明書取得後は、Notarizationも必要です：

### App-Specific Passwordの生成
1. **Apple ID サイト**にアクセス
   ```
   https://appleid.apple.com/
   ```
2. **サインイン**
3. **App用パスワード** → **パスワードを生成**
4. **ラベル**: "RecRadiko Notarization"
5. **生成されたパスワードを保存**

### Notarizationコマンド
```bash
# アプリをZIP圧縮
ditto -c -k --keepParent dist/RecRadiko.app RecRadiko.zip

# Notarization送信
xcrun notarytool submit RecRadiko.zip \
  --apple-id "your@email.com" \
  --team-id "TEAM123456" \
  --password "xxxx-xxxx-xxxx-xxxx" \
  --wait

# 成功後、ステープル（公証チケット添付）
xcrun stapler staple dist/RecRadiko.app
```

## 💡 メリット

### ユーザー体験
- **Gatekeeperの警告なし**: ダブルクリックで即座に起動
- **信頼性**: Appleによる検証済み
- **セキュリティ**: マルウェアスキャン済み

### 開発者メリット
- **プロフェッショナル**: 正式な開発者として認定
- **App Store Connect**: アプリの分析データ取得
- **TestFlight**: ベータテスト配布
- **その他のAppleサービス**: Push通知、iCloud等

## ⚠️ 注意事項

### 年会費
- 毎年$99の支払いが必要
- 支払いを忘れると証明書が無効化

### 証明書の有効期限
- Developer ID証明書: 5年間有効
- 期限前に更新が必要

### Team管理
- 複数人で開発する場合はTeam管理が重要
- 権限の適切な設定

## 🔄 代替案

### 1. 署名なし配布
- **メリット**: 費用なし、即座に配布可能
- **デメリット**: ユーザーが手動で許可する必要

### 2. 自己署名証明書
- **メリット**: 費用なし
- **デメリット**: 配布時に各ユーザーで設定が必要

### 3. オープンソース配布
- **メリット**: ユーザーが自分でビルド
- **デメリット**: 技術的なユーザーのみ対象

## 📞 サポート

### Apple Developer Support
- 電話サポート（英語）
- Developer Forums
- Technical Support Incidents（年間2回まで無料）

### 申請に関する問題
- 身分証明に時間がかかる場合がある
- 法人の場合は追加書類が必要な場合がある
- 支払いエラーの場合はカード会社に確認

---

**推奨アクション**: RecRadikoの本格的な配布を考えている場合、Developer ID証明書の取得をお勧めします。年間$99は、プロフェッショナルなアプリケーション配布には妥当な投資です。

**作成日**: 2025年7月23日  
**更新日**: 2025年7月23日
#!/bin/bash
# RecRadiko アプリケーション署名スクリプト

set -e

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# アプリケーションパス
APP_PATH="dist/RecRadiko.app"
ENTITLEMENTS="entitlements.plist"

echo -e "${BLUE}RecRadiko アプリケーション署名スクリプト${NC}"
echo "========================================"

# アプリケーションの存在確認
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}エラー: $APP_PATH が見つかりません${NC}"
    exit 1
fi

# entitlements.plistの存在確認
if [ ! -f "$ENTITLEMENTS" ]; then
    echo -e "${RED}エラー: $ENTITLEMENTS が見つかりません${NC}"
    exit 1
fi

# 署名オプションの選択
echo -e "\n署名方法を選択してください:"
echo "1) アドホック署名（テスト用、ローカル実行のみ）"
echo "2) Developer ID署名（配布用、要Apple Developer Program）"
echo -n "選択 (1 or 2): "
read choice

case $choice in
    1)
        echo -e "\n${BLUE}アドホック署名を実行中...${NC}"
        
        # まず内部バイナリから署名
        echo "1. ffmpegを署名中..."
        codesign --force --sign - "$APP_PATH/Contents/MacOS/ffmpeg"
        
        echo "2. Frameworksを署名中..."
        find "$APP_PATH/Contents/Frameworks" -name "*.dylib" -o -name "*.so" | while read lib; do
            codesign --force --sign - "$lib"
        done
        
        echo "3. アプリケーション全体を署名中..."
        codesign --force --deep --sign - --entitlements "$ENTITLEMENTS" "$APP_PATH"
        
        echo -e "${GREEN}✅ アドホック署名完了${NC}"
        ;;
        
    2)
        echo -e "\n${BLUE}Developer ID署名${NC}"
        echo "利用可能な証明書を確認中..."
        
        # 証明書の一覧表示
        security find-identity -v -p codesigning
        
        echo -e "\n証明書名を入力してください（例: 'Developer ID Application: Your Name (XXXXXXXXXX)'）:"
        read -r CERT_NAME
        
        if [ -z "$CERT_NAME" ]; then
            echo -e "${RED}エラー: 証明書名が入力されていません${NC}"
            exit 1
        fi
        
        echo -e "\n${BLUE}Developer ID署名を実行中...${NC}"
        
        # 内部バイナリから署名
        echo "1. ffmpegを署名中..."
        codesign --force --sign "$CERT_NAME" --options runtime "$APP_PATH/Contents/MacOS/ffmpeg"
        
        echo "2. Frameworksを署名中..."
        find "$APP_PATH/Contents/Frameworks" -name "*.dylib" -o -name "*.so" | while read lib; do
            codesign --force --sign "$CERT_NAME" --options runtime "$lib"
        done
        
        echo "3. アプリケーション全体を署名中..."
        codesign --force --deep --sign "$CERT_NAME" --options runtime --entitlements "$ENTITLEMENTS" "$APP_PATH"
        
        echo -e "${GREEN}✅ Developer ID署名完了${NC}"
        ;;
        
    *)
        echo -e "${RED}無効な選択です${NC}"
        exit 1
        ;;
esac

# 署名の検証
echo -e "\n${BLUE}署名を検証中...${NC}"
codesign --verify --verbose=2 "$APP_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 署名検証成功${NC}"
    
    # 詳細情報表示
    echo -e "\n${BLUE}署名詳細情報:${NC}"
    codesign --display --verbose=4 "$APP_PATH"
    
    # Gatekeeperチェック（Developer ID署名の場合のみ）
    if [ "$choice" == "2" ]; then
        echo -e "\n${BLUE}Gatekeeperチェック:${NC}"
        spctl --assess --verbose "$APP_PATH" || echo -e "${YELLOW}警告: Gatekeeper評価失敗（Notarization未実施の可能性）${NC}"
    fi
else
    echo -e "${RED}❌ 署名検証失敗${NC}"
    exit 1
fi

echo -e "\n${GREEN}署名プロセス完了!${NC}"
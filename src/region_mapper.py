"""
地域IDマッピングモジュール

このモジュールは都道府県名から地域IDへの変換機能を提供します。
- 47都道府県の完全マッピング
- 英語・日本語名対応
- 地域ID逆引き機能
"""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class RegionInfo:
    """地域情報"""
    area_id: str           # 地域ID（JP13等）
    prefecture_ja: str     # 都道府県名（日本語）
    prefecture_en: str     # 都道府県名（英語）
    region_name: str       # 地方名
    major_stations: List[str]  # 主要放送局例


class RegionMapper:
    """地域IDマッピングクラス"""
    
    # 47都道府県の完全マッピング（日本語・英語対応）
    REGION_MAPPING = {
        # 北海道・東北地方
        "北海道": "JP1", "Hokkaido": "JP1", "hokkaido": "JP1",
        "青森": "JP2", "青森県": "JP2", "Aomori": "JP2", "aomori": "JP2",
        "岩手": "JP3", "岩手県": "JP3", "Iwate": "JP3", "iwate": "JP3",
        "宮城": "JP4", "宮城県": "JP4", "Miyagi": "JP4", "miyagi": "JP4",
        "秋田": "JP5", "秋田県": "JP5", "Akita": "JP5", "akita": "JP5",
        "山形": "JP6", "山形県": "JP6", "Yamagata": "JP6", "yamagata": "JP6",
        "福島": "JP7", "福島県": "JP7", "Fukushima": "JP7", "fukushima": "JP7",
        
        # 関東地方
        "茨城": "JP8", "茨城県": "JP8", "Ibaraki": "JP8", "ibaraki": "JP8",
        "栃木": "JP9", "栃木県": "JP9", "Tochigi": "JP9", "tochigi": "JP9",
        "群馬": "JP10", "群馬県": "JP10", "Gunma": "JP10", "gunma": "JP10",
        "埼玉": "JP11", "埼玉県": "JP11", "Saitama": "JP11", "saitama": "JP11",
        "千葉": "JP12", "千葉県": "JP12", "Chiba": "JP12", "chiba": "JP12",
        "東京": "JP13", "東京都": "JP13", "Tokyo": "JP13", "tokyo": "JP13",
        "神奈川": "JP14", "神奈川県": "JP14", "Kanagawa": "JP14", "kanagawa": "JP14",
        
        # 中部地方
        "新潟": "JP15", "新潟県": "JP15", "Niigata": "JP15", "niigata": "JP15",
        "富山": "JP16", "富山県": "JP16", "Toyama": "JP16", "toyama": "JP16",
        "石川": "JP17", "石川県": "JP17", "Ishikawa": "JP17", "ishikawa": "JP17",
        "福井": "JP18", "福井県": "JP18", "Fukui": "JP18", "fukui": "JP18",
        "山梨": "JP19", "山梨県": "JP19", "Yamanashi": "JP19", "yamanashi": "JP19",
        "長野": "JP20", "長野県": "JP20", "Nagano": "JP20", "nagano": "JP20",
        "岐阜": "JP21", "岐阜県": "JP21", "Gifu": "JP21", "gifu": "JP21",
        "静岡": "JP22", "静岡県": "JP22", "Shizuoka": "JP22", "shizuoka": "JP22",
        "愛知": "JP23", "愛知県": "JP23", "Aichi": "JP23", "aichi": "JP23",
        
        # 近畿地方
        "三重": "JP24", "三重県": "JP24", "Mie": "JP24", "mie": "JP24",
        "滋賀": "JP25", "滋賀県": "JP25", "Shiga": "JP25", "shiga": "JP25",
        "京都": "JP26", "京都府": "JP26", "Kyoto": "JP26", "kyoto": "JP26",
        "大阪": "JP27", "大阪府": "JP27", "Osaka": "JP27", "osaka": "JP27",
        "兵庫": "JP28", "兵庫県": "JP28", "Hyogo": "JP28", "hyogo": "JP28",
        "奈良": "JP29", "奈良県": "JP29", "Nara": "JP29", "nara": "JP29",
        "和歌山": "JP30", "和歌山県": "JP30", "Wakayama": "JP30", "wakayama": "JP30",
        
        # 中国地方
        "鳥取": "JP31", "鳥取県": "JP31", "Tottori": "JP31", "tottori": "JP31",
        "島根": "JP32", "島根県": "JP32", "Shimane": "JP32", "shimane": "JP32",
        "岡山": "JP33", "岡山県": "JP33", "Okayama": "JP33", "okayama": "JP33",
        "広島": "JP34", "広島県": "JP34", "Hiroshima": "JP34", "hiroshima": "JP34",
        "山口": "JP35", "山口県": "JP35", "Yamaguchi": "JP35", "yamaguchi": "JP35",
        
        # 四国地方
        "徳島": "JP36", "徳島県": "JP36", "Tokushima": "JP36", "tokushima": "JP36",
        "香川": "JP37", "香川県": "JP37", "Kagawa": "JP37", "kagawa": "JP37",
        "愛媛": "JP38", "愛媛県": "JP38", "Ehime": "JP38", "ehime": "JP38",
        "高知": "JP39", "高知県": "JP39", "Kochi": "JP39", "kochi": "JP39",
        
        # 九州・沖縄地方
        "福岡": "JP40", "福岡県": "JP40", "Fukuoka": "JP40", "fukuoka": "JP40",
        "佐賀": "JP41", "佐賀県": "JP41", "Saga": "JP41", "saga": "JP41",
        "長崎": "JP42", "長崎県": "JP42", "Nagasaki": "JP42", "nagasaki": "JP42",
        "熊本": "JP43", "熊本県": "JP43", "Kumamoto": "JP43", "kumamoto": "JP43",
        "大分": "JP44", "大分県": "JP44", "Oita": "JP44", "oita": "JP44",
        "宮崎": "JP45", "宮崎県": "JP45", "Miyazaki": "JP45", "miyazaki": "JP45",
        "鹿児島": "JP46", "鹿児島県": "JP46", "Kagoshima": "JP46", "kagoshima": "JP46",
        "沖縄": "JP47", "沖縄県": "JP47", "Okinawa": "JP47", "okinawa": "JP47",
    }
    
    # 地域詳細情報（地域ID順、地方内は北から南へ）
    REGION_INFO = {
        # 北海道
        "JP1": RegionInfo("JP1", "北海道", "Hokkaido", "北海道", ["HBC", "STV", "AIR-G'"]),
        
        # 東北（北から南へ）
        "JP2": RegionInfo("JP2", "青森県", "Aomori", "東北", ["RAB"]),
        "JP3": RegionInfo("JP3", "岩手県", "Iwate", "東北", ["IBC"]),
        "JP5": RegionInfo("JP5", "秋田県", "Akita", "東北", ["ABS"]),
        "JP4": RegionInfo("JP4", "宮城県", "Miyagi", "東北", ["TBC", "fmSENDAI", "FMii"]),
        "JP6": RegionInfo("JP6", "山形県", "Yamagata", "東北", ["YBC"]),
        "JP7": RegionInfo("JP7", "福島県", "Fukushima", "東北", ["RFC"]),
        
        # 関東（北から南へ）
        "JP8": RegionInfo("JP8", "茨城県", "Ibaraki", "関東", ["IBS"]),
        "JP9": RegionInfo("JP9", "栃木県", "Tochigi", "関東", ["CRT"]),
        "JP10": RegionInfo("JP10", "群馬県", "Gunma", "関東", ["FM-GUNMA"]),
        "JP11": RegionInfo("JP11", "埼玉県", "Saitama", "関東", ["NACK5"]),
        "JP12": RegionInfo("JP12", "千葉県", "Chiba", "関東", ["CRO", "bayfm"]),
        "JP13": RegionInfo("JP13", "東京都", "Tokyo", "関東", ["TBS", "QRR", "LFR", "INT", "FMT", "FMJ", "JORF"]),
        "JP14": RegionInfo("JP14", "神奈川県", "Kanagawa", "関東", ["YBS", "FMN"]),
        
        # 中部（北から南へ）
        "JP15": RegionInfo("JP15", "新潟県", "Niigata", "中部", ["BSN", "FM-NIIGATA"]),
        "JP16": RegionInfo("JP16", "富山県", "Toyama", "中部", ["KNB"]),
        "JP17": RegionInfo("JP17", "石川県", "Ishikawa", "中部", ["MRO"]),
        "JP18": RegionInfo("JP18", "福井県", "Fukui", "中部", ["FBC"]),
        "JP19": RegionInfo("JP19", "山梨県", "Yamanashi", "中部", ["YBS"]),
        "JP20": RegionInfo("JP20", "長野県", "Nagano", "中部", ["SBC", "FM-NAGANO"]),
        "JP21": RegionInfo("JP21", "岐阜県", "Gifu", "中部", ["GBS"]),
        "JP22": RegionInfo("JP22", "静岡県", "Shizuoka", "中部", ["SBS", "K-MIX"]),
        "JP23": RegionInfo("JP23", "愛知県", "Aichi", "中部", ["CBC", "SF", "ZIP-FM"]),
        
        # 近畿（北から南へ）
        "JP25": RegionInfo("JP25", "滋賀県", "Shiga", "近畿", ["BBC"]),
        "JP26": RegionInfo("JP26", "京都府", "Kyoto", "近畿", ["KBS", "α-STATION"]),
        "JP27": RegionInfo("JP27", "大阪府", "Osaka", "近畿", ["OBC", "MBS", "ABC", "FM-OSAKA", "FM802"]),
        "JP28": RegionInfo("JP28", "兵庫県", "Hyogo", "近畿", ["CRK", "Kiss-FM"]),
        "JP29": RegionInfo("JP29", "奈良県", "Nara", "近畿", ["FMN"]),
        "JP24": RegionInfo("JP24", "三重県", "Mie", "近畿", ["FM-MIE"]),
        "JP30": RegionInfo("JP30", "和歌山県", "Wakayama", "近畿", ["WBS"]),
        
        # 中国（北東から南西へ）
        "JP31": RegionInfo("JP31", "鳥取県", "Tottori", "中国", ["BSS"]),
        "JP32": RegionInfo("JP32", "島根県", "Shimane", "中国", ["BSS"]),
        "JP33": RegionInfo("JP33", "岡山県", "Okayama", "中国", ["RSK", "FM-OKAYAMA"]),
        "JP34": RegionInfo("JP34", "広島県", "Hiroshima", "中国", ["RCC", "HFM"]),
        "JP35": RegionInfo("JP35", "山口県", "Yamaguchi", "中国", ["KRY"]),
        
        # 四国（北東から南西へ）
        "JP37": RegionInfo("JP37", "香川県", "Kagawa", "四国", ["RNC", "FM-KAGAWA"]),
        "JP36": RegionInfo("JP36", "徳島県", "Tokushima", "四国", ["JRT"]),
        "JP38": RegionInfo("JP38", "愛媛県", "Ehime", "四国", ["RNB", "HiTFM"]),
        "JP39": RegionInfo("JP39", "高知県", "Kochi", "四国", ["RKC", "Hi-SIX"]),
        
        # 九州・沖縄（北から南へ）
        "JP40": RegionInfo("JP40", "福岡県", "Fukuoka", "九州・沖縄", ["RKB", "KBC", "FM-FUKUOKA", "LOVEFM"]),
        "JP41": RegionInfo("JP41", "佐賀県", "Saga", "九州・沖縄", ["NBC"]),
        "JP42": RegionInfo("JP42", "長崎県", "Nagasaki", "九州・沖縄", ["NBC", "FM-NAGASAKI"]),
        "JP43": RegionInfo("JP43", "熊本県", "Kumamoto", "九州・沖縄", ["RKK", "FMK"]),
        "JP44": RegionInfo("JP44", "大分県", "Oita", "九州・沖縄", ["OBS", "FM-OITA"]),
        "JP45": RegionInfo("JP45", "宮崎県", "Miyazaki", "九州・沖縄", ["MRT", "JOY-FM"]),
        "JP46": RegionInfo("JP46", "鹿児島県", "Kagoshima", "九州・沖縄", ["MBC", "μFM"]),
        "JP47": RegionInfo("JP47", "沖縄県", "Okinawa", "九州・沖縄", ["ROK"]),
    }
    
    @classmethod
    def get_area_id(cls, prefecture_name: str) -> Optional[str]:
        """都道府県名から地域IDを取得"""
        if not prefecture_name or not prefecture_name.strip():
            return None
        
        # 前後の空白を除去
        prefecture_name = prefecture_name.strip()
        
        # 直接マッピングを確認
        area_id = cls.REGION_MAPPING.get(prefecture_name)
        if area_id:
            return area_id
        
        # 大文字小文字を区別しない検索
        prefecture_lower = prefecture_name.lower()
        area_id = cls.REGION_MAPPING.get(prefecture_lower)
        if area_id:
            return area_id
        
        # 「県」「府」「都」を除いた検索（正確な接尾辞のみ）
        # ただし、基本名＋接尾辞の組み合わせが正しい都道府県名の場合のみ
        valid_combinations = {
            # 正しい都道府県名のマッピング（基本名: 正しい接尾辞）
            "青森": "県", "岩手": "県", "宮城": "県", "秋田": "県", "山形": "県", "福島": "県",
            "茨城": "県", "栃木": "県", "群馬": "県", "埼玉": "県", "千葉": "県", "神奈川": "県",
            "新潟": "県", "富山": "県", "石川": "県", "福井": "県", "山梨": "県", "長野": "県",
            "岐阜": "県", "静岡": "県", "愛知": "県", "三重": "県", "滋賀": "県", "兵庫": "県",
            "奈良": "県", "和歌山": "県", "鳥取": "県", "島根": "県", "岡山": "県", "広島": "県",
            "山口": "県", "徳島": "県", "香川": "県", "愛媛": "県", "高知": "県", "福岡": "県",
            "佐賀": "県", "長崎": "県", "熊本": "県", "大分": "県", "宮崎": "県", "鹿児島": "県",
            "沖縄": "県", "京都": "府", "大阪": "府", "東京": "都"
        }
        
        for suffix in ["県", "府", "都"]:
            if prefecture_name.endswith(suffix):
                base_name = prefecture_name[:-1]
                # 基本名が空文字の場合は無効
                if not base_name:
                    return None
                
                # 正しい組み合わせかチェック
                if base_name in valid_combinations and valid_combinations[base_name] == suffix:
                    area_id = cls.REGION_MAPPING.get(base_name)
                    if area_id:
                        return area_id
                    # 基本名の小文字版でも検索
                    area_id = cls.REGION_MAPPING.get(base_name.lower())
                    if area_id:
                        return area_id
        
        return None
    
    @classmethod
    def get_prefecture_name(cls, area_id: str) -> Optional[str]:
        """地域IDから都道府県名（日本語）を取得"""
        region_info = cls.REGION_INFO.get(area_id)
        return region_info.prefecture_ja if region_info else None
    
    @classmethod
    def get_region_info(cls, area_id: str) -> Optional[RegionInfo]:
        """地域IDから詳細情報を取得"""
        return cls.REGION_INFO.get(area_id)
    
    @classmethod
    def list_all_prefectures(cls) -> Dict[str, str]:
        """全都道府県の日本語名と地域IDのマッピングを取得"""
        return {info.prefecture_ja: area_id for area_id, info in cls.REGION_INFO.items()}
    
    @classmethod
    def search_prefecture(cls, query: str) -> List[Dict[str, str]]:
        """都道府県名の部分検索"""
        results = []
        
        # 空文字または空白のみの場合は空のリストを返す
        if not query or not query.strip():
            return results
        
        query = query.strip()
        query_lower = query.lower()
        
        for area_id, info in cls.REGION_INFO.items():
            # 日本語名での検索
            if query in info.prefecture_ja or query_lower in info.prefecture_en.lower():
                results.append({
                    "area_id": area_id,
                    "prefecture_ja": info.prefecture_ja,
                    "prefecture_en": info.prefecture_en,
                    "region_name": info.region_name
                })
        
        return results
    
    @classmethod
    def validate_area_id(cls, area_id: str) -> bool:
        """地域IDの妥当性を確認"""
        return area_id in cls.REGION_INFO
    
    @classmethod
    def get_default_area_id(cls) -> str:
        """デフォルト地域ID（東京）を取得"""
        return "JP13"
    
    @classmethod
    def get_current_prefecture(cls) -> Optional[str]:
        """現在の都道府県を取得（デフォルト実装）"""
        # 設定から取得する場合の実装
        # 現在はデフォルトで東京を返す
        return "東京"


# 使用例とテスト用関数
def test_region_mapper():
    """RegionMapperのテスト"""
    print("RegionMapper テスト開始")
    
    # 基本的な変換テスト
    test_cases = [
        ("東京", "JP13"),
        ("東京都", "JP13"),
        ("Tokyo", "JP13"),
        ("osaka", "JP27"),
        ("北海道", "JP1"),
        ("沖縄県", "JP47"),
        ("神奈川", "JP14"),
        ("存在しない県", None),
    ]
    
    for prefecture, expected in test_cases:
        result = RegionMapper.get_area_id(prefecture)
        status = "✅" if result == expected else "❌"
        print(f"{status} {prefecture} -> {result} (期待値: {expected})")
    
    # 逆引きテスト
    print(f"\nJP13 -> {RegionMapper.get_prefecture_name('JP13')}")
    print(f"JP27 -> {RegionMapper.get_prefecture_name('JP27')}")
    
    # 検索テスト
    print(f"\n'東京'検索結果: {RegionMapper.search_prefecture('東京')}")
    
    print("RegionMapper テスト完了")


if __name__ == "__main__":
    test_region_mapper()
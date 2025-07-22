"""
Program Selection Screen for RecRadiko Keyboard Navigation UI

Provides program selection interface with keyboard navigation for RecRadiko timefree recording.
Handles program list display, pagination, and program information viewing.

Based on UI_SPECIFICATION.md:
- Program selection with keyboard navigation
- Pagination support for large program lists
- Program information display
- Integration with timefree recording workflow
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import math
from src.ui.screen_base import ScreenBase
from src.program_history import ProgramHistoryManager
from src.program_info import ProgramInfoManager
from src.auth import RadikoAuthenticator


class ProgramSelectScreen(ScreenBase):
    """
    Program selection screen for RecRadiko timefree recording
    
    Provides program selection interface with:
    - Program list display with pagination
    - Keyboard navigation for program selection
    - Program information viewing
    - Integration with timefree recording workflow
    """
    
    def __init__(self):
        """Initialize program selection screen"""
        super().__init__()
        self.set_title("番組選択")
        self.selected_station: Optional[Dict[str, Any]] = None
        self.selected_date: Optional[date] = None
        self.programs: List[Dict[str, Any]] = []
        self.current_page: int = 0
        self.items_per_page: int = 15  # 15番組ずつ表示
        
        # ProgramInfoManagerを使用（番組表API直接アクセス）
        self.program_info_manager: Optional[ProgramInfoManager] = None
        self.authenticator: Optional[RadikoAuthenticator] = None
        self._initialize_managers()
    
    def _initialize_managers(self) -> None:
        """マネージャー初期化"""
        try:
            # Radiko認証
            self.authenticator = RadikoAuthenticator()
            auth_info = self.authenticator.authenticate()
            
            if not auth_info or not auth_info.auth_token:
                self.logger.error("Radiko認証に失敗しました")
                return
            
            # ProgramInfoManager初期化
            self.program_info_manager = ProgramInfoManager(
                area_id=auth_info.area_id,
                authenticator=self.authenticator
            )
            
            self.logger.info(f"ProgramInfoManager初期化完了 - エリア: {auth_info.area_id}")
            
        except Exception as e:
            self.logger.error(f"マネージャー初期化エラー: {e}")
            self.program_info_manager = None
        
    def set_station_and_date(self, station: Dict[str, Any], target_date: date) -> None:
        """
        Set selected station and date, update title
        
        Args:
            station: Selected station dictionary
            target_date: Selected date for program list
        """
        self.selected_station = station
        self.selected_date = target_date
        date_str = target_date.strftime('%Y-%m-%d')
        self.set_title(f"番組選択 - {station['name']} ({date_str})")
        
    def load_programs(self) -> bool:
        """
        Load programs for selected station and date
        
        Returns:
            True if programs loaded successfully, False otherwise
        """
        if not self.selected_station or not self.selected_date:
            error_msg = f"Station or date not set for program loading - station: {self.selected_station}, date: {self.selected_date}"
            self.logger.error(error_msg)
            self.ui_service.display_error("放送局または日付が正しく設定されていません。")
            return False
            
        try:
            # 詳細ログ出力
            self.logger.info(f"Loading programs - Station: {self.selected_station['name']} ({self.selected_station['id']}), Date: {self.selected_date} (type: {type(self.selected_date)})")
            
            self.display_loading_message()
            self.programs = self._fetch_programs_from_api(
                self.selected_station["id"], 
                self.selected_date
            )
            
            if not self.programs:
                error_msg = f"No programs found for {self.selected_station['id']} on {self.selected_date}"
                self.logger.warning(error_msg)
                self.ui_service.display_error(
                    f"番組が見つかりませんでした。\n"
                    f"放送局: {self.selected_station['name']}\n"
                    f"日付: {self.selected_date}\n"
                    f"別の日付を選択してください。"
                )
                return False
                
            self.logger.info(
                f"Successfully loaded {len(self.programs)} programs for {self.selected_station['id']} on {self.selected_date}"
            )
            self.current_page = 0  # Reset to first page
            return True
            
        except Exception as e:
            error_msg = f"Failed to load programs: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.ui_service.display_error(
                f"番組の読み込みでエラーが発生しました：\n{str(e)}\n"
                f"ネットワーク接続またはサーバーの状態を確認してください。"
            )
            return False
            
    def _fetch_programs_from_api(self, station_id: str, target_date: date) -> List[Dict[str, Any]]:
        """
        Fetch programs from RecRadiko API
        
        Args:
            station_id: Station identifier
            target_date: Target date for programs
            
        Returns:
            List of program dictionaries
        """
        try:
            # ProgramInfoManagerが初期化されているか確認
            if not self.program_info_manager:
                self.logger.error("ProgramInfoManagerが初期化されていません")
                return []
            
            self.logger.debug(f"Using ProgramInfoManager for station_id: {station_id}, target_date: {target_date}")
            
            # dateをdatetimeに変換
            target_datetime = datetime.combine(target_date, datetime.min.time())
            self.logger.debug(f"Converted date to datetime: {target_datetime}")
            
            # ProgramInfoManagerから番組表を取得
            self.logger.info(f"Calling fetch_program_guide for station {station_id} on {target_date}")
            program_infos = self.program_info_manager.fetch_program_guide(target_datetime, station_id)
            
            # 深夜番組の処理：当日の深夜番組は前日番組表に表示するため除外
            # 深夜番組（0:00-4:59開始）を除外し、通常番組のみ表示
            regular_programs = []
            midnight_programs = []
            
            for prog in program_infos:
                if prog.is_midnight_program:
                    midnight_programs.append(prog)
                    self.logger.debug(f"Midnight program excluded from today's list: {prog.title} at {prog.start_time}")
                else:
                    regular_programs.append(prog)
            
            # 通常番組のみを使用（深夜番組は除外）
            program_infos = regular_programs
            
            self.logger.info(f"API returned {len(program_infos)} regular programs (excluded {len(midnight_programs)} midnight programs)")
            
            # 過去日の番組表の場合のみ、翌日の深夜番組を末尾に追加
            today = date.today()
            if target_date < today:
                next_day_midnight_programs = self._get_next_day_midnight_programs(station_id, target_date)
                if next_day_midnight_programs:
                    self.logger.info(f"Adding {len(next_day_midnight_programs)} next-day midnight programs to {target_date}'s schedule")
                    program_infos.extend(next_day_midnight_programs)
                    
                    # 通常番組と深夜番組を分けてソート（深夜番組は末尾に配置）
                    regular_programs = [p for p in program_infos if not p.is_midnight_program]
                    midnight_programs = [p for p in program_infos if p.is_midnight_program]
                    
                    # それぞれを時刻順でソート
                    regular_programs.sort(key=lambda x: x.start_time)
                    midnight_programs.sort(key=lambda x: x.start_time)
                    
                    # 通常番組 + 深夜番組の順で結合（深夜番組が末尾に）
                    program_infos = regular_programs + midnight_programs
            else:
                # 今日の番組表の場合は通常番組のみを時系列順でソート
                program_infos.sort(key=lambda x: x.start_time)
                self.logger.info(f"Today's schedule ({target_date}): not adding next-day midnight programs")
            
            if not program_infos:
                self.logger.warning(f"No program info objects returned from API for {station_id} on {target_date}")
                return []
            
            # Convert ProgramInfo objects to dictionary format for UI
            programs = []
            for i, prog in enumerate(program_infos):
                try:
                    # 深夜番組の表示日付処理
                    display_title = prog.title
                    
                    if prog.is_midnight_program:
                        # 深夜番組は前日の日付で表示（ユーザー体験向上）
                        display_date = (prog.start_time.date() - timedelta(days=1)).strftime('%Y-%m-%d')
                        self.logger.debug(f"Midnight program: {prog.title} displayed as {display_date} (actual: {prog.start_time.date()})")
                    else:
                        # 通常番組は実際の放送日で表示
                        display_date = prog.start_time.date().strftime('%Y-%m-%d')
                        self.logger.debug(f"Regular program: {prog.title} on {display_date}")
                    
                    program_dict = {
                        'id': prog.program_id,
                        'title': display_title,
                        'start_time': prog.start_time.strftime('%H:%M'),
                        'end_time': prog.end_time.strftime('%H:%M'),
                        'display_start_time': prog.display_start_time,
                        'display_end_time': prog.display_end_time,
                        'performer': getattr(prog, 'performers', []),
                        'description': getattr(prog, 'description', ''),
                        'station_id': prog.station_id,
                        'station_name': prog.station_name,
                        'display_date': display_date,
                        'is_midnight': prog.is_midnight_program
                    }
                    programs.append(program_dict)
                    
                except Exception as prog_e:
                    self.logger.error(f"Error converting program {i} to dict: {prog_e}")
                    continue
            
            # 深夜番組を含む場合は通常番組＋深夜番組の順序を保持、そうでなければ時刻順でソート
            has_midnight = any(p.get('is_midnight', False) for p in programs)
            if has_midnight:
                # 深夜番組がある場合：通常番組＋深夜番組の順序を保持（既にソート済み）
                pass
            else:
                # 深夜番組がない場合：時刻順でソート
                programs.sort(key=lambda x: x['start_time'])
            
            self.logger.info(f"Successfully converted {len(programs)} programs to dictionary format")
            return programs
            
        except Exception as e:
            self.logger.error(f"Error in _fetch_programs_from_api: {e}", exc_info=True)
            raise  # Re-raise the exception to be handled by calling method
    
    def _get_next_day_midnight_programs(self, station_id: str, target_date: date) -> List[Any]:
        """
        翌日の深夜番組を取得
        前日の番組表末尾に表示するため
        """
        try:
            # 翌日の日付を計算
            next_day = target_date + timedelta(days=1)
            next_day_datetime = datetime.combine(next_day, datetime.min.time())
            
            self.logger.debug(f"Fetching next day midnight programs for {next_day}")
            
            # 翌日の全番組を取得
            next_day_programs = self.program_info_manager.fetch_program_guide(next_day_datetime, station_id)
            
            # 深夜番組のみを抽出
            midnight_programs = [prog for prog in next_day_programs if prog.is_midnight_program]
            
            if midnight_programs:
                self.logger.info(f"Found {len(midnight_programs)} midnight programs for {next_day}")
                for prog in midnight_programs:
                    self.logger.debug(f"Next day midnight program: {prog.title} at {prog.start_time}")
            
            return midnight_programs
            
        except Exception as e:
            self.logger.error(f"Error fetching next day midnight programs: {e}")
            return []
        
    def display_content(self) -> None:
        """Display program selection content"""
        if not self.selected_station or not self.selected_date:
            self.ui_service.display_error(
                "放送局または日付が選択されていません。\n"
                "メインメニューから録音を開始してください。"
            )
            self.ui_service.keyboard_handler.get_key()
            return
            
        if not self.programs:
            self.display_no_programs_message()
            return
            
        station_name = self.selected_station["name"]
        date_str = self.selected_date.strftime('%Y年%m月%d日')
        total_programs = len(self.programs)
        
        print(f"\n放送局: {station_name}")
        print(f"日付: {date_str}")
        print(f"番組数: {total_programs}番組")
        print("=" * 40)
        
        # ページング表示
        total_pages = self.get_total_pages()
        print(f"\n📄 ページ表示 ({self.get_pagination_info()})")
        print("\n番組を選択してください:\n")
        
        # 現在のページの番組を表示
        page_programs = self.get_current_page_programs()
        program_displays = [self.format_program_for_display(prog) for prog in page_programs]
        
        # ページ移動オプションを番組リストに追加
        if total_pages > 1:
            program_displays.append("═══════════════════════")
            
            # 前のページオプション（最初のページでなければ表示）
            if self.current_page > 0:
                program_displays.append("⬅️ 前のページ")
            
            # 次のページオプション（最後のページでなければ表示）
            if self.current_page < total_pages - 1:
                program_displays.append("➡️ 次のページ")
        
        self.ui_service.set_menu_items(program_displays)
        self.ui_service.display_menu_with_highlight()
        
        print(f"\n💡 操作方法: ↑↓キーで選択、Enterで確定")
            
    def run_program_selection_loop(self) -> Optional[Dict[str, Any]]:
        """
        Run program selection interaction loop
        
        Returns:
            Selected program dictionary, or None if cancelled
        """
        if not self.selected_station or not self.selected_date:
            return None
            
        while True:
            self.show()
            
            # メニュー選択を取得
            selected_display = self.ui_service.get_user_selection()
            
            if selected_display is None:
                # Escapeキーまたはキャンセル
                return None
            
            # 特殊なメニュー項目かどうかをチェック
            if selected_display == "➡️ 次のページ":
                # 次のページに移動
                if self.next_page():
                    self.ui_service.display_status(f"ページ {self.current_page + 1} に移動しました")
                else:
                    self.ui_service.display_status("最後のページです")
                continue
                
            elif selected_display == "⬅️ 前のページ":
                # 前のページに移動
                if self.previous_page():
                    self.ui_service.display_status(f"ページ {self.current_page + 1} に移動しました")
                else:
                    self.ui_service.display_status("最初のページです")
                continue
                
            elif selected_display == "═══════════════════════":
                # 区切り線は無視
                continue
                
            elif selected_display in ('h', 'H'):
                # ヘルプ表示（旧キーサポート）
                self.show_help()
                continue
                
            else:
                # 通常の番組選択
                selected_program = self.get_program_by_display_text(selected_display)
                
                if selected_program:
                    return selected_program
                else:
                    # 番組が見つからない場合はスキップ（区切り線や特殊項目の可能性）
                    continue
                
    def format_program_for_display(self, program: Dict[str, Any]) -> str:
        """
        Format program for display
        
        Args:
            program: Program dictionary
            
        Returns:
            Formatted display string
        """
        display_start_time = program.get("display_start_time", program.get("start_time", ""))
        display_end_time = program.get("display_end_time", program.get("end_time", ""))
        title = program.get("title", "")
        
        return f"{display_start_time}-{display_end_time} {title}"
        
    def get_program_by_display_text(self, display_text: str) -> Optional[Dict[str, Any]]:
        """
        Get program by display text
        
        Args:
            display_text: Program display text
            
        Returns:
            Program dictionary or None if not found
        """
        # 特殊なメニュー項目は番組検索から除外
        special_items = [
            "═══════════════════════",
            "➡️ 次のページ",
            "⬅️ 前のページ"
        ]
        
        if display_text in special_items:
            return None
        
        # 現在のページの番組から検索
        search_programs = self.get_current_page_programs()
        
        for program in search_programs:
            if self.format_program_for_display(program) == display_text:
                return program
        return None
        
    def get_current_page_programs(self) -> List[Dict[str, Any]]:
        """
        Get programs for current page
        
        Returns:
            List of programs for current page
        """
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.programs[start_idx:end_idx]
        
    def get_total_pages(self) -> int:
        """
        Get total number of pages
        
        Returns:
            Total number of pages
        """
        if not self.programs:
            return 0
        return math.ceil(len(self.programs) / self.items_per_page)
        
    def next_page(self) -> bool:
        """
        Move to next page
        
        Returns:
            True if moved to next page, False if already at last page
        """
        if self.current_page < self.get_total_pages() - 1:
            self.current_page += 1
            return True
        return False
        
    def previous_page(self) -> bool:
        """
        Move to previous page
        
        Returns:
            True if moved to previous page, False if already at first page
        """
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
        
    def get_pagination_info(self) -> str:
        """
        Get pagination information string
        
        Returns:
            Pagination info string
        """
        if not self.programs:
            return "番組なし"
            
        total_pages = self.get_total_pages()
        current_page_num = self.current_page + 1
        
        start_item = self.current_page * self.items_per_page + 1
        end_item = min((self.current_page + 1) * self.items_per_page, len(self.programs))
        
        return f"ページ {current_page_num}/{total_pages} ({start_item}-{end_item}/{len(self.programs)}件)"
        
    def show_program_info(self, program: Dict[str, Any]) -> None:
        """
        Show detailed program information
        
        Args:
            program: Program dictionary
        """
        print(f"\n番組詳細情報")
        print("=" * 20)
        print(f"番組名: {program.get('title', '')}")
        display_start_time = program.get('display_start_time', program.get('start_time', ''))
        display_end_time = program.get('display_end_time', program.get('end_time', ''))
        print(f"放送時間: {display_start_time}-{display_end_time}")
        
        if 'performer' in program and program['performer']:
            print(f"出演者: {program['performer']}")
            
        if 'description' in program and program['description']:
            print(f"番組内容: {program['description']}")
            
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def handle_shortcut_key(self, key: str) -> bool:
        """
        Handle shortcut keys
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if key was handled, False otherwise
        """
        if key in ('i', 'I'):
            # Show program info for current selection
            current_display = self.ui_service.get_current_item()
            if current_display:
                program = self.get_program_by_display_text(current_display)
                if program:
                    self.show_program_info(program)
            return True
            
        elif key in ('n', 'N'):
            # Next page
            if self.next_page():
                self.ui_service.display_status("次のページに移動しました")
            else:
                self.ui_service.display_status("最後のページです")
            return True
            
        elif key in ('p', 'P'):
            # Previous page
            if self.previous_page():
                self.ui_service.display_status("前のページに移動しました")
            else:
                self.ui_service.display_status("最初のページです")
            return True
            
        elif key in ('r', 'R'):
            # Refresh programs
            success = self.refresh_programs()
            if success:
                self.ui_service.display_status("番組リストを更新しました")
            else:
                self.ui_service.display_error("番組リストの更新に失敗しました")
            return True
            
        elif key in ('h', 'H'):
            # Show help
            self.show_help()
            return True
            
        return False
        
    def show_help(self) -> None:
        """Show help information"""
        print("\n📺 番組選択ヘルプ")
        print("=" * 30)
        print("🎯 基本操作:")
        print("  ↑/↓キー : 番組選択・メニュー移動")
        print("  Enterキー: 選択確定")
        print("  Escキー : 戻る")
        print("  Hキー   : このヘルプ")
        
        print("\n📱 メニュー操作:")
        print("  メニューに表示される項目を↑↓キーで選択:")
        print("  • 番組名 - 録音する番組を選択")
        
        total_pages = self.get_total_pages()
        if total_pages > 1:
            if self.current_page > 0:
                print("  • ⬅️ 前のページ - 前のページに移動")
            if self.current_page < total_pages - 1:
                print("  • ➡️ 次のページ - 次のページに移動")
        
        print("\n💡 表示モード:")
        print(f"  📄 ページ表示 ({self.items_per_page}番組ずつ)")
        print(f"  - 現在 {self.current_page + 1}/{self.get_total_pages()} ページ")
        print("  - メニューで簡単にページ移動")
        
        print("\n🔍 その他:")
        print("  Iキー   : 番組詳細情報")
        print("  Rキー   : 番組リスト更新")
        
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def display_loading_message(self) -> None:
        """Display loading message"""
        print("\n番組情報を読み込み中...")
        print("しばらくお待ちください...")
        
    def display_no_programs_message(self) -> None:
        """Display no programs available message"""
        self.ui_service.display_error(
            "この日付・放送局では番組が見つかりませんでした。\n"
            "日付や放送局を変更してください。"
        )
        self.ui_service.keyboard_handler.get_key()
        
    def validate_program_data(self, program: Dict[str, Any]) -> bool:
        """
        Validate program data
        
        Args:
            program: Program dictionary to validate
            
        Returns:
            True if program data is valid, False otherwise
        """
        required_fields = ['title', 'start_time', 'end_time']
        return all(field in program and program[field] for field in required_fields)
        
    def get_program_count(self) -> int:
        """
        Get number of loaded programs
        
        Returns:
            Number of programs
        """
        return len(self.programs)
        
    def has_programs(self) -> bool:
        """
        Check if programs are loaded
        
        Returns:
            True if programs are loaded, False otherwise
        """
        return len(self.programs) > 0
        
    def refresh_programs(self) -> bool:
        """
        Refresh program list for current station and date
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.selected_station or not self.selected_date:
            return False
            
        return self.load_programs()
        
    def get_current_selection_info(self) -> str:
        """
        Get current selection information for display
        
        Returns:
            Current selection info string
        """
        if not self.selected_station or not self.selected_date:
            return "選択情報なし"
            
        station_name = self.selected_station["name"]
        date_str = self.selected_date.strftime('%Y-%m-%d')
        program_count = len(self.programs)
        
        return f"{station_name} / {date_str} / {program_count}番組"
        
    def filter_programs_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Filter programs by keyword
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching programs
        """
        if not keyword:
            return self.programs
            
        keyword_lower = keyword.lower()
        return [
            program for program in self.programs
            if keyword_lower in program.get('title', '').lower() or
               keyword_lower in program.get('performer', '').lower() or
               keyword_lower in program.get('description', '').lower()
        ]
        
    def get_program_time_range(self) -> str:
        """
        Get time range of all programs
        
        Returns:
            Time range description string
        """
        if not self.programs:
            return "番組なし"
            
        start_times = [prog.get('display_start_time', prog.get('start_time', '')) for prog in self.programs if prog.get('display_start_time') or prog.get('start_time')]
        end_times = [prog.get('display_end_time', prog.get('end_time', '')) for prog in self.programs if prog.get('display_end_time') or prog.get('end_time')]
        
        if start_times and end_times:
            earliest = min(start_times)
            latest = max(end_times)
            return f"{earliest} ～ {latest}"
        else:
            return "時間情報なし"
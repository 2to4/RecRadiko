"""
Search Screen for RecRadiko Keyboard Navigation UI

Provides program search functionality with keyboard navigation for RecRadiko timefree recording.
Supports multiple search methods and result display with pagination.

Based on UI_SPECIFICATION.md:
- Search method selection (title, performer, time, station, date)
- Keyword input handling
- Search result display with pagination
- Selection and navigation
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime, time
from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.program_history import ProgramHistoryManager
from src.program_info import ProgramInfo
from src.auth import RadikoAuthenticator


class SearchScreen(ScreenBase):
    """
    Search screen for program search functionality
    
    Provides comprehensive search capabilities including:
    - Multiple search methods (title, performer, time, station, date)
    - Keyword input with validation
    - Search result display with pagination
    - Selection and navigation
    """
    
    def __init__(self):
        """Initialize search screen"""
        super().__init__()
        self.set_title("番組検索")
        
        # Search methods
        self.search_methods = [
            "番組名で検索",
            "出演者で検索", 
            "時間帯で検索",
            "放送局で絞り込み",
            "日付範囲で絞り込み"
        ]
        
        # Initialize program history manager
        self.program_history_manager = ProgramHistoryManager()
        
        # Pagination settings
        self.page_size = 10
        self.current_page = 0
        
        # Current search results
        self.current_results: List[ProgramInfo] = []
        self.current_query: Optional[str] = None
        
    def display_content(self) -> None:
        """Display search menu content"""
        print("\n番組検索システム")
        print("=" * 40)
        print("\n以下の検索方法から選択してください:\n")
        
        # Set menu items for search methods
        self.ui_service.set_menu_items(self.search_methods)
        
        # Display additional options
        print("\n[99] メインメニューに戻る")
        print("[0] 終了")
        
    def run_search_workflow(self) -> Optional[ProgramInfo]:
        """
        Run complete search workflow
        
        Returns:
            Selected ProgramInfo or None if cancelled
        """
        try:
            self.logger.info("Starting search workflow")
            
            # Display search menu
            self.display_content()
            
            # Get search method selection
            selection = self.ui_service.get_user_selection(
                prompt="検索方法を選択してください (1-5, 99, 0): ",
                valid_range=(0, 5),
                allow_special=[99]
            )
            
            if selection is None or selection == 0:
                self.logger.info("Search workflow cancelled")
                return None
            elif selection == 99:
                self.logger.info("Returning to main menu")
                return None
            
            # Execute selected search method
            search_results = self._execute_search_method(selection - 1)
            
            if not search_results:
                self.ui_service.display_message("検索結果が見つかりませんでした。")
                return None
            
            # Display search results and get selection
            selected_program = self.display_search_results(search_results, self.current_query)
            
            if selected_program:
                self.logger.info(f"Program selected: {selected_program.title}")
                return selected_program
            else:
                self.logger.info("No program selected")
                return None
                
        except Exception as e:
            self.logger.error(f"Search workflow error: {e}")
            self.ui_service.display_error(f"検索でエラーが発生しました: {e}")
            return None
    
    def _execute_search_method(self, method_index: int) -> List[ProgramInfo]:
        """
        Execute selected search method
        
        Args:
            method_index: Index of selected search method
            
        Returns:
            List of found programs
        """
        try:
            if method_index == 0:
                return self.search_by_title()
            elif method_index == 1:
                return self.search_by_performer()
            elif method_index == 2:
                return self.search_by_time_range()
            elif method_index == 3:
                return self.search_by_station()
            elif method_index == 4:
                return self.search_by_date_range()
            else:
                self.logger.error(f"Invalid search method index: {method_index}")
                return []
                
        except Exception as e:
            self.logger.error(f"Search method execution error: {e}")
            self.ui_service.display_error(f"検索実行エラー: {e}")
            return []
    
    def search_by_title(self) -> List[ProgramInfo]:
        """
        Search programs by title
        
        Returns:
            List of matching programs
        """
        try:
            # Get search keyword
            keyword = self.ui_service.get_text_input(
                prompt="番組名のキーワードを入力してください: ",
                allow_empty=False
            )
            
            if not keyword:
                return []
            
            self.current_query = keyword
            self.logger.info(f"Searching by title: {keyword}")
            
            # Execute search
            results = self.program_history_manager.search_programs(keyword)
            
            self.logger.info(f"Found {len(results)} programs")
            return results
            
        except Exception as e:
            self.logger.error(f"Title search error: {e}")
            self.ui_service.display_error(f"番組名検索エラー: {e}")
            return []
    
    def search_by_performer(self) -> List[ProgramInfo]:
        """
        Search programs by performer
        
        Returns:
            List of matching programs
        """
        try:
            # Get performer name
            performer = self.ui_service.get_text_input(
                prompt="出演者名を入力してください: ",
                allow_empty=False
            )
            
            if not performer:
                return []
            
            self.current_query = performer
            self.logger.info(f"Searching by performer: {performer}")
            
            # Execute search (using general search with performer name)
            results = self.program_history_manager.search_programs(performer)
            
            # Filter results to only include programs with matching performers
            filtered_results = []
            for program in results:
                if any(performer.lower() in p.lower() for p in program.performers):
                    filtered_results.append(program)
            
            self.logger.info(f"Found {len(filtered_results)} programs")
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Performer search error: {e}")
            self.ui_service.display_error(f"出演者検索エラー: {e}")
            return []
    
    def search_by_time_range(self) -> List[ProgramInfo]:
        """
        Search programs by time range
        
        Returns:
            List of matching programs
        """
        try:
            # Get start time
            start_time_str = self.ui_service.get_text_input(
                prompt="開始時刻を入力してください (HH:MM): ",
                allow_empty=False
            )
            
            # Get end time
            end_time_str = self.ui_service.get_text_input(
                prompt="終了時刻を入力してください (HH:MM): ",
                allow_empty=False
            )
            
            if not start_time_str or not end_time_str:
                return []
            
            # Parse time strings
            try:
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
            except ValueError:
                self.ui_service.display_error("時刻形式が正しくありません。HH:MM形式で入力してください。")
                return []
            
            self.current_query = f"{start_time_str}-{end_time_str}"
            self.logger.info(f"Searching by time range: {start_time_str} - {end_time_str}")
            
            # Get all recent programs and filter by time
            results = self.program_history_manager.search_programs("")
            
            # Filter by time range
            filtered_results = []
            for program in results:
                program_start = program.start_time.time()
                program_end = program.end_time.time()
                
                # Check if program overlaps with search time range
                if (program_start <= end_time and program_end >= start_time):
                    filtered_results.append(program)
            
            self.logger.info(f"Found {len(filtered_results)} programs")
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Time range search error: {e}")
            self.ui_service.display_error(f"時間帯検索エラー: {e}")
            return []
    
    def search_by_station(self) -> List[ProgramInfo]:
        """
        Search programs by station
        
        Returns:
            List of matching programs
        """
        try:
            # Get available stations
            stations = self._get_available_stations()
            
            if not stations:
                self.ui_service.display_error("利用可能な放送局が見つかりません。")
                return []
            
            # Display station selection
            print("\n放送局を選択してください:")
            station_names = [station["name"] for station in stations]
            self.ui_service.set_menu_items(station_names)
            
            selection = self.ui_service.get_user_selection(
                prompt="放送局を選択してください: ",
                valid_range=(1, len(stations))
            )
            
            if selection is None or selection == 0:
                return []
            
            # Handle string return value from mock
            if isinstance(selection, str):
                # Find station by ID
                selected_station = next((s for s in stations if s["id"] == selection), None)
                if not selected_station:
                    return []
            else:
                selected_station = stations[selection - 1]
            self.current_query = selected_station["name"]
            self.logger.info(f"Searching by station: {selected_station['name']}")
            
            # Search programs for the selected station
            results = self.program_history_manager.search_programs(
                "", 
                station_ids=[selected_station["id"]]
            )
            
            self.logger.info(f"Found {len(results)} programs")
            return results
            
        except Exception as e:
            self.logger.error(f"Station search error: {e}")
            self.ui_service.display_error(f"放送局検索エラー: {e}")
            return []
    
    def search_by_date_range(self) -> List[ProgramInfo]:
        """
        Search programs by date range
        
        Returns:
            List of matching programs
        """
        try:
            # Get start date
            start_date = self.ui_service.get_date_input(
                prompt="開始日付を入力してください (YYYY-MM-DD): "
            )
            
            # Get end date
            end_date = self.ui_service.get_date_input(
                prompt="終了日付を入力してください (YYYY-MM-DD): "
            )
            
            if not start_date or not end_date:
                return []
            
            if start_date > end_date:
                self.ui_service.display_error("開始日付は終了日付より前である必要があります。")
                return []
            
            self.current_query = f"{start_date} - {end_date}"
            self.logger.info(f"Searching by date range: {start_date} - {end_date}")
            
            # Search programs in date range
            results = self.program_history_manager.search_programs(
                "", 
                date_range=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )
            
            self.logger.info(f"Found {len(results)} programs")
            return results
            
        except Exception as e:
            self.logger.error(f"Date range search error: {e}")
            self.ui_service.display_error(f"日付範囲検索エラー: {e}")
            return []
    
    def display_search_results(self, results: List[ProgramInfo], query: Optional[str] = None) -> Optional[ProgramInfo]:
        """
        Display search results with pagination
        
        Args:
            results: List of search results
            query: Search query for display
            
        Returns:
            Selected program or None if cancelled
        """
        try:
            if not results:
                self.ui_service.display_message("検索結果が見つかりませんでした。")
                return None
            
            self.current_results = results
            self.current_page = 0
            
            while True:
                # Display current page
                page_results = self._get_current_page_results()
                
                print(f"\n検索結果: {query or '全番組'}")
                print("=" * 40)
                print(f"見つかった番組: {len(results)}件")
                
                if len(results) > self.page_size:
                    print(f"ページ: {self.current_page + 1}/{self._get_total_pages()}")
                
                print()
                
                # Create display items
                display_items = []
                for i, program in enumerate(page_results):
                    # Format program display
                    duration = program.duration_minutes
                    time_str = f"{program.start_time.strftime('%H:%M')}-{program.end_time.strftime('%H:%M')}"
                    date_str = program.start_time.strftime('%Y-%m-%d')
                    
                    display_text = f"{program.station_name} {date_str} {time_str}\n    {program.title} ({duration}分)"
                    
                    if program.performers:
                        display_text += f"\n    出演: {', '.join(program.performers)}"
                    
                    display_items.append(display_text)
                
                # Set menu items
                self.ui_service.set_menu_items(display_items)
                
                # Add navigation options
                options = []
                if self.current_page > 0:
                    options.append("[88] 前のページ")
                if self.current_page < self._get_total_pages() - 1:
                    options.append("[89] 次のページ")
                
                options.extend(["[77] 新しい検索", "[99] メインメニューに戻る", "[0] 終了"])
                
                print("\n" + " | ".join(options))
                
                # Get user selection
                valid_range = (1, len(page_results))
                special_options = [0, 77, 99]
                
                if self.current_page > 0:
                    special_options.append(88)
                if self.current_page < self._get_total_pages() - 1:
                    special_options.append(89)
                
                selection = self.ui_service.get_user_selection(
                    prompt="選択してください: ",
                    valid_range=valid_range,
                    allow_special=special_options
                )
                
                if selection is None or selection == 0:
                    return None
                elif selection == 77:
                    # New search
                    return self.run_search_workflow()
                elif selection == 99:
                    # Return to main menu
                    return None
                elif selection == 88:
                    # Previous page
                    self.current_page -= 1
                    continue
                elif selection == 89:
                    # Next page
                    self.current_page += 1
                    continue
                else:
                    # Program selection
                    if 1 <= selection <= len(page_results):
                        selected_program = page_results[selection - 1]
                        self.logger.info(f"Program selected: {selected_program.title}")
                        return selected_program
                    else:
                        # Invalid selection
                        self.ui_service.display_error(f"無効な選択です: {selection}")
                        continue
                    
        except Exception as e:
            self.logger.error(f"Search results display error: {e}")
            self.ui_service.display_error(f"検索結果表示エラー: {e}")
            return None
    
    def _get_current_page_results(self) -> List[ProgramInfo]:
        """
        Get results for current page
        
        Returns:
            List of programs for current page
        """
        start_index = self.current_page * self.page_size
        end_index = start_index + self.page_size
        return self.current_results[start_index:end_index]
    
    def _get_total_pages(self) -> int:
        """
        Get total number of pages
        
        Returns:
            Total number of pages
        """
        return (len(self.current_results) + self.page_size - 1) // self.page_size
    
    def _get_available_stations(self) -> List[Dict[str, str]]:
        """
        Get list of available stations
        
        Returns:
            List of station dictionaries
        """
        try:
            # Get stations from program history manager
            # This is a simplified implementation - in real system would get from API
            return [
                {"id": "TBS", "name": "TBSラジオ"},
                {"id": "QRR", "name": "文化放送"},
                {"id": "LFR", "name": "ニッポン放送"},
                {"id": "INT", "name": "InterFM"},
                {"id": "FMT", "name": "TOKYO FM"},
                {"id": "FMJ", "name": "J-WAVE"},
                {"id": "JORF", "name": "ラジオ日本"}
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting available stations: {e}")
            return []
    
    def reset_search_state(self) -> None:
        """Reset search state"""
        self.current_results = []
        self.current_query = None
        self.current_page = 0
        self.logger.debug("Search state reset")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Get search statistics
        
        Returns:
            Dictionary with search statistics
        """
        return {
            "total_results": len(self.current_results),
            "current_page": self.current_page + 1,
            "total_pages": self._get_total_pages(),
            "current_query": self.current_query
        }
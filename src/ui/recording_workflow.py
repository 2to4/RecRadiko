"""
Recording Workflow Integration for RecRadiko Keyboard Navigation UI

Integrates all UI screens to provide complete recording workflow.
Handles the end-to-end process from station selection to recording execution.

Based on UI_SPECIFICATION.md:
- Complete 3-stage recording workflow (Station → Date → Program)
- Integration with existing RecRadiko components
- Error handling and user feedback
- Recording execution with progress display
"""

import logging
from typing import Optional, Dict, Any
from datetime import date
from src.ui.screens import MainMenuScreen, StationSelectScreen, DateSelectScreen, ProgramSelectScreen
from src.ui.menu_manager import MenuManager
from src.ui.services.ui_service import UIService
from src.timefree_recorder import TimeFreeRecorder
from src.region_mapper import RegionMapper


class RecordingWorkflow:
    """
    Complete recording workflow integration
    
    Manages the entire recording process from UI navigation to actual recording.
    Provides seamless integration between keyboard navigation UI and RecRadiko core.
    """
    
    def __init__(self):
        """Initialize recording workflow"""
        self.logger = logging.getLogger(__name__)
        self.ui_service = UIService()
        self.menu_manager = MenuManager()
        self.region_mapper = RegionMapper()
        
        # Initialize screens
        self.main_menu_screen = MainMenuScreen()
        self.station_select_screen = StationSelectScreen()
        self.date_select_screen = DateSelectScreen()
        self.program_select_screen = ProgramSelectScreen()
        
        # Register screens with menu manager
        self._register_screens()
        
        # Current selection state
        self.selected_station: Optional[Dict[str, Any]] = None
        self.selected_date: Optional[date] = None
        self.selected_program: Optional[Dict[str, Any]] = None
        
    def _register_screens(self) -> None:
        """Register all screens with menu manager"""
        self.menu_manager.register_screen("main_menu", self.main_menu_screen)
        self.menu_manager.register_screen("station_select", self.station_select_screen)
        self.menu_manager.register_screen("date_select", self.date_select_screen)
        self.menu_manager.register_screen("program_select", self.program_select_screen)
        
    def start_recording_workflow(self) -> bool:
        """
        Start complete recording workflow
        
        Returns:
            True if recording completed successfully, False if cancelled
        """
        self.logger.info("Starting recording workflow")
        
        try:
            # Step 1: Station Selection
            selected_station = self._run_station_selection()
            if not selected_station:
                self.logger.info("Recording workflow cancelled at station selection")
                return False
                
            self.selected_station = selected_station
            self.logger.info(f"Station selected: {selected_station['name']}")
            
            # Step 2: Date Selection
            selected_date = self._run_date_selection()
            if not selected_date:
                self.logger.info("Recording workflow cancelled at date selection")
                return False
                
            self.selected_date = selected_date
            self.logger.info(f"Date selected: {selected_date}")
            
            # Step 3: Program Selection
            selected_program = self._run_program_selection()
            if not selected_program:
                self.logger.info("Recording workflow cancelled at program selection")
                return False
                
            self.selected_program = selected_program
            self.logger.info(f"Program selected: {selected_program['title']}")
            
            # Step 4: Recording Execution
            return self._execute_recording()
            
        except Exception as e:
            self.logger.error(f"Recording workflow error: {e}")
            self.ui_service.display_error(f"録音ワークフローでエラーが発生しました: {e}")
            return False
            
    def _run_station_selection(self) -> Optional[Dict[str, Any]]:
        """
        Run station selection workflow
        
        Returns:
            Selected station dictionary or None if cancelled
        """
        # Load stations for current area
        current_area = self._get_current_area()
        if not self.station_select_screen.load_stations(current_area):
            self.ui_service.display_error("放送局の読み込みに失敗しました")
            return None
            
        # Run station selection loop
        return self.station_select_screen.run_station_selection_loop()
        
    def _run_date_selection(self) -> Optional[date]:
        """
        Run date selection workflow
        
        Returns:
            Selected date or None if cancelled
        """
        if not self.selected_station:
            return None
            
        # Set station for date selection screen
        self.date_select_screen.set_station(self.selected_station)
        
        # Run date selection loop
        return self.date_select_screen.run_date_selection_loop()
        
    def _run_program_selection(self) -> Optional[Dict[str, Any]]:
        """
        Run program selection workflow
        
        Returns:
            Selected program dictionary or None if cancelled
        """
        if not self.selected_station or not self.selected_date:
            return None
            
        # Set station and date for program selection screen
        self.program_select_screen.set_station_and_date(self.selected_station, self.selected_date)
        
        # Load programs
        if not self.program_select_screen.load_programs():
            self.ui_service.display_error("番組の読み込みに失敗しました")
            return None
            
        # Run program selection loop
        return self.program_select_screen.run_program_selection_loop()
        
    def _execute_recording(self) -> bool:
        """
        Execute the actual recording
        
        Returns:
            True if recording completed successfully, False otherwise
        """
        if not all([self.selected_station, self.selected_date, self.selected_program]):
            self.logger.error("Missing selection data for recording")
            return False
            
        # Display recording confirmation
        if not self._confirm_recording():
            self.logger.info("Recording cancelled by user")
            return False
            
        try:
            # Initialize TimeFreeRecorder
            recorder = TimeFreeRecorder()
            
            # Display recording start message
            self._display_recording_start()
            
            # Execute recording
            success = recorder.record_program(
                station_id=self.selected_station["id"],
                target_date=self.selected_date,
                program_info=self.selected_program
            )
            
            if success:
                self._display_recording_success()
                return True
            else:
                self._display_recording_failure()
                return False
                
        except Exception as e:
            self.logger.error(f"Recording execution error: {e}")
            self.ui_service.display_error(f"録音中にエラーが発生しました: {e}")
            return False
            
    def _confirm_recording(self) -> bool:
        """
        Show recording confirmation dialog
        
        Returns:
            True if user confirms, False otherwise
        """
        station_name = self.selected_station["name"]
        date_str = self.selected_date.strftime('%Y年%m月%d日')
        program_title = self.selected_program["title"]
        start_time = self.selected_program.get("start_time", "")
        end_time = self.selected_program.get("end_time", "")
        
        print(f"\n録音確認")
        print("=" * 30)
        print(f"放送局: {station_name}")
        print(f"日付: {date_str}")
        print(f"番組: {program_title}")
        print(f"時間: {start_time}-{end_time}")
        print("\nこの内容で録音を開始しますか？")
        
        return self.ui_service.confirm_action("録音を開始する")
        
    def _display_recording_start(self) -> None:
        """Display recording start message"""
        print(f"\n🎙️  録音を開始しています...")
        print(f"番組: {self.selected_program['title']}")
        print(f"放送局: {self.selected_station['name']}")
        print(f"日付: {self.selected_date.strftime('%Y-%m-%d')}")
        print("\n録音中です。しばらくお待ちください...")
        
    def _display_recording_success(self) -> None:
        """Display recording success message"""
        print(f"\n✅ 録音が完了しました！")
        print(f"番組: {self.selected_program['title']}")
        print("録音ファイルは出力ディレクトリに保存されました。")
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def _display_recording_failure(self) -> None:
        """Display recording failure message"""
        print(f"\n❌ 録音に失敗しました")
        print(f"番組: {self.selected_program['title']}")
        print("詳細はログファイルを確認してください。")
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def _get_current_area(self) -> str:
        """
        Get current area ID
        
        Returns:
            Current area ID
        """
        # Try to get from region mapper default or use Tokyo as fallback
        try:
            # Get from settings or use default
            return "JP13"  # Tokyo as default
        except Exception:
            return "JP13"
            
    def reset_selection(self) -> None:
        """Reset all selection state"""
        self.selected_station = None
        self.selected_date = None
        self.selected_program = None
        self.logger.debug("Selection state reset")
        
    def get_selection_summary(self) -> str:
        """
        Get summary of current selections
        
        Returns:
            Summary string of current selections
        """
        parts = []
        
        if self.selected_station:
            parts.append(f"放送局: {self.selected_station['name']}")
            
        if self.selected_date:
            parts.append(f"日付: {self.selected_date.strftime('%Y-%m-%d')}")
            
        if self.selected_program:
            parts.append(f"番組: {self.selected_program['title']}")
            
        return " / ".join(parts) if parts else "選択なし"
        
    def has_complete_selection(self) -> bool:
        """
        Check if all required selections are complete
        
        Returns:
            True if all selections are complete, False otherwise
        """
        return all([self.selected_station, self.selected_date, self.selected_program])
        
    def get_recording_info(self) -> Optional[Dict[str, Any]]:
        """
        Get recording information dictionary
        
        Returns:
            Recording info dictionary or None if incomplete
        """
        if not self.has_complete_selection():
            return None
            
        return {
            "station": self.selected_station,
            "date": self.selected_date,
            "program": self.selected_program,
            "summary": self.get_selection_summary()
        }
        
    def validate_selections(self) -> bool:
        """
        Validate all selections
        
        Returns:
            True if all selections are valid, False otherwise
        """
        # Validate station
        if not self.selected_station or "id" not in self.selected_station:
            return False
            
        # Validate date
        if not self.selected_date:
            return False
            
        # Validate program
        if not self.selected_program or "title" not in self.selected_program:
            return False
            
        return True
        
    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.menu_manager.shutdown()
            self.reset_selection()
            self.logger.debug("Recording workflow cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
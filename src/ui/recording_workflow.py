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
from src.program_info import ProgramInfo
from src.auth import RadikoAuthenticator


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
        
        # TimeFreeRecorderの初期化（RadikoAuthenticatorを含む）
        self.authenticator = RadikoAuthenticator()
        self.timefree_recorder = TimeFreeRecorder(self.authenticator)
        
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
        
            
    async def start_recording_workflow(self) -> bool:
        """
        Start complete recording workflow
        
        Returns:
            True if recording completed successfully, False if cancelled
        """
        self.logger.info("Starting recording workflow")
        
        try:
            # Pre-flight checks
            if not self._validate_workflow_requirements():
                self.logger.error("Workflow requirements validation failed")
                return False
            
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
            
            # Step 4: Recording Execution (async)
            return await self._execute_recording()
            
        except KeyboardInterrupt:
            self._handle_workflow_interruption()
            return False
            
        except Exception as e:
            self.logger.error(f"Recording workflow error: {e}")
            self.ui_service.display_error(f"録音ワークフローでエラーが発生しました: {e}")
            self._display_error_summary()
            return False
            
    def _run_station_selection(self) -> Optional[Dict[str, Any]]:
        """
        Run station selection workflow
        
        Returns:
            Selected station dictionary or None if cancelled
        """
        try:
            # Load stations for current area
            current_area = self._get_current_area()
            self.logger.info(f"Loading stations for area: {current_area}")
            
            if not self.station_select_screen.load_stations(current_area):
                error_msg = f"放送局の読み込みに失敗しました (地域: {current_area})"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                self.ui_service.display_error("地域設定を確認してください。")
                return None
            
            # Run station selection loop
            self.logger.info("Starting station selection loop")
            selected_station = self.station_select_screen.run_station_selection_loop()
            
            if selected_station:
                self.logger.info(f"Station selected: {selected_station['name']} ({selected_station['id']})")
            else:
                self.logger.info("Station selection cancelled by user")
                
            return selected_station
            
        except Exception as e:
            error_msg = f"放送局選択でエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            return None
        
    def _run_date_selection(self) -> Optional[date]:
        """
        Run date selection workflow
        
        Returns:
            Selected date or None if cancelled
        """
        try:
            if not self.selected_station:
                error_msg = "日付選択の前に放送局を選択してください"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                return None
            
            # Set station for date selection screen
            self.logger.info(f"Setting station for date selection: {self.selected_station['name']}")
            self.date_select_screen.set_station(self.selected_station)
            
            # Run date selection loop
            self.logger.info("Starting date selection loop")
            selected_date = self.date_select_screen.run_date_selection_loop()
            
            if selected_date:
                self.logger.info(f"Date selected: {selected_date}")
            else:
                self.logger.info("Date selection cancelled by user")
                
            return selected_date
            
        except Exception as e:
            error_msg = f"日付選択でエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            return None
        
    def _run_program_selection(self) -> Optional[Dict[str, Any]]:
        """
        Run program selection workflow
        
        Returns:
            Selected program dictionary or None if cancelled
        """
        try:
            if not self.selected_station or not self.selected_date:
                error_msg = "番組選択の前に放送局と日付を選択してください"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                return None
            
            # Set station and date for program selection screen
            self.logger.info(f"Setting station and date for program selection: {self.selected_station['name']}, {self.selected_date}")
            self.program_select_screen.set_station_and_date(self.selected_station, self.selected_date)
            
            # Load programs
            self.logger.info("Loading programs from API")
            if not self.program_select_screen.load_programs():
                error_msg = f"番組の読み込みに失敗しました (放送局: {self.selected_station['name']}, 日付: {self.selected_date})"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                self.ui_service.display_error("別の日付を選択するか、しばらく時間をおいてから再試行してください。")
                return None
            
            # Run program selection loop
            self.logger.info("Starting program selection loop")
            selected_program = self.program_select_screen.run_program_selection_loop()
            
            if selected_program:
                self.logger.info(f"Program selected: {selected_program.get('title', 'Unknown')}")
            else:
                self.logger.info("Program selection cancelled by user")
                
            return selected_program
            
        except Exception as e:
            error_msg = f"番組選択でエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            return None
        
    async def _execute_recording(self) -> bool:
        """
        Execute the actual recording
        
        Returns:
            True if recording completed successfully, False otherwise
        """
        try:
            # Validate selection data
            if not all([self.selected_station, self.selected_date, self.selected_program]):
                missing_items = []
                if not self.selected_station:
                    missing_items.append("放送局")
                if not self.selected_date:
                    missing_items.append("日付")
                if not self.selected_program:
                    missing_items.append("番組")
                
                error_msg = f"録音実行に必要な選択が不足しています: {', '.join(missing_items)}"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                return False
            
            # Display recording confirmation
            if not self._confirm_recording():
                self.logger.info("Recording cancelled by user")
                return False
            
            # Create ProgramInfo object from selected program
            self.logger.info("Creating program info from selection")
            program_info = self._create_program_info()
            
            if not program_info:
                error_msg = "番組情報の作成に失敗しました"
                self.logger.error(error_msg)
                self.ui_service.display_error(error_msg)
                self.ui_service.display_error("番組の時間情報が正しくない可能性があります。")
                return False
            
            # Generate output filename
            output_filename = self._generate_output_filename()
            self.logger.info(f"Generated output filename: {output_filename}")
            
            # Display recording start message
            self._display_recording_start()
            
            # Execute recording (async)
            self.logger.info("Starting TimeFreeRecorder recording")
            recording_result = await self.timefree_recorder.record_program(
                program_info,
                output_filename
            )
            
            if recording_result.success:
                self.logger.info(f"Recording completed successfully: {output_filename}")
                self._display_recording_success(recording_result)
                return True
            else:
                self.logger.error(f"Recording failed: {recording_result.error_messages}")
                self._display_recording_failure(recording_result)
                return False
                
        except ImportError as e:
            error_msg = f"必要なモジュールのインポートに失敗しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            return False
            
        except PermissionError as e:
            error_msg = f"ファイルの書き込み権限がありません: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            self.ui_service.display_error("出力ディレクトリの権限を確認してください。")
            return False
            
        except ConnectionError as e:
            error_msg = f"ネットワーク接続エラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            self.ui_service.display_error("インターネット接続を確認してください。")
            return False
            
        except Exception as e:
            error_msg = f"録音中に予期しないエラーが発生しました: {e}"
            self.logger.error(error_msg)
            self.ui_service.display_error(error_msg)
            self.ui_service.display_error("詳細はログファイルを確認してください。")
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
        
    def _display_recording_success(self, recording_result) -> None:
        """Display recording success message"""
        print(f"\n✅ 録音が完了しました！")
        print(f"番組: {self.selected_program['title']}")
        print(f"出力ファイル: {recording_result.output_path}")
        print(f"ファイルサイズ: {recording_result.file_size_bytes / 1024 / 1024:.1f}MB")
        print(f"録音時間: {recording_result.recording_duration_seconds:.1f}秒")
        print(f"セグメント数: {recording_result.total_segments}")
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def _display_recording_failure(self, recording_result) -> None:
        """Display recording failure message"""
        print(f"\n❌ 録音に失敗しました")
        print(f"番組: {self.selected_program['title']}")
        if recording_result.error_messages:
            print(f"エラー: {', '.join(recording_result.error_messages)}")
        print("詳細はログファイルを確認してください。")
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def _get_current_area(self) -> str:
        """
        Get current area ID
        
        Returns:
            Current area ID
        """
        try:
            # Try to get from region mapper
            current_prefecture = self.region_mapper.get_current_prefecture()
            if current_prefecture:
                area_id = self.region_mapper.get_area_id(current_prefecture)
                if area_id:
                    return area_id
            
            # Fallback to Tokyo
            self.logger.warning("Using Tokyo as fallback area")
            return "JP13"
            
        except Exception as e:
            self.logger.error(f"Error getting current area: {e}")
            return "JP13"
            
    def reset_selection(self) -> None:
        """Reset all selection state"""
        self.selected_station = None
        self.selected_date = None
        self.selected_program = None
        self.logger.debug("Selection state reset")
        
    def reset_workflow_state(self) -> None:
        """Reset workflow state (alias for reset_selection)"""
        self.reset_selection()
        
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
        
    def is_workflow_complete(self) -> bool:
        """
        Check if workflow is complete (alias for has_complete_selection)
        
        Returns:
            True if workflow is complete, False otherwise
        """
        return self.has_complete_selection()
        
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
        
    def get_workflow_state(self) -> Dict[str, Any]:
        """
        Get workflow state dictionary
        
        Returns:
            Dictionary containing workflow state
        """
        return {
            "station": self.selected_station,
            "date": self.selected_date,
            "program": self.selected_program
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
        
    def _create_program_info(self) -> Optional[ProgramInfo]:
        """
        Create ProgramInfo object from selected program
        
        Returns:
            ProgramInfo object or None if failed
        """
        if not self.selected_program or not self.selected_station:
            return None
            
        try:
            from datetime import datetime
            
            # Parse datetime strings to datetime objects
            start_time_str = self.selected_program.get("start_time")
            end_time_str = self.selected_program.get("end_time")
            
            # Convert time strings to datetime objects
            # Assuming format: "HH:MM" or "YYYY-MM-DD HH:MM:SS"
            if start_time_str and end_time_str:
                # If only time is provided, combine with selected date
                if len(start_time_str) <= 5:  # "HH:MM" format
                    start_datetime = datetime.combine(
                        self.selected_date, 
                        datetime.strptime(start_time_str, "%H:%M").time()
                    )
                    end_datetime = datetime.combine(
                        self.selected_date, 
                        datetime.strptime(end_time_str, "%H:%M").time()
                    )
                else:
                    # Full datetime format
                    start_datetime = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    end_datetime = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            else:
                self.logger.error("Invalid time format in program data")
                return None
            
            program_info = ProgramInfo(
                program_id=self.selected_program.get("id", f"{self.selected_station['id']}_{self.selected_date}_{start_time_str}"),
                station_id=self.selected_station["id"],
                station_name=self.selected_station["name"],
                title=self.selected_program.get("title"),
                start_time=start_datetime,
                end_time=end_datetime,
                performers=self.selected_program.get("performer", ""),
                description=self.selected_program.get("description", ""),
                is_timefree_available=True  # タイムフリー専用システムなので常にTrue
            )
            
            return program_info
            
        except Exception as e:
            self.logger.error(f"Failed to create program info: {e}")
            return None
            
    def _generate_output_filename(self) -> str:
        """
        Generate output filename for recording (fixed to Desktop folder)
        
        Returns:
            Full output file path string
        """
        import os
        from pathlib import Path
        
        # デスクトップフォルダ固定
        desktop_path = Path.home() / "Desktop" / "RecRadiko"
        
        # ディレクトリが存在しない場合は作成
        desktop_path.mkdir(parents=True, exist_ok=True)
        
        station_id = self.selected_station["id"]
        date_str = self.selected_date.strftime("%Y%m%d")
        program_title = self.selected_program.get("title", "unknown")
        start_time = self.selected_program.get("start_time", "0000")
        
        # Remove invalid characters from filename
        safe_title = "".join(c for c in program_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(" ", "_")
        
        filename = f"{station_id}_{date_str}_{start_time}_{safe_title}.mp3"
        full_path = desktop_path / filename
        
        return str(full_path)
        
    def _validate_workflow_requirements(self) -> bool:
        """
        Validate that all required components are available
        
        Returns:
            True if all requirements are met, False otherwise
        """
        try:
            # Check if FFmpeg is available
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode != 0:
                self.logger.error("FFmpeg is not available")
                self.ui_service.display_error("FFmpegがインストールされていません。")
                self.ui_service.display_error("FFmpegをインストールしてから再試行してください。")
                return False
            
            # Check internet connection
            import urllib.request
            try:
                urllib.request.urlopen('https://radiko.jp', timeout=10)
            except Exception as e:
                self.logger.error(f"Internet connection test failed: {e}")
                self.ui_service.display_error("インターネット接続が必要です。")
                self.ui_service.display_error("ネットワーク接続を確認してください。")
                return False
            
            # Check if output directory is writable
            import tempfile
            import os
            try:
                with tempfile.NamedTemporaryFile(delete=True) as tmp:
                    tmp.write(b'test')
                    tmp.flush()
                    os.path.dirname(tmp.name)
            except Exception as e:
                self.logger.error(f"Output directory write test failed: {e}")
                self.ui_service.display_error("出力ディレクトリに書き込み権限がありません。")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Requirements validation error: {e}")
            self.ui_service.display_error(f"システム検証エラー: {e}")
            return False
    
    def _handle_workflow_interruption(self) -> None:
        """
        Handle workflow interruption (Ctrl+C)
        """
        try:
            self.logger.info("Workflow interrupted by user")
            print("\n\nℹ️  録音ワークフローを中断しました")
            print("進行中の録音がある場合は、部分的に保存されている可能性があります。")
            
            # Reset workflow state
            self.reset_selection()
            
        except Exception as e:
            self.logger.error(f"Error handling workflow interruption: {e}")
    
    def _display_error_summary(self) -> None:
        """
        Display error summary and troubleshooting tips
        """
        print("\n\n🔧 トラブルシューティング")
        print("=" * 40)
        print("録音が失敗した場合の確認項目:")
        print("1. インターネット接続が安定しているか")
        print("2. FFmpegがインストールされているか")
        print("3. 出力ディレクトリに書き込み権限があるか")
        print("4. 選択した番組がタイムフリー対応しているか")
        print("5. システムの日時が正しく設定されているか")
        print("\n詳細なログは recradiko.log ファイルを確認してください。")
        print("\n任意のキーを押して続行...")
        
        try:
            self.ui_service.keyboard_handler.get_key()
        except Exception:
            pass
    
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
        
    def run_sync(self) -> bool:
        """
        Run workflow synchronously using asyncio
        
        Returns:
            True if recording completed successfully, False otherwise
        """
        import asyncio
        
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async recording workflow
            return loop.run_until_complete(self.start_recording_workflow())
            
        except Exception as e:
            self.logger.error(f"Sync workflow execution error: {e}")
            return False
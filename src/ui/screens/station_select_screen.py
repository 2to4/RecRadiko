"""
Station Selection Screen for RecRadiko Keyboard Navigation UI

Provides station selection interface with keyboard navigation for RecRadiko timefree recording.
Integrates with existing ProgramInfo to fetch available stations.

Based on UI_SPECIFICATION.md:
- Station selection with keyboard navigation
- Area-based station filtering
- Integration with existing station data
- Navigation to date selection
"""

import logging
from typing import Optional, List, Dict, Any
from src.ui.screen_base import ScreenBase
from src.program_info import ProgramInfoManager
from src.region_mapper import RegionMapper


class StationSelectScreen(ScreenBase):
    """
    Station selection screen for RecRadiko application
    
    Provides station selection interface with:
    - Area-based station list loading
    - Keyboard navigation for station selection
    - Integration with existing ProgramInfo system
    - Navigation flow to date selection
    """
    
    def __init__(self):
        """Initialize station selection screen"""
        super().__init__()
        self.set_title("放送局選択")
        self.stations: List[Dict[str, Any]] = []
        self.current_area: Optional[str] = None
        self.region_mapper = RegionMapper()
        
    def load_stations(self, area_id: str) -> bool:
        """
        Load stations for specified area
        
        Args:
            area_id: Area identifier (e.g., "JP13" for Tokyo)
            
        Returns:
            True if stations loaded successfully, False otherwise
        """
        try:
            self.display_loading_message()
            self.stations = self._fetch_stations_from_api(area_id)
            self.current_area = area_id
            
            if not self.stations:
                self.logger.warning(f"No stations found for area {area_id}")
                return False
                
            self.logger.info(f"Loaded {len(self.stations)} stations for area {area_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load stations for area {area_id}: {e}")
            return False
            
    def _fetch_stations_from_api(self, area_id: str) -> List[Dict[str, Any]]:
        """
        Fetch stations from RecRadiko API
        
        Args:
            area_id: Area identifier
            
        Returns:
            List of station dictionaries
        """
        program_info_manager = ProgramInfoManager()
        return program_info_manager.get_stations()
        
    def display_content(self) -> None:
        """Display station selection content"""
        if not self.stations:
            self.display_no_stations_message()
            return
            
        area_name = self.region_mapper.get_prefecture_name(self.current_area) or self.current_area
        print(f"\n地域: {area_name}")
        print(f"利用可能な放送局: {len(self.stations)}局")
        print("=" * 40)
        print("\n放送局を選択してください:\n")
        
        # Create station display names
        station_names = [station["name"] for station in self.stations]
        
        self.ui_service.set_menu_items(station_names)
        self.ui_service.display_menu_with_highlight()
        
    def run_station_selection_loop(self) -> Optional[Dict[str, Any]]:
        """
        Run station selection interaction loop
        
        Returns:
            Selected station dictionary, or None if cancelled
        """
        while True:
            self.show()
            
            selected_name = self.ui_service.get_user_selection()
            
            if selected_name is None:
                # User cancelled (Escape key)
                return None
                
            # Find selected station
            selected_station = self.get_station_by_name(selected_name)
            
            if selected_station:
                return selected_station
            else:
                self.ui_service.display_error(f"放送局が見つかりません: {selected_name}")
                
    def get_station_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get station by name
        
        Args:
            name: Station name
            
        Returns:
            Station dictionary or None if not found
        """
        for station in self.stations:
            if station["name"] == name:
                return station
        return None
        
    def format_station_display_name(self, station: Dict[str, Any]) -> str:
        """
        Format station name for display
        
        Args:
            station: Station dictionary
            
        Returns:
            Formatted display name
        """
        return f"{station['name']} ({station['id']})"
        
    def refresh_stations(self) -> bool:
        """
        Refresh station list for current area
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.current_area:
            return False
            
        return self.load_stations(self.current_area)
        
    def show_station_info(self, station: Dict[str, Any]) -> None:
        """
        Show detailed station information
        
        Args:
            station: Station dictionary
        """
        print(f"\n放送局情報")
        print("=" * 20)
        print(f"名前: {station['name']}")
        print(f"ID: {station['id']}")
        if 'logo' in station and station['logo']:
            print(f"ロゴ: {station['logo']}")
        print("\n任意のキーを押して続行...")
        self.ui_service.keyboard_handler.get_key()
        
    def change_area(self) -> bool:
        """
        Change current area
        
        Returns:
            True if area changed successfully, False otherwise
        """
        area_options = self.get_area_options()
        
        print("\n地域を選択してください:")
        self.ui_service.set_menu_items(area_options)
        selected_area_name = self.ui_service.get_user_selection()
        
        if selected_area_name is None:
            return False
            
        # Convert area name to area ID
        area_id = self.region_mapper.get_area_id(selected_area_name)
        
        if area_id:
            return self.load_stations(area_id)
        else:
            self.ui_service.display_error(f"地域IDが見つかりません: {selected_area_name}")
            return False
            
    def get_area_options(self) -> List[str]:
        """
        Get available area options
        
        Returns:
            List of area names
        """
        # Get prefecture names from region mapper
        prefectures_dict = self.region_mapper.list_all_prefectures()
        return list(prefectures_dict.keys())
        
    def display_loading_message(self) -> None:
        """Display loading message"""
        print("\n放送局情報を読み込み中...")
        print("しばらくお待ちください...")
        
    def display_no_stations_message(self) -> None:
        """Display no stations available message"""
        self.ui_service.display_error(
            "この地域では利用可能な放送局が見つかりませんでした。\n"
            "地域設定を確認してください。"
        )
        self.ui_service.keyboard_handler.get_key()
        
    def handle_shortcut_key(self, key: str) -> bool:
        """
        Handle shortcut keys
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if key was handled, False otherwise
        """
        if key in ('r', 'R'):
            # Refresh stations
            success = self.refresh_stations()
            if success:
                self.ui_service.display_status("放送局リストを更新しました")
            else:
                self.ui_service.display_error("放送局リストの更新に失敗しました")
            return True
            
        elif key in ('a', 'A'):
            # Change area
            success = self.change_area()
            if success:
                self.ui_service.display_status("地域を変更しました")
            return True
            
        elif key in ('i', 'I'):
            # Show station info for current selection
            current_name = self.ui_service.get_current_item()
            if current_name:
                station = self.get_station_by_name(current_name)
                if station:
                    self.show_station_info(station)
            return True
            
        return False
        
    def get_current_area_name(self) -> str:
        """
        Get current area name for display
        
        Returns:
            Current area name or "未設定" if not set
        """
        if not self.current_area:
            return "未設定"
            
        area_name = self.region_mapper.get_prefecture_name(self.current_area)
        return area_name or self.current_area
        
    def validate_station_data(self, station: Dict[str, Any]) -> bool:
        """
        Validate station data
        
        Args:
            station: Station dictionary to validate
            
        Returns:
            True if station data is valid, False otherwise
        """
        required_fields = ['id', 'name']
        return all(field in station and station[field] for field in required_fields)
        
    def filter_stations_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Filter stations by keyword
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching stations
        """
        if not keyword:
            return self.stations
            
        keyword_lower = keyword.lower()
        return [
            station for station in self.stations
            if keyword_lower in station['name'].lower() or 
               keyword_lower in station['id'].lower()
        ]
        
    def get_station_count(self) -> int:
        """
        Get number of loaded stations
        
        Returns:
            Number of stations
        """
        return len(self.stations)
        
    def has_stations(self) -> bool:
        """
        Check if stations are loaded
        
        Returns:
            True if stations are loaded, False otherwise
        """
        return len(self.stations) > 0
"""
Unit tests for folder parser
"""

import pytest
from app.utils.folder_parser import parse_folder_name, normalize_folder_name, get_safe_folder_name


class TestFolderParser:
    """Test folder name parsing"""
    
    def test_parse_valid_folder_name(self):
        """Test parsing valid folder name"""
        folder_name = "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2026-01-02 00:30"
        assert league == "PL 25_26"
        assert match_name == "Crystal Palace - Fulham"
        assert original == "02.01.26 00:30"
    
    def test_parse_folder_with_epl(self):
        """Test parsing folder with EPL league"""
        folder_name = "15.12.25 14:30 EPL 24_25 Manchester United - Liverpool"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2025-12-15 14:30"
        assert league == "EPL 24_25"
        assert match_name == "Manchester United - Liverpool"
    
    def test_parse_folder_with_multiword_league(self):
        """Test parsing folder with multi-word league"""
        folder_name = "01.06.26 20:00 La Liga 25_26 Barcelona - Real Madrid"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2026-06-01 20:00"
        assert league == "La Liga 25_26"
        assert match_name == "Barcelona - Real Madrid"
    
    def test_parse_invalid_folder_name(self):
        """Test parsing invalid folder name"""
        folder_name = "Invalid Folder Name"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time is None
        assert league is None
        assert match_name is None
        assert original is None
    
    def test_parse_empty_folder_name(self):
        """Test parsing empty folder name"""
        folder_name = ""
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time is None
        assert league is None
        assert match_name is None
    
    def test_parse_folder_without_time(self):
        """Test parsing folder without time"""
        folder_name = "PL 25_26 Crystal Palace - Fulham"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time is None
    
    def test_parse_windows_safe_folder_with_dash(self):
        """Test parsing Windows-safe folder name with '-' instead of ':'"""
        # Windows replaces ':' with '-' in folder names
        folder_name = "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2026-01-02 00:30"
        assert league == "PL 25_26"
        assert match_name == "Crystal Palace - Fulham"
        assert original == "02.01.26 00:30"
    
    def test_parse_windows_safe_folder_without_separator(self):
        """Test parsing Windows-safe folder name without time separator"""
        # Windows sometimes removes ':' completely
        folder_name = "02.01.26 0030 PL 25_26 Crystal Palace - Fulham"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2026-01-02 00:30"
        assert league == "PL 25_26"
        assert match_name == "Crystal Palace - Fulham"
        assert original == "02.01.26 00:30"
    
    def test_parse_windows_safe_folder_with_underscore(self):
        """Test parsing Windows-safe folder name with '_' instead of ':'"""
        # Windows sometimes replaces ':' with '_' in folder names
        folder_name = "02.01.26 00_30 PL 25_26 Crystal Palace - Fulham"
        start_time, league, match_name, original = parse_folder_name(folder_name)
        
        assert start_time == "2026-01-02 00:30"
        assert league == "PL 25_26"
        assert match_name == "Crystal Palace - Fulham"
        assert original == "02.01.26 00:30"
    
    def test_normalize_folder_name_with_dash(self):
        """Test normalize function with dash"""
        folder_name = "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"
        normalized = normalize_folder_name(folder_name)
        
        assert normalized == "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
    
    def test_normalize_folder_name_without_separator(self):
        """Test normalize function without separator"""
        folder_name = "02.01.26 0030 PL 25_26 Crystal Palace - Fulham"
        normalized = normalize_folder_name(folder_name)
        
        assert normalized == "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
    
    def test_normalize_folder_name_with_colon(self):
        """Test normalize function with colon (unchanged)"""
        folder_name = "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
        normalized = normalize_folder_name(folder_name)
        
        assert normalized == folder_name
    
    def test_normalize_folder_name_with_underscore(self):
        """Test normalize function with underscore"""
        folder_name = "02.01.26 00_30 PL 25_26 Crystal Palace - Fulham"
        normalized = normalize_folder_name(folder_name)
        
        assert normalized == "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
    
    def test_get_safe_folder_name(self):
        """Test get safe folder name for Windows"""
        folder_name = "02.01.26 00:30 PL 25_26 Crystal Palace - Fulham"
        safe_name = get_safe_folder_name(folder_name)
        
        assert safe_name == "02.01.26 00-30 PL 25_26 Crystal Palace - Fulham"

"""
Folder Parser: Extract match_name, league, and start_time from folder names
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def get_safe_folder_name(folder_name: str) -> str:
    """
    Convert folder name to Windows-safe format by replacing ':' with '-' in time part.
    
    This should be used when creating folders on Windows file system.
    
    Examples:
        "02.01.26 00:30 PL 25_26 ..." -> "02.01.26 00-30 PL 25_26 ..."
    """
    # Pattern to match time part: "dd.mm.yy hh:mm"
    pattern = r'^(\d{2}\.\d{2}\.\d{2})\s+(\d{2}):(\d{2})'
    match = re.match(pattern, folder_name)
    
    if match:
        date_part = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        remaining = folder_name[match.end():]
        # Replace ':' with '-' for Windows compatibility
        safe_name = f"{date_part} {hour}-{minute}{remaining}"
        return safe_name
    
    return folder_name


def normalize_folder_name(folder_name: str) -> str:
    """
    Normalize folder name to handle Windows file system restrictions.
    On Windows, ':' is replaced with '-' or '_' or removed.
    This function restores ':' in the time part for parsing.
    
    Examples:
        "02.01.26 00-30 PL 25_26 ..." -> "02.01.26 00:30 PL 25_26 ..."
        "02.01.26 00_30 PL 25_26 ..." -> "02.01.26 00:30 PL 25_26 ..."
        "02.01.26 0030 PL 25_26 ..." -> "02.01.26 00:30 PL 25_26 ..."
        "02.01.26 00:30 PL 25_26 ..." -> "02.01.26 00:30 PL 25_26 ..." (unchanged)
    """
    # Pattern to match: "dd.mm.yy hh:mm" or "dd.mm.yy hh-mm" or "dd.mm.yy hh_mm" or "dd.mm.yy hhmm"
    # We need to restore ':' in the time part
    pattern = r'^(\d{2}\.\d{2}\.\d{2})\s+(\d{2})[-:_]?(\d{2})'
    match = re.match(pattern, folder_name)
    
    if match:
        date_part = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        remaining = folder_name[match.end():]
        # Restore normalized format with ':'
        normalized = f"{date_part} {hour}:{minute}{remaining}"
        return normalized
    
    return folder_name


def parse_folder_name(folder_name: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse folder name to extract:
    - start_time: datetime string in format "yyyy-mm-dd hh:mm"
    - league: league name (e.g., "PL 25_26")
    - match_name: match name (e.g., "Crystal Palace - Fulham")
    - original_start_time: original format "dd.mm.yy hh:mm"
    
    Handles multiple formats:
    - "02.01.26 00:30 PL 25_26 ..." (original with :)
    - "02.01.26 00-30 PL 25_26 ..." (Windows safe with -)
    - "02.01.26 00_30 PL 25_26 ..." (Windows safe with _)
    - "02.01.26 0030 PL 25_26 ..." (Windows safe without separator)
    
    Returns: (start_time, league, match_name, original_start_time)
    """
    try:
        # Normalize folder name first (restore ':' in time part)
        normalized_name = normalize_folder_name(folder_name)
        
        # Pattern: "dd.mm.yy hh:mm LEAGUE match_name"
        # Now we can safely match with ':' since we normalized it
        datetime_pattern = r'^(\d{2})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2})'
        match = re.match(datetime_pattern, normalized_name)
        
        if not match:
            return None, None, None, None
        
        day, month, year_short, hour, minute = match.groups()
        year = int("20" + year_short)
        dt = datetime(year, int(month), int(day), int(hour), int(minute))
        
        formatted_start_time = dt.strftime("%Y-%m-%d %H:%M")
        original_start_time = f"{day}.{month}.{year_short} {hour}:{minute}"
        
        # Use normalized_name for remaining part to ensure correct parsing
        remaining = normalized_name[match.end():].strip()
        
        # Find league pattern
        league_patterns = [
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+\s+\d{2}_\d{2})',  # "La Liga 25_26"
            r'^([A-Z]{2,}\s+\d{2}_\d{2})',  # "PL 25_26"
            r'^([A-Z]{2,}\s+\d{4})',  # "PL 2025"
            r'^([A-Z]{2,})',  # "PL"
        ]
        
        league = None
        match_name = remaining
        
        for pattern in league_patterns:
            league_match = re.match(pattern, remaining)
            if league_match:
                league = league_match.group(1).strip()
                match_name = remaining[league_match.end():].strip()
                break
        
        # Heuristic fallback
        if not league:
            parts = remaining.split(' ')
            dash_index = remaining.find(' - ')
            if dash_index > 0:
                potential_league_parts = []
                for i, part in enumerate(parts):
                    if ' - ' in ' '.join(parts[:i+1]):
                        break
                    potential_league_parts.append(part)
                    if re.match(r'\d{2}_\d{2}', part):
                        break
                    if len(potential_league_parts) >= 3:
                        break
                
                if potential_league_parts:
                    if len(potential_league_parts) > 1 and re.match(r'\d{2}_\d{2}', potential_league_parts[-1]):
                        league = ' '.join(potential_league_parts)
                        match_name = ' '.join(parts[len(potential_league_parts):])
                    elif len(potential_league_parts) <= 2:
                        league = ' '.join(potential_league_parts)
                        match_name = ' '.join(parts[len(potential_league_parts):])
                    else:
                        league = ' '.join(potential_league_parts[:2])
                        match_name = ' '.join(parts[2:])
            else:
                if len(parts) >= 2:
                    league = ' '.join(parts[:2])
                    match_name = ' '.join(parts[2:])
                elif len(parts) == 1:
                    league = parts[0]
                    match_name = ""
        
        if match_name:
            match_name = match_name.strip()
        
        return formatted_start_time, league, match_name, original_start_time
        
    except Exception as e:
        return None, None, None, None

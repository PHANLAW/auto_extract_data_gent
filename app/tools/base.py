"""
Base Tool Interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, description: str):
        """
        Initialize tool
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> Tuple[Any, Optional[str]]:
        """
        Execute the tool
        
        Args:
            **kwargs: Tool-specific parameters
        
        Returns:
            Tuple of (result, error_message)
            If successful: (result, None)
            If error: (None, error_message)
        """
        pass
    
    def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Validate tool inputs
        
        Args:
            **kwargs: Tool-specific parameters
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def get_schema(self) -> Dict:
        """
        Get tool schema for API documentation
        
        Returns:
            Dictionary describing tool parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {}
        }

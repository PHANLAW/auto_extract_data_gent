"""
Tool Manager: Manage and register all tools
"""

from typing import Dict, List, Optional
from app.tools.base import BaseTool
from app.core.logging_config import logger


class ToolManager:
    """Manage all available tools"""
    
    def __init__(self):
        """Initialize tool manager"""
        self._tools: Dict[str, BaseTool] = {}
    
    def register_tool(self, tool: BaseTool):
        """
        Register a tool
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """
        List all registered tool names
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_schemas(self) -> Dict[str, Dict]:
        """
        Get schemas for all tools
        
        Returns:
            Dictionary mapping tool names to their schemas
        """
        return {name: tool.get_schema() for name, tool in self._tools.items()}
    
    def execute_tool(self, tool_name: str, **kwargs) -> tuple:
        """
        Execute a tool
        
        Args:
            tool_name: Name of the tool
            **kwargs: Tool-specific parameters
        
        Returns:
            Tuple of (result, error_message)
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return None, f"Tool not found: {tool_name}"
        
        return tool.execute(**kwargs)


# Global tool manager instance
tool_manager = ToolManager()

"""
Prompt Loader: Load prompts from YAML files
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from app.core.logging_config import logger


class PromptLoader:
    """Load and manage prompts from YAML files"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize prompt loader
        
        Args:
            prompts_dir: Directory containing YAML prompt files
        """
        self.prompts_dir = Path(prompts_dir)
        self._prompts_cache: Dict[str, Dict] = {}
    
    def load_prompt(self, prompt_name: str) -> Optional[Dict]:
        """
        Load prompt from YAML file
        
        Args:
            prompt_name: Name of the prompt file (without .yaml extension)
        
        Returns:
            Dictionary containing prompt configuration
        """
        if prompt_name in self._prompts_cache:
            return self._prompts_cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.yaml"
        
        if not prompt_file.exists():
            logger.error(f"Prompt file not found: {prompt_file}")
            return None
        
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_config = yaml.safe_load(f)
            
            self._prompts_cache[prompt_name] = prompt_config
            logger.info(f"Loaded prompt: {prompt_name}")
            return prompt_config
            
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_name}: {e}")
            return None
    
    def get_prompt_text(self, prompt_name: str) -> Optional[str]:
        """Get prompt text from YAML file"""
        config = self.load_prompt(prompt_name)
        if config:
            return config.get("prompt", "")
        return None
    
    def get_model_config(self, prompt_name: str) -> Dict:
        """Get model configuration from YAML file"""
        config = self.load_prompt(prompt_name)
        if config:
            return config.get("model_config", {})
        return {}
    
    def reload_prompt(self, prompt_name: str) -> Optional[Dict]:
        """Reload a specific prompt (clear cache and reload)"""
        if prompt_name in self._prompts_cache:
            del self._prompts_cache[prompt_name]
        return self.load_prompt(prompt_name)
    
    def reload_all(self):
        """Reload all prompts"""
        self._prompts_cache.clear()


# Global prompt loader instance
prompt_loader = PromptLoader()

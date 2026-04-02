"""
Unit tests for Prompt Loader
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open
from app.core.prompt_loader import PromptLoader


class TestPromptLoader:
    """Test Prompt Loader"""
    
    def test_load_prompt_success(self, temp_dir):
        """Test loading prompt successfully"""
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "test_prompt.yaml"
        prompt_data = {
            "name": "test_prompt",
            "prompt": "Test prompt text",
            "model_config": {
                "max_tokens": 300,
                "temperature": 0.1
            }
        }
        
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.dump(prompt_data, f)
        
        loader = PromptLoader(prompts_dir=str(prompts_dir))
        config = loader.load_prompt("test_prompt")
        
        assert config is not None
        assert config["name"] == "test_prompt"
        assert config["prompt"] == "Test prompt text"
    
    def test_load_prompt_not_found(self):
        """Test loading non-existent prompt"""
        loader = PromptLoader(prompts_dir="nonexistent")
        config = loader.load_prompt("nonexistent_prompt")
        
        assert config is None
    
    def test_get_prompt_text(self, temp_dir):
        """Test getting prompt text"""
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "test.yaml"
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.dump({"prompt": "Test text"}, f)
        
        loader = PromptLoader(prompts_dir=str(prompts_dir))
        text = loader.get_prompt_text("test")
        
        assert text == "Test text"
    
    def test_get_model_config(self, temp_dir):
        """Test getting model config"""
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "test.yaml"
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.dump({"model_config": {"max_tokens": 500}}, f)
        
        loader = PromptLoader(prompts_dir=str(prompts_dir))
        config = loader.get_model_config("test")
        
        assert config["max_tokens"] == 500
    
    def test_reload_prompt(self, temp_dir):
        """Test reloading prompt"""
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "test.yaml"
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.dump({"prompt": "Original"}, f)
        
        loader = PromptLoader(prompts_dir=str(prompts_dir))
        loader.load_prompt("test")
        
        # Update file
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.dump({"prompt": "Updated"}, f)
        
        # Reload
        config = loader.reload_prompt("test")
        assert config["prompt"] == "Updated"

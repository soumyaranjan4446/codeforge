"""Centralized configuration loader."""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-coder"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen2.5-coder-32b-instruct"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # Embeddings
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "bug_resolutions"

    # Sandbox
    sandbox_timeout: int = 15
    max_healing_loops: int = 5
    human_escalation_webhook: str = ""


# --- Typed YAML Config Models ---
class SwarmCfg(BaseModel):
    max_healing_loops: int = 5
    sandbox_timeout_sec: int = 15
    escalation: dict[str, Any] = Field(default_factory=dict)

class LLMCfg(BaseModel):
    temperature_coder: float = 0.2
    temperature_tester: float = 0.4
    temperature_fixer: float = 0.3
    temperature_adversarial: float = 0.7
    max_tokens: int = 4096

class MemoryCfg(BaseModel):
    top_k: int = 3
    min_score: float = 0.55

class ASTDiffCfg(BaseModel):
    trivial_change_threshold: float = 0.15

class PatchEffCfg(BaseModel):
    max_lines_per_fix: int = 40

class SycophancyCfg(BaseModel):
    test_only_change_threshold: float = 0.7

class MetricsCfg(BaseModel):
    ast_diff: ASTDiffCfg = Field(default_factory=ASTDiffCfg)
    patch_efficiency: PatchEffCfg = Field(default_factory=PatchEffCfg)
    sycophancy: SycophancyCfg = Field(default_factory=SycophancyCfg)

class YAMLConfig(BaseModel):
    swarm: SwarmCfg = Field(default_factory=SwarmCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    memory: MemoryCfg = Field(default_factory=MemoryCfg)
    metrics: MetricsCfg = Field(default_factory=MetricsCfg)


@lru_cache
def get_settings() -> Settings:
    return Settings()

@lru_cache
def get_yaml_config() -> YAMLConfig:
    path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    if not path.exists():
        return YAMLConfig()
    raw = yaml.safe_load(path.read_text())
    
    def _expand(obj: Any) -> Any:
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        if isinstance(obj, dict):
            return {k: _expand(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_expand(v) for v in obj]
        return obj
        
    return YAMLConfig(**_expand(raw))
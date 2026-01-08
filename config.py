from pydantic import BaseModel, Field
from enum import Enum


class LLMType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    COHERE = "cohere"
    DEEPSEEK = "deepseek"

class LLMModel(Enum):
    LLAMA3 = "llama3"
    LLAMA2 = "llama2"
    MISTRAL = "mistral"


class LLMConfig(BaseModel):
    llm_type: LLMType
    llm_model: LLMModel
    temperature: float = 0.2
    base_url: str = "http://127.0.0.1:11434"
    api_key: str | None = None


class SwarmConfig(BaseModel):
    llm_config: LLMConfig
    population_size: int


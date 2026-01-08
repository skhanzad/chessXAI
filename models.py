from pydantic import BaseModel, Field
from enum import Enum
from langchain_ollama import ChatOllama

class LLMModel(Enum):
    LLAMA2 = "llama2"
    LLAMA3 = "llama3"
    MISTRAL = "mistral"

class LLMConfig(BaseModel):
    model: LLMModel  = Field(default=LLMModel.LLAMA2)
    temperature: float = 0.2
    base_url: str = "http://127.0.0.1:11434"
    api_key: str | None = None

class LLM:

    def __init__(self, config: LLMConfig):
        self.llm = ChatOllama(model=config.model.value, 
        temperature=config.temperature, base_url=config.base_url, api_key=config.api_key)

    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content
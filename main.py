from models import LLM, LLMConfig
from models import LLMModel

config = LLMConfig(model=LLMModel.LLAMA2, temperature=0.2, base_url="http://127.0.0.1:11434", api_key=None)

llm = LLM(config)

print(llm.invoke("Hello, how are you?"))
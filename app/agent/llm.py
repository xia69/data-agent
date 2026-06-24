import sys

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

llm = init_chat_model(
    model=app_config.llm.model_name,
    model_provider="openai",
    api_key=app_config.llm.api_key,
    base_url=app_config.llm.base_url,
    temperature=0.0,  # 0=确定性，每次结果一致；越高越随机
)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8")
    response = llm.invoke("你好，你是谁")
    print(response.content)

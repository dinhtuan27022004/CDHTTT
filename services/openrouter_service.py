"""
services/openrouter_service.py – LangChain ChatOpenAI qua OpenRouter
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "openrouter/auto")


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    """
    Trả về LangChain ChatOpenAI trỏ đến OpenRouter.
    Dùng trong LCEL chain.
    """
    return ChatOpenAI(
        model=CHAT_MODEL,
        temperature=temperature,
        openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openai_api_base="https://openrouter.ai/api/v1",
    )


def chat_completion(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Compatibility wrapper – gọi LLM với danh sách messages dict.
    Dùng khi cần gọi trực tiếp ngoài chain.
    """
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    lc_messages = []
    for m in messages:
        role, content = m["role"], m["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        else:
            lc_messages.append(AIMessage(content=content))

    llm = get_llm(temperature=temperature)
    response = llm.invoke(lc_messages)
    return response.content

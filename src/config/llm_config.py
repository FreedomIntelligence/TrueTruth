import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    Get configured LLM instance for main agent tasks.

    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", "gpt-4"),
        temperature=temperature
    )


def get_fast_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    Get a faster/cheaper LLM instance for classification tasks (Judge, Scheduling).

    Falls back to the main LLM if FAST_LLM_MODEL is not set.
    Configure via FAST_LLM_MODEL env var (e.g. claude-sonnet-4-6, gpt-4o-mini).

    Args:
        temperature: Sampling temperature

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("FAST_LLM_MODEL", os.getenv("LLM_MODEL", "gpt-4")),
        temperature=temperature
    )

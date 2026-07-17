import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    use_real_llm: bool
    groq_api_key: str | None
    groq_model: str


def parse_boolean(value: str | None) -> bool:
    if value is None:
        return False

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_settings() -> Settings:
    return Settings(
        use_real_llm=parse_boolean(
            os.getenv("USE_REAL_LLM")
        ),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv(
            "GROQ_MODEL",
            "llama-3.1-8b-instant",
        ),
    )


def require_groq_api_key(
    settings: Settings,
) -> str:
    api_key = settings.groq_api_key

    if api_key is None or not api_key.strip():
        raise RuntimeError(
            "GROQ_API_KEY is required when "
            "USE_REAL_LLM=true"
        )

    return api_key
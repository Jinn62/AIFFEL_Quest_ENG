"""Runtime settings kept separate from application logic."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuration read once when the server starts."""

    google_oauth_client_id: str | None
    translator_model_id: str
    huggingface_token: str | None


def get_settings() -> Settings:
    return Settings(
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID") or None,
        translator_model_id=os.getenv(
            "TRANSLATOR_MODEL_ID", "facebook/nllb-200-distilled-600M"
        ),
        huggingface_token=os.getenv("HF_TOKEN") or None,
    )

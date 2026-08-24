"""Stable API contracts, independent of the model selected later."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

LanguageCode = Literal["ko", "en", "zh", "ja"]


class TranslationRequest(BaseModel):
    """A request to translate one short piece of text."""

    text: str = Field(..., min_length=1, max_length=1_000)
    source_language: LanguageCode
    target_language: LanguageCode

    @field_validator("text")
    @classmethod
    def reject_whitespace_only_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must contain at least one non-whitespace character")
        return cleaned

    @model_validator(mode="after")
    def require_different_languages(self) -> "TranslationRequest":
        if self.source_language == self.target_language:
            raise ValueError("source_language and target_language must be different")
        return self


class TranslationResponse(BaseModel):
    """The model output returned to API clients and Streamlit."""

    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    model_id: str
    elapsed_ms: float = Field(..., ge=0)


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    model_loaded: bool
    model_id: str | None = None

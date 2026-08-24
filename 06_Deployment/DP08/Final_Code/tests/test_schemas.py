import pytest
from pydantic import ValidationError

from app.schemas import TranslationRequest


def test_translation_request_accepts_supported_language_pair() -> None:
    request = TranslationRequest(
        text="안녕하세요",
        source_language="ko",
        target_language="en",
    )

    assert request.text == "안녕하세요"


def test_translation_request_accepts_japanese_and_simplified_chinese() -> None:
    request = TranslationRequest(
        text="こんにちは",
        source_language="ja",
        target_language="zh",
    )

    assert request.target_language == "zh"


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "   ", "source_language": "ko", "target_language": "en"},
        {"text": "hello", "source_language": "en", "target_language": "en"},
        {"text": "hello", "source_language": "fr", "target_language": "en"},
    ],
)
def test_translation_request_rejects_invalid_input(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        TranslationRequest(**payload)

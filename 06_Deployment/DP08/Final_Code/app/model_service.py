"""NLLB model adapter, isolated from the API and UI layers."""

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.config import Settings
from app.schemas import LanguageCode, TranslationResponse


class ModelInferenceError(RuntimeError):
    """Raised when the loaded model cannot produce a usable translation."""


NLLB_LANGUAGE_CODES = {
    "ko": "kor_Hang",
    "en": "eng_Latn",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
}


class Translator(Protocol):
    """Minimal interface that every future model adapter must implement."""

    @property
    def model_id(self) -> str: ...

    def translate(
        self,
        text: str,
        source_language: LanguageCode,
        target_language: LanguageCode,
    ) -> TranslationResponse: ...


@dataclass
class NLLBTranslator:
    """Korean-English adapter for NLLB-200 sequence-to-sequence translation."""

    tokenizer: Any
    model: Any
    _model_id: str

    @property
    def model_id(self) -> str:
        return self._model_id

    def translate(
        self,
        text: str,
        source_language: LanguageCode,
        target_language: LanguageCode,
    ) -> TranslationResponse:
        """Translate text by setting NLLB's source and target language tokens."""

        import torch

        self.tokenizer.src_lang = NLLB_LANGUAGE_CODES[source_language]
        target_language_code = NLLB_LANGUAGE_CODES[target_language]
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(target_language_code),
                max_new_tokens=256,
            )

        translated_text = self.tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
        )[0].strip()
        if not translated_text:
            raise ModelInferenceError("The model returned an empty translation.")

        return TranslationResponse(
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            model_id=self.model_id,
            elapsed_ms=0,
        )


def load_translator(settings: Settings) -> Translator:
    """Load the selected NLLB model once during FastAPI startup."""

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer_kwargs: dict[str, Any] = {}
    model_kwargs: dict[str, Any] = {}
    if settings.huggingface_token:
        tokenizer_kwargs["token"] = settings.huggingface_token
        model_kwargs["token"] = settings.huggingface_token

    if torch.cuda.is_available():
        model_kwargs.update(device_map="auto", dtype=torch.float16)
    else:
        model_kwargs["dtype"] = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        settings.translator_model_id,
        **tokenizer_kwargs,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        settings.translator_model_id,
        **model_kwargs,
    )
    if not torch.cuda.is_available():
        model.to("cpu")
    model.eval()

    return NLLBTranslator(
        tokenizer=tokenizer,
        model=model,
        _model_id=settings.translator_model_id,
    )


def timed_translation(
    translator: Translator,
    text: str,
    source_language: LanguageCode,
    target_language: LanguageCode,
) -> TranslationResponse:
    """Run synchronous model inference and attach wall-clock latency."""

    started_at = perf_counter()
    result = translator.translate(text, source_language, target_language)
    return result.model_copy(update={"elapsed_ms": round((perf_counter() - started_at) * 1_000, 2)})

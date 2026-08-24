import torch

from app.model_service import NLLBTranslator


class FakeInputs(dict):
    def to(self, device: str) -> "FakeInputs":
        self.device = device
        return self


class FakeTokenizer:
    def __init__(self) -> None:
        self.src_lang = None
        self.text = None

    def __call__(self, text, **kwargs) -> FakeInputs:
        self.text = text
        return FakeInputs(input_ids=torch.tensor([[1, 2, 3]]))

    def convert_tokens_to_ids(self, language_code: str) -> int:
        return {"eng_Latn": 10, "kor_Hang": 20}[language_code]

    def batch_decode(self, token_ids, **kwargs) -> list[str]:
        return ["Hello, world!"]


class FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        self.kwargs = kwargs
        return [[1, 2, 3, 4, 5]]


def test_nllb_adapter_sets_source_and_target_language_tokens() -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    translator = NLLBTranslator(
        tokenizer=tokenizer,
        model=model,
        _model_id="facebook/nllb-200-distilled-600M",
    )

    result = translator.translate("안녕하세요", "ko", "en")

    assert tokenizer.src_lang == "kor_Hang"
    assert tokenizer.text == "안녕하세요"
    assert model.kwargs["forced_bos_token_id"] == 10
    assert result.translated_text == "Hello, world!"

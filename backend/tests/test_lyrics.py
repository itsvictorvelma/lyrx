import pytest

from app.contracts import LyricDraft, LyricLine
from app.errors import DomainError
from app.lyrics import draft_from_model, hiragana_for_lines


def test_a_blank_layer_is_rejected() -> None:
    with pytest.raises(DomainError) as error:
        draft_from_model(
            {
                "title": "Ame",
                "artist": "Example",
                "lines": [
                    {
                        "originalText": "雨",
                        "readingHiragana": "   ",
                        "pronunciationRomaji": "ame",
                        "translationEnglish": "rain",
                    }
                ],
            }
        )

    assert error.value.code == "generation_invalid"


def test_hiragana_must_stay_on_the_saved_lines() -> None:
    stored = [
        LyricLine(
            id="ame-0",
            index=0,
            originalText="雨",
            readingHiragana="",
            pronunciationRomaji="ame",
            translationEnglish="rain",
        )
    ]
    matched = LyricDraft.model_validate(
        {
            "title": "Ame",
            "artist": "Example",
            "lines": [
                {
                    "originalText": "雨",
                    "readingHiragana": "あめ",
                    "pronunciationRomaji": "ame",
                    "translationEnglish": "rain",
                }
            ],
        }
    )

    assert hiragana_for_lines(stored, matched) == ["あめ"]

    shifted = matched.model_copy(deep=True)
    shifted.lines[0].originalText = "空"
    with pytest.raises(DomainError) as error:
        hiragana_for_lines(stored, shifted)

    assert error.value.code == "generation_invalid"


def test_an_empty_line_list_is_rejected() -> None:
    with pytest.raises(DomainError) as error:
        draft_from_model({"title": "Ame", "artist": "Example", "lines": []})

    assert error.value.code == "generation_invalid"

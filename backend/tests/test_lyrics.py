import pytest

from app.errors import DomainError
from app.lyrics import draft_from_model


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


def test_an_empty_line_list_is_rejected() -> None:
    with pytest.raises(DomainError) as error:
        draft_from_model({"title": "Ame", "artist": "Example", "lines": []})

    assert error.value.code == "generation_invalid"

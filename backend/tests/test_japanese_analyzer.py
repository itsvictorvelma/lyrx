"""Tests for the analyzer wrapper: words, tags, and readings from the real dictionary.

Spec 003 "Readings" and plan.md items 5 and 7 and "Two analyzer details". Invented lines only.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from lyrx.japanese_analyzer import Word, analyze

SOURCE_FOLDER = Path(__file__).resolve().parents[1] / "src" / "lyrx"


def described(words: list[Word]) -> list[tuple[str, str, bool, str | None]]:
    return [(w.surface, w.part_of_speech, w.conjunctive, w.reading) for w in words]


# Words, parts of speech, and readings (AC-38)


def test_ac38_line_is_cut_into_words_with_part_of_speech_and_reading() -> None:
    assert described(analyze("君の声が")) == [
        ("君", "代名詞", False, "キミ"),
        ("の", "助詞", False, "\u30ce"),
        ("声", "名詞", False, "コエ"),
        ("が", "助詞", False, "ガ"),
    ]


def test_ac38_reading_is_the_kana_field_as_written() -> None:
    words = analyze("遠くひびく")

    assert [w.surface for w in words] == ["遠く", "ひびく"]
    assert words[0].reading == "トオク"


def test_ac45_reading_is_never_the_pronunciation() -> None:
    """UniDic's pronunciation of 東京 is トーキョー; only the kana field is read."""
    assert analyze("東京")[0].reading == "トウキョウ"


def test_ac47_particles_are_tagged_as_particles() -> None:
    assert [(w.surface, w.part_of_speech) for w in analyze("君は空へ")] == [
        ("君", "代名詞"),
        ("は", "助詞"),
        ("空", "名詞"),
        ("へ", "助詞"),
    ]


def test_ac48_tooth_is_tagged_as_a_noun_read_ha() -> None:
    words = analyze("歯が")

    assert (words[0].surface, words[0].part_of_speech, words[0].reading) == ("歯", "名詞", "ハ")


# Conjunctive particles (plan.md settled question 5)


def test_conjunctive_particle_te_is_marked_conjunctive() -> None:
    assert described(analyze("聞いて")) == [
        ("聞い", "動詞", False, "キイ"),
        ("て", "助詞", True, "テ"),
    ]


def test_conjunctive_particle_de_is_marked_and_case_particles_are_not() -> None:
    conjunctive = {w.surface: w.conjunctive for w in analyze("そらへとんでゆく")}

    assert conjunctive == {"そら": False, "へ": False, "とん": False, "で": True, "ゆく": False}


# Latin letters and digits (AC-42, plan.md item 7)


def test_ac42_latin_and_digit_words_have_no_reading() -> None:
    assert analyze("Oh")[0].reading is None
    assert analyze("2人で")[0].reading is None


def test_ac42_counter_after_a_digit_is_a_suffix_with_its_own_reading() -> None:
    assert described(analyze("2人で"))[:2] == [
        ("2", "名詞", False, None),
        ("人", "接尾辞", False, "ニン"),
    ]


# Full-width digits (AC-42, plan.md "Two analyzer details")


def test_ac42_full_width_digit_is_analyzed_as_a_digit_but_keeps_its_written_form() -> None:
    """２人 alone is one dictionary word read フタリ, which would lose the digit."""
    words = analyze("２人で")

    assert [w.surface for w in words] == ["\uff12", "人", "で"]
    assert words[0].reading is None
    assert words[1].reading == "ニン"


def test_ac42_every_full_width_digit_keeps_its_written_form() -> None:
    run = "０１２３４５６７８９人"

    assert "".join(w.surface for w in analyze(run)) == run
    assert all("0" not in w.surface for w in analyze(run))


@pytest.mark.parametrize(
    "run",
    [
        "君の声が",
        "遠くひびく",
        "２人で",
        "ココロがひかる",
        "「君は」",
        "空、青い",
        "そらへとんでゆく",
    ],
)
def test_ac40_written_forms_join_back_into_the_run(run: str) -> None:
    assert "".join(w.surface for w in analyze(run)) == run


def test_empty_run_gives_no_words() -> None:
    assert analyze("") == []


# One shared tagger behind a lock (plan.md "Two analyzer details")


def test_concurrent_calls_give_the_same_words_as_one_at_a_time() -> None:
    runs = ["君の声が", "遠くひびく", "君は空へ", "聞いて", "２人で", "そらへとんでゆく"] * 20
    expected = [described(analyze(run)) for run in runs]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda run: described(analyze(run)), runs))

    assert results == expected


def test_only_the_analyzer_module_imports_fugashi() -> None:
    importers = sorted(
        path.name
        for path in SOURCE_FOLDER.glob("*.py")
        if "import fugashi" in path.read_text(encoding="utf-8")
        or "from fugashi" in path.read_text(encoding="utf-8")
    )

    assert importers == ["japanese_analyzer.py"]

"""Tests for turning one line into its hiragana, readingVerified, and its particles は and へ.

Spec 003 "Readings" (AC-38 to AC-45) and plan.md settled question 5 and "Two analyzer details".
The real analyzer covers common invented lines; the fake analyzer covers dictionary edge cases.
"""

import pytest
from fake_analyzer import (
    AUXILIARY_VERB,
    PRONOUN,
    SUFFIX,
    SYMBOL,
    VERB,
    FakeAnalyzer,
    noun,
    particle,
    symbol,
    word,
)

from lyrx.hiragana import read_line
from lyrx.kana import to_hiragana

# U+20B9F, a kanji outside the Basic Multilingual Plane that the fake dictionary does not know.
UNKNOWN_KANJI = "\U00020b9f"
UNKNOWN_BMP_KANJI = "鷽"


def assert_well_spaced(hiragana: str) -> None:
    assert hiragana == hiragana.strip(" ")
    assert "  " not in hiragana


# Real analyzer (AC-38 to AC-42)


def test_ac38_kanji_words_get_the_dictionary_reading_and_particles_stand_alone() -> None:
    reading = read_line("君の声が")

    assert reading.hiragana == "きみ の こえ が"
    assert reading.reading_verified is True


def test_ac38_adjective_and_verb_are_separate_words() -> None:
    assert read_line("遠くひびく").hiragana == "とおく ひびく"


@pytest.mark.parametrize(("line", "expected"), [("ココロ", "こころ"), ("ラーメン", "らーめん")])
def test_ac39_katakana_becomes_hiragana_from_the_line_itself(line: str, expected: str) -> None:
    assert read_line(line).hiragana == expected


@pytest.mark.parametrize("line", ["かぜがふく", "ココロがひかる", "そらへとんでゆく"])
def test_ac40_kana_in_the_line_keeps_its_spelling(line: str) -> None:
    reading = read_line(line)

    assert reading.hiragana.replace(" ", "") == to_hiragana(line)
    assert reading.reading_verified is True


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("君と行こう", "きみ と いこう"),
        ("「君は」", "「きみ は」"),
        ("空、青い", "そら、 あおい"),
    ],
)
def test_ac41_joining_rules_on_real_lines(line: str, expected: str) -> None:
    hiragana = read_line(line).hiragana

    assert hiragana == expected
    assert_well_spaced(hiragana)


def test_plan5_conjunctive_particle_joins_the_verb_before_it() -> None:
    assert read_line("聞いて").hiragana == "きいて"


def test_plan5_conjunctive_de_joins_and_the_next_verb_stands_alone() -> None:
    assert read_line("とんでゆく").hiragana == "とんで ゆく"


def test_ac42_latin_word_is_kept_and_each_space_separated_run_is_analyzed_alone() -> None:
    """On the whole line, the analyzer reads 君 after `Oh` as the suffix くん."""
    assert read_line("Oh 君と").hiragana == "Oh きみ と"


def test_ac42_ascii_digit_is_kept_as_written() -> None:
    assert read_line("2人で").hiragana.startswith("2")


def test_ac42_full_width_digit_is_kept_as_written() -> None:
    assert read_line("２人で").hiragana.startswith("\uff12")


def test_ac38_full_width_space_separates_runs_and_is_not_copied() -> None:
    hiragana = read_line("遠く　ひびく").hiragana

    assert hiragana == "とおく ひびく"


def test_ac47_real_particles_ha_and_he_are_reported_by_word_index() -> None:
    reading = read_line("君は空へ")

    assert reading.hiragana == "きみ は そら へ"
    assert reading.particle_word_indexes == frozenset({1, 3})


def test_ac48_ha_inside_a_noun_is_not_reported_as_a_particle() -> None:
    reading = read_line("はなが咲く")

    assert reading.hiragana.startswith("はな ")
    assert reading.particle_word_indexes == frozenset()


# One piece per word (fake analyzer)


def test_ac39_kana_word_uses_its_written_form_not_the_dictionary_reading() -> None:
    analyzer = FakeAnalyzer({"ココロが": [noun("ココロ", "シン"), particle("が")]})

    reading = read_line("ココロが", analyzer)

    assert reading.hiragana == "こころ が"
    assert reading.reading_verified is True


def test_ac43_unknown_kanji_is_kept_as_written_and_the_line_is_not_verified() -> None:
    analyzer = FakeAnalyzer(
        {f"星{UNKNOWN_KANJI}が": [noun("星", "ホシ"), noun(UNKNOWN_KANJI, None), particle("が")]}
    )

    reading = read_line(f"星{UNKNOWN_KANJI}が", analyzer)

    assert reading.hiragana == f"ほし {UNKNOWN_KANJI} が"
    assert reading.reading_verified is False


@pytest.mark.parametrize(
    "unusable",
    [None, "", "*", "ABC", "ホ1シ"],
    ids=["none", "empty", "asterisk", "latin", "digit-inside"],
)
def test_ac43_kanji_word_with_no_usable_reading_is_kept_as_written(unusable: str | None) -> None:
    line = f"{UNKNOWN_BMP_KANJI}が"
    analyzer = FakeAnalyzer({line: [noun(UNKNOWN_BMP_KANJI, unusable), particle("が")]})

    reading = read_line(line, analyzer)

    assert reading.hiragana == f"{UNKNOWN_BMP_KANJI} が"
    assert reading.reading_verified is False


def test_ac43_line_with_only_known_kanji_is_verified() -> None:
    analyzer = FakeAnalyzer({"星が": [noun("星", "ホシ"), particle("が")]})

    assert read_line("星が", analyzer).reading_verified is True


def test_ac44_kana_check_fails_when_the_reading_changes_the_trailing_kana() -> None:
    analyzer = FakeAnalyzer({"光る": [word("光る", VERB, "ヒカッタ")]})

    reading = read_line("光る", analyzer)

    assert reading.hiragana == "ひかった"
    assert reading.reading_verified is False


def test_ac44_kana_check_passes_when_the_reading_keeps_the_trailing_kana() -> None:
    analyzer = FakeAnalyzer({"光る": [word("光る", VERB, "ヒカル")]})

    reading = read_line("光る", analyzer)

    assert reading.hiragana == "ひかる"
    assert reading.reading_verified is True


def test_ac44_kana_check_also_covers_the_leading_kana() -> None:
    analyzer = FakeAnalyzer({"お星": [noun("お星", "ホシ")]})

    reading = read_line("お星", analyzer)

    assert reading.hiragana == "ほし"
    assert reading.reading_verified is False


def test_ac44_kana_check_compares_katakana_in_the_word_as_hiragana() -> None:
    analyzer = FakeAnalyzer({"光ル": [word("光ル", VERB, "ヒカル")]})

    assert read_line("光ル", analyzer).reading_verified is True


def test_ac45_reading_comes_from_the_kana_field() -> None:
    analyzer = FakeAnalyzer({"東京": [noun("東京", "トウキョウ")]})

    assert read_line("東京", analyzer).hiragana == "とうきょう"


def test_ac42_latin_letters_keep_their_case_and_digits_keep_their_form() -> None:
    analyzer = FakeAnalyzer(
        {
            "ABC君": [noun("ABC", None), word("君", PRONOUN, "キミ")],
            "2人": [noun("2", None), word("人", SUFFIX, "ニン")],
        }
    )

    reading = read_line("ABC君 2人", analyzer)

    assert reading.hiragana == "ABC きみ 2にん"
    assert reading.reading_verified is True


# Joining the pieces (fake analyzer)


def test_ac41_auxiliary_verb_joins_the_piece_before() -> None:
    analyzer = FakeAnalyzer(
        {"行こう": [word("行こ", VERB, "イコ"), word("う", AUXILIARY_VERB, "ウ")]}
    )

    assert read_line("行こう", analyzer).hiragana == "いこう"


def test_ac41_suffix_joins_the_piece_before() -> None:
    analyzer = FakeAnalyzer({"田中さん": [noun("田中", "タナカ"), word("さん", SUFFIX, "サン")]})

    assert read_line("田中さん", analyzer).hiragana == "たなかさん"


@pytest.mark.parametrize("mark", ["、", "。", "\uff01", "」", "』", "…"])
def test_ac41_punctuation_joins_the_piece_before(mark: str) -> None:
    analyzer = FakeAnalyzer({f"空{mark}青": [noun("空", "ソラ"), symbol(mark), noun("青", "アオ")]})

    assert read_line(f"空{mark}青", analyzer).hiragana == f"そら{mark} あお"


def test_ac41_symbol_joins_the_piece_before() -> None:
    analyzer = FakeAnalyzer({"空♪": [noun("空", "ソラ"), word("♪", SYMBOL, "")]})

    assert read_line("空♪", analyzer).hiragana == "そら♪"


@pytest.mark.parametrize("opening", ["「", "『", "\uff08", "(", "[", "【"])
def test_ac41_opening_bracket_joins_the_piece_after(opening: str) -> None:
    analyzer = FakeAnalyzer(
        {f"空{opening}青": [noun("空", "ソラ"), symbol(opening), noun("青", "アオ")]}
    )

    hiragana = read_line(f"空{opening}青", analyzer).hiragana

    assert hiragana == f"そら {opening}あお"


def test_ac41_opening_bracket_at_line_start_and_closing_bracket_at_line_end() -> None:
    analyzer = FakeAnalyzer(
        {"「君は」": [symbol("「"), word("君", PRONOUN, "キミ"), particle("は"), symbol("」")]}
    )

    reading = read_line("「君は」", analyzer)

    assert reading.hiragana == "「きみ は」"
    assert reading.particle_word_indexes == frozenset({1})


def test_ac41_particle_stands_alone_unless_it_is_the_first_word() -> None:
    analyzer = FakeAnalyzer({"がの": [particle("が"), particle("の")]})

    assert read_line("がの", analyzer).hiragana == "が の"


def test_plan5_conjunctive_particle_joins_the_piece_before() -> None:
    analyzer = FakeAnalyzer(
        {"聞いて": [word("聞い", VERB, "キイ"), particle("て", conjunctive=True)]}
    )

    assert read_line("聞いて", analyzer).hiragana == "きいて"


def test_ac41_opening_bracket_alone_at_line_end_leaves_no_trailing_space() -> None:
    analyzer = FakeAnalyzer({"空「": [noun("空", "ソラ"), symbol("「")]})

    assert_well_spaced(read_line("空「", analyzer).hiragana)


def test_ac41_spaces_in_the_line_are_not_copied() -> None:
    analyzer = FakeAnalyzer(
        {"星が": [noun("星", "ホシ"), particle("が")], "空": [noun("空", "ソラ")]}
    )

    reading = read_line("星が 　\t 空", analyzer)

    assert reading.hiragana == "ほし が そら"


def test_ac41_punctuation_after_a_space_joins_the_last_piece_of_the_run_before() -> None:
    analyzer = FakeAnalyzer(
        {"星": [noun("星", "ホシ")], "、空": [symbol("、"), noun("空", "ソラ")]}
    )

    hiragana = read_line("星 、空", analyzer).hiragana

    assert hiragana == "ほし、 そら"
    assert_well_spaced(hiragana)


# Runs and the analyzer calls (plan.md "Two analyzer details")


def test_each_whitespace_separated_run_is_analyzed_alone() -> None:
    analyzer = FakeAnalyzer(
        {"星が": [noun("星", "ホシ"), particle("が")], "空": [noun("空", "ソラ")]}
    )

    read_line("星が　空", analyzer)

    assert analyzer.calls == ["星が", "空"]


def test_run_with_no_japanese_is_one_piece_and_never_reaches_the_analyzer() -> None:
    analyzer = FakeAnalyzer({"君": [word("君", PRONOUN, "キミ")]})

    reading = read_line("la-la, 君", analyzer)

    assert reading.hiragana == "la-la, きみ"
    assert analyzer.calls == ["君"]


# Particles は and へ (AC-47, AC-48)


def test_ac47_tagged_particles_ha_and_he_are_reported_by_word_index() -> None:
    analyzer = FakeAnalyzer(
        {
            "君は空へ": [
                word("君", PRONOUN, "キミ"),
                particle("は"),
                noun("空", "ソラ"),
                particle("へ"),
            ]
        }
    )

    reading = read_line("君は空へ", analyzer)

    assert reading.hiragana == "きみ は そら へ"
    assert reading.particle_word_indexes == frozenset({1, 3})


def test_ac47_particle_with_punctuation_attached_is_still_reported() -> None:
    analyzer = FakeAnalyzer(
        {
            "君は、空へ": [
                word("君", PRONOUN, "キミ"),
                particle("は"),
                symbol("、"),
                noun("空", "ソラ"),
                particle("へ"),
            ]
        }
    )

    reading = read_line("君は、空へ", analyzer)

    assert reading.hiragana == "きみ は、 そら へ"
    assert reading.particle_word_indexes == frozenset({1, 3})


def test_ac48_tooth_read_ha_is_not_a_particle() -> None:
    analyzer = FakeAnalyzer({"歯が": [noun("歯", "ハ"), particle("が")]})

    reading = read_line("歯が", analyzer)

    assert reading.hiragana == "は が"
    assert reading.particle_word_indexes == frozenset()


def test_ac48_he_tagged_as_a_noun_is_not_a_particle() -> None:
    analyzer = FakeAnalyzer({"へ": [noun("へ", "ヘ")]})

    assert read_line("へ", analyzer).particle_word_indexes == frozenset()


def test_ac48_other_particles_are_not_reported() -> None:
    analyzer = FakeAnalyzer({"星がの": [noun("星", "ホシ"), particle("が"), particle("の")]})

    assert read_line("星がの", analyzer).particle_word_indexes == frozenset()


def test_ac48_katakana_particle_ha_is_reported_and_written_in_hiragana() -> None:
    analyzer = FakeAnalyzer({"君ハ": [word("君", PRONOUN, "キミ"), particle("ハ")]})

    reading = read_line("君ハ", analyzer)

    assert reading.hiragana == "きみ は"
    assert reading.particle_word_indexes == frozenset({1})


# Runs with no Japanese made only of punctuation, and katakana counter marks (T2 review)


@pytest.mark.parametrize(
    ("line", "expected"),
    [("君 、", "きみ、"), ("君 !", "きみ!"), ("君 …", "きみ…"), ("君 !?", "きみ!?")],
    ids=["comma", "exclamation", "ellipsis", "two-marks"],
)
def test_ac41_punctuation_only_run_joins_the_piece_before(line: str, expected: str) -> None:
    analyzer = FakeAnalyzer({"君": [word("君", PRONOUN, "キミ")]})

    reading = read_line(line, analyzer)

    assert reading.hiragana == expected
    assert analyzer.calls == ["君"]


def test_ac41_star_then_comma_run_joins_the_piece_before() -> None:
    analyzer = FakeAnalyzer({"星": [noun("星", "ホシ")]})

    assert read_line("星 、", analyzer).hiragana == "ほし、"


@pytest.mark.parametrize(
    ("line", "expected"),
    [("( 君 )", "(きみ)"), ("「 星が 」", "「ほし が」"), ("空 ( 君 )", "そら (きみ)")],
    ids=["round-alone", "kagi-around-two-words", "after-a-word"],
)
def test_ac41_opening_bracket_run_joins_the_piece_after(line: str, expected: str) -> None:
    analyzer = FakeAnalyzer(
        {
            "君": [word("君", PRONOUN, "キミ")],
            "星が": [noun("星", "ホシ"), particle("が")],
            "空": [noun("空", "ソラ")],
        }
    )

    hiragana = read_line(line, analyzer).hiragana

    assert hiragana == expected
    assert_well_spaced(hiragana)


@pytest.mark.parametrize(
    ("surface", "reading", "expected"),
    [("三ヶ月", "サンカゲツ", "さんかげつ"), ("三ヵ月", "サンカゲツ", "さんかげつ")],
    ids=["small-ke", "small-ka"],
)
def test_ac44_small_ke_and_ka_in_a_kanji_word_pass_the_kana_check(
    surface: str, reading: str, expected: str
) -> None:
    analyzer = FakeAnalyzer({surface: [noun(surface, reading)]})

    result = read_line(surface, analyzer)

    assert result.hiragana == expected
    assert result.reading_verified is True


def test_ac44_small_ke_at_the_end_of_a_kanji_word_matches_ka_or_ga_in_the_reading() -> None:
    analyzer = FakeAnalyzer({"関ヶ": [noun("関ヶ", "セキガ")]})

    result = read_line("関ヶ", analyzer)

    assert result.hiragana == "せきが"
    assert result.reading_verified is True


def test_ac44_small_ke_as_its_own_suffix_word_passes_the_kana_check() -> None:
    analyzer = FakeAnalyzer({"三ヶ月": [noun("三", "サン"), word("ヶ月", SUFFIX, "カゲツ")]})

    result = read_line("三ヶ月", analyzer)

    assert result.hiragana == "さんかげつ"
    assert result.reading_verified is True


def test_ac44_small_ke_at_the_end_of_a_kanji_word_fails_on_another_kana() -> None:
    analyzer = FakeAnalyzer({"関ヶ": [noun("関ヶ", "セキノ")]})

    result = read_line("関ヶ", analyzer)

    assert result.hiragana == "せきの"
    assert result.reading_verified is False

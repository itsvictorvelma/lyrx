"""Tests for spelling hiragana as modified Hepburn romaji without macrons. Invented words only."""

import pytest

from lyrx.romaji import to_romaji

# Basic and combined sounds (AC-23)


def test_ac23_spec_example_basic_sounds() -> None:
    assert to_romaji("しちつふじぢづ") == "shichitsufujijizu"


def test_ac23_spec_example_combined_sounds() -> None:
    assert to_romaji("きゃ しゃ ちゃ じゃ りょ") == "kya sha cha ja ryo"


# Each row is one word, so no row hits the whole-word は/へ particle rule.
@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("あいうえお", "aiueo"),
        ("かきくけこ", "kakikukeko"),
        ("さしすせそ", "sashisuseso"),
        ("たちつてと", "tachitsuteto"),
        ("なにぬねの", "naninuneno"),
        ("はひふへほ", "hahifuheho"),
        ("まみむめも", "mamimumemo"),
        ("やゆよ", "yayuyo"),
        ("らりるれろ", "rarirurero"),
        ("わを", "wao"),
    ],
)
def test_ac23_every_basic_kana_row(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("がぎぐげご", "gagigugego"),
        ("ざじずぜぞ", "zajizuzezo"),
        ("だぢづでど", "dajizudedo"),
        ("ばびぶべぼ", "babibubebo"),
        ("ぱぴぷぺぽ", "papipupepo"),
    ],
)
def test_ac23_every_dakuten_and_handakuten_row(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("きゃ", "kya"),
        ("きゅ", "kyu"),
        ("きょ", "kyo"),
        ("ぎゃ", "gya"),
        ("ぎゅ", "gyu"),
        ("ぎょ", "gyo"),
        ("しゃ", "sha"),
        ("しゅ", "shu"),
        ("しょ", "sho"),
        ("じゃ", "ja"),
        ("じゅ", "ju"),
        ("じょ", "jo"),
        ("ちゃ", "cha"),
        ("ちゅ", "chu"),
        ("ちょ", "cho"),
        ("ぢゃ", "ja"),
        ("ぢゅ", "ju"),
        ("ぢょ", "jo"),
        ("にゃ", "nya"),
        ("にゅ", "nyu"),
        ("にょ", "nyo"),
        ("ひゃ", "hya"),
        ("ひゅ", "hyu"),
        ("ひょ", "hyo"),
        ("びゃ", "bya"),
        ("びゅ", "byu"),
        ("びょ", "byo"),
        ("ぴゃ", "pya"),
        ("ぴゅ", "pyu"),
        ("ぴょ", "pyo"),
        ("みゃ", "mya"),
        ("みゅ", "myu"),
        ("みょ", "myo"),
        ("りゃ", "rya"),
        ("りゅ", "ryu"),
        ("りょ", "ryo"),
    ],
)
def test_ac23_every_combined_sound(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac23_combined_sound_inside_a_word() -> None:
    assert to_romaji("おちゃのみ") == "ochanomi"


def test_ac23_voiced_chi_and_tsu_inside_words() -> None:
    assert to_romaji("ちぢむ つづく") == "chijimu tsuzuku"


# Katakana, extended kana, and iteration marks (AC-23, plan.md "Romaji edge cases")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ラーメン", "raamen"),
        ("ココロ", "kokoro"),
        ("キャンプ", "kyanpu"),
        ("そら ト ウミ", "sora to umi"),
    ],
)
def test_ac23_katakana_is_turned_into_hiragana_first(text: str, expected: str) -> None:
    assert to_romaji(text) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ふぁ", "fa"),
        ("ふぃ", "fi"),
        ("ふぇ", "fe"),
        ("ふぉ", "fo"),
        ("ふゅ", "fyu"),
        ("てぃ", "ti"),
        ("でぃ", "di"),
        ("とぅ", "tu"),
        ("どぅ", "du"),
        ("しぇ", "she"),
        ("じぇ", "je"),
        ("ちぇ", "che"),
        ("いぇ", "ye"),
        ("うぃ", "wi"),
        ("うぇ", "we"),
        ("うぉ", "wo"),
        ("ゔ", "vu"),
        ("ゔぁ", "va"),
        ("ゔぃ", "vi"),
        ("ゔぇ", "ve"),
        ("ゔぉ", "vo"),
        ("ゐ", "wi"),
        ("ゑ", "we"),
    ],
)
def test_ac23_every_extended_kana(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac23_extended_kana_inside_a_word() -> None:
    assert to_romaji("ふぉとぅでぃ") == "fotudi"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ぁ", "a"),
        ("ぃ", "i"),
        ("ぅ", "u"),
        ("ぇ", "e"),
        ("ぉ", "o"),
        ("ゃ", "ya"),
        ("ゅ", "yu"),
        ("ょ", "yo"),
        ("ゎ", "wa"),
    ],
)
def test_ac23_lone_small_kana_is_read_as_its_own_sound(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("あゃ", "aya"),
        ("かぁ", "kaa"),
        ("ふゃ", "fuya"),
        ("くゎ", "kuwa"),
    ],
)
def test_ac23_small_kana_that_cannot_combine_is_read_as_its_own_sound(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("こゝろ", "kokoro"),
        ("すゞ", "suzu"),
        ("はゞ", "haba"),
        ("しゞみ", "shijimi"),
        ("つゞく", "tsuzuku"),
        ("コヽロ", "kokoro"),
        ("スヾ", "suzu"),
    ],
)
def test_ac23_iteration_marks_repeat_the_kana_before_them(text: str, expected: str) -> None:
    assert to_romaji(text) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ぶゝ", "bubu"),
        ("きゃゝ", "kyakya"),
        ("きゃゞ", "kyagya"),
        ("あゞ", "aa"),
    ],
)
def test_ac23_iteration_marks_repeat_the_whole_previous_sound(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ゝあ", "a"),
        ("ゞあ", "a"),
        ("そら ゝあ", "sora a"),
    ],
)
def test_ac23_iteration_mark_at_word_start_is_dropped(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("\u30f6", "ke"),
        ("\u30f5", "ka"),
        ("\u3096", "ke"),
        ("\u3095", "ka"),
        ("一\u30f6月", "一ke月"),
    ],
)
def test_ac23_small_ka_and_ke_read_as_ka_and_ke(text: str, expected: str) -> None:
    assert to_romaji(text) == expected


def test_ac23_katakana_vu_reads_vu() -> None:
    assert to_romaji("ヴ") == "vu"


HANDLED_KANA = [
    *(chr(code_point) for code_point in range(0x3041, 0x3097)),
    *(chr(code_point) for code_point in range(0x30A1, 0x30F7)),
    "\u309d",  # hiragana iteration mark
    "\u309e",  # voiced hiragana iteration mark
    "\u30fd",  # katakana iteration mark
    "\u30fe",  # voiced katakana iteration mark
    "\u30fc",  # long vowel mark
]


def kana_left_in(romaji: str) -> list[str]:
    """The characters of `romaji` that are handled kana and so should have been spelled."""
    return [character for character in romaji if character in HANDLED_KANA]


@pytest.mark.parametrize("before", ["", "き", "ん", "っ"])
def test_ac23_no_handled_kana_survives_into_the_romaji(before: str) -> None:
    leftovers = {
        kana: kana_left_in(to_romaji(before + kana))
        for kana in HANDLED_KANA
        if kana_left_in(to_romaji(before + kana))
    }

    assert leftovers == {}


# Small っ (AC-24)


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("がっこう", "gakkou"),
        ("いっしょ", "issho"),
        ("まっちゃ", "matcha"),
    ],
)
def test_ac24_spec_examples_small_tsu_doubles_the_next_consonant(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("いっぱい", "ippai"),
        ("みっつ", "mittsu"),
        ("ばっじ", "bajji"),
        ("あっさり", "assari"),
        ("ねっと", "netto"),
        ("あっきゃ", "akkya"),
        ("きっぷ", "kippu"),
    ],
)
def test_ac24_small_tsu_doubles_the_first_consonant_of_the_next_sound(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("まっち", "matchi"),
        ("まっちゅ", "matchu"),
        ("まっちょ", "matcho"),
    ],
)
def test_ac24_small_tsu_before_chi_is_t_not_c(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac24_spec_example_small_tsu_at_word_end_is_dropped() -> None:
    assert to_romaji("あっ") == "a"


def test_ac24_small_tsu_at_word_end_before_a_space_is_dropped() -> None:
    assert to_romaji("あっ そら") == "a sora"


def test_ac24_small_tsu_before_a_vowel_is_dropped() -> None:
    assert to_romaji("あっあ") == "aa"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("あっ!", "a!"),
        ("あっ\uff01", "a!"),
        ("あっ。", "a."),
        ("あっk", "ak"),
    ],
)
def test_ac24_small_tsu_before_non_kana_is_dropped(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("あっん", "an"),
        ("あっっか", "akka"),
        ("そらっ", "sora"),
    ],
)
def test_ac24_small_tsu_before_n_another_small_tsu_or_at_the_end_is_dropped(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


def test_ac24_dropped_small_tsu_is_invisible_to_the_long_mark() -> None:
    assert to_romaji("あっー") == "aa"


def test_ac24_small_tsu_before_vu_doubles_v() -> None:
    assert to_romaji("っゔ") == "vvu"


# Long vowels (AC-25)


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("おかあさん", "okaasan"),
        ("とうきょう", "toukyou"),
        ("おおきい", "ookii"),
        ("えいが", "eiga"),
    ],
)
def test_ac25_spec_examples_long_vowels_follow_the_kana(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac25_spec_example_long_mark_repeats_the_vowel_before_it() -> None:
    assert to_romaji("らーめん") == "raamen"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("しー", "shii"),
        ("ちー", "chii"),
        ("つー", "tsuu"),
        ("ふー", "fuu"),
        ("けー", "kee"),
        ("のー", "noo"),
        ("きょー", "kyoo"),
        ("ちゅー", "chuu"),
        ("じゃー", "jaa"),
    ],
)
def test_ac25_long_mark_repeats_the_vowel_of_the_sound_before_it(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


def test_ac25_long_mark_in_the_middle_of_a_word() -> None:
    assert to_romaji("すーぷの") == "suupuno"


def test_ac25_output_has_no_macrons() -> None:
    assert to_romaji("とうきょう おおきい らーめん") == "toukyou ookii raamen"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ーあ", "a"),
        ("そら ーあ", "sora a"),
        ("んー", "n"),
        ("きんー", "kin"),
    ],
)
def test_ac25_long_mark_with_no_vowel_before_it_is_dropped(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac25_long_mark_after_an_extended_kana_repeats_its_vowel() -> None:
    assert to_romaji("ふぁー") == "faa"


# ん (AC-26)


def test_ac26_spec_example_n_before_a_vowel_gets_an_apostrophe() -> None:
    assert to_romaji("きんえん") == "kin'en"


def test_ac26_spec_example_n_before_y_gets_an_apostrophe() -> None:
    assert to_romaji("ほんや") == "hon'ya"


def test_ac26_spec_example_n_before_p_stays_n() -> None:
    assert to_romaji("さんぽ") == "sanpo"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("きんあ", "kin'a"),
        ("きんい", "kin'i"),
        ("きんう", "kin'u"),
        ("きんお", "kin'o"),
        ("ほんゆ", "hon'yu"),
        ("ほんよ", "hon'yo"),
    ],
)
def test_ac26_n_before_every_vowel_and_y_gets_an_apostrophe(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("さんば", "sanba"),
        ("さんま", "sanma"),
        ("さんぴゃ", "sanpya"),
    ],
)
def test_ac26_n_before_b_m_or_p_stays_n(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("ほん", "hon"),
        ("さんか", "sanka"),
        ("あんない", "annai"),
        ("かんじゃ", "kanja"),
        ("ぎんしゃ", "ginsha"),
    ],
)
def test_ac26_n_elsewhere_is_n_without_an_apostrophe(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac26_n_at_word_end_before_a_word_starting_with_a_vowel_has_no_apostrophe() -> None:
    assert to_romaji("ほん あお") == "hon ao"


def test_ac26_dropped_long_mark_is_invisible_to_the_n_rule() -> None:
    assert to_romaji("んーあ") == "n'a"


def test_ac26_n_before_attached_punctuation_is_plain_n() -> None:
    assert to_romaji("ほん、") == "hon,"


# Particles (AC-27)


def test_ac27_spec_example_particles_in_a_line() -> None:
    assert to_romaji("きみ は うみ へ はな を") == "kimi wa umi e hana o"


def test_ac27_spec_example_he_inside_a_word_stays_he() -> None:
    assert to_romaji("へや") == "heya"


def test_ac27_ha_inside_a_word_stays_ha() -> None:
    assert to_romaji("はな") == "hana"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("は", "wa"),
        ("へ", "e"),
        ("を", "o"),
    ],
)
def test_ac27_word_that_is_exactly_a_particle(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("は そら", "wa sora"),
        ("そら は", "sora wa"),
        ("へ うみ", "e umi"),
    ],
)
def test_ac27_particle_at_the_start_or_end_of_a_line(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("はは", "haha"),
        ("へへ", "hehe"),
        ("ほしは", "hoshiha"),
        ("うみへ", "umihe"),
        ("ば", "ba"),
        ("ぺ", "pe"),
    ],
)
def test_ac27_ha_and_he_that_are_not_a_whole_word_keep_ha_and_he(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


def test_ac27_wo_inside_a_longer_word_is_still_o() -> None:
    assert to_romaji("をかし") == "okashi"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("は、", "wa,"),
        ("へ。", "e."),
        ("「は」", '"wa"'),
        ("きみ は、 うみ へ。", "kimi wa, umi e."),
    ],
)
def test_ac27_particle_rule_ignores_attached_punctuation(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac27_particle_separated_by_full_width_spaces() -> None:
    assert to_romaji("きみ\u3000は\u3000うみ") == "kimi wa umi"


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("は!", "wa!"),
        ("へ?", "e?"),
        ("は,", "wa,"),
    ],
)
def test_ac27_ascii_punctuation_counts_as_attached_for_particles(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("キミ ハ ウミ ヘ", "kimi wa umi e"),
        ("ハ", "wa"),
        ("ヘ", "e"),
    ],
)
def test_ac27_katakana_particle_alone_follows_the_particle_rule(text: str, expected: str) -> None:
    assert to_romaji(text) == expected


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("は…", "wa…"),
        ("は\uff5e", "wa\uff5e"),
        ("は\u301c", "wa\u301c"),
        ("『は』", "『wa』"),
        ("へ・", "e・"),
    ],
)
def test_ac27_particle_with_other_japanese_punctuation_attached(
    hiragana: str, expected: str
) -> None:
    assert to_romaji(hiragana) == expected


def test_ac27_punctuation_inside_a_word_is_not_stripped_for_the_particle_rule() -> None:
    assert to_romaji("は、は") == "ha,ha"


# Spacing and punctuation (AC-28)


def test_ac28_spec_example_punctuation_and_spacing() -> None:
    assert to_romaji("そら、 あお。") == "sora, ao."


def test_ac28_spec_example_latin_letters_and_digits_pass_through() -> None:
    assert to_romaji("ABC 123") == "ABC 123"


def test_ac28_words_stay_separated_by_single_spaces() -> None:
    assert to_romaji("ほし の よる に") == "hoshi no yoru ni"


def test_ac28_romaji_from_kana_is_lowercase() -> None:
    romaji = to_romaji("きゃ しゃ ちゃ はな")

    assert romaji == "kya sha cha hana"
    assert romaji == romaji.lower()


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("そら、", "sora,"),
        ("そら。", "sora."),
        ("そら\uff01", "sora!"),
        ("そら\uff1f", "sora?"),
        ("「そら」", '"sora"'),
        ("そら\u3000あお", "sora ao"),
    ],
)
def test_ac28_japanese_punctuation_becomes_ascii(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


@pytest.mark.parametrize(
    "text",
    [
        "abc",
        "Hello World",
        "2024",
        "~ - * / # & ( ) : ; ' _",
        "♪",  # music note
        "!?,.",
    ],
)
def test_ac28_other_characters_pass_through_unchanged(text: str) -> None:
    assert to_romaji(text) == text


def test_ac28_mixed_kana_latin_and_digits_in_one_line() -> None:
    assert to_romaji("そら 2 ABC は") == "sora 2 ABC wa"


def test_ac28_empty_input_gives_empty_output() -> None:
    assert to_romaji("") == ""


@pytest.mark.parametrize(
    ("hiragana", "expected"),
    [
        ("きみ  は", "kimi  wa"),
        ("きみ\u3000\u3000は", "kimi  wa"),
        ("きみ \u3000は", "kimi  wa"),
        (" そら ", " sora "),
    ],
)
def test_ac28_spacing_is_kept_as_given_without_collapsing(hiragana: str, expected: str) -> None:
    assert to_romaji(hiragana) == expected


def test_ac28_full_width_latin_and_digits_pass_through_unchanged() -> None:
    assert to_romaji("\uff21\uff11") == "\uff21\uff11"


# Determinism (AC-23 to AC-28: the same input always gives the same output)


def test_ac23_same_input_always_gives_the_same_output() -> None:
    line = "きみ は がっこう へ らーめん を たべ に いく。"

    assert to_romaji(line) == "kimi wa gakkou e raamen o tabe ni iku."
    assert to_romaji(line) == to_romaji(line)

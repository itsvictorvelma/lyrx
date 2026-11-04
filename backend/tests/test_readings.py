from app.readings import reading_for


def test_the_same_line_always_reads_the_same_way() -> None:
    assert reading_for("死ぬのがいいわ") == ("しぬ の が いい わ", "shinu no ga ii wa")
    assert reading_for("死ぬのがいいわ") == reading_for("死ぬのがいいわ")


def test_repeated_mirror_lines_keep_the_same_reading() -> None:
    assert reading_for("鏡よ 鏡よ この世で一番") == (
        "かがみ よ かがみ よ このよ で いちばん",
        "kagami yo kagami yo konoyo de ichiban",
    )


def test_katakana_and_an_english_word_stay_in_place() -> None:
    hiragana, romaji = reading_for("あなたとこのままおサラバするより Monday")

    assert "さらば" in hiragana
    assert "サラバ" not in hiragana
    assert hiragana.endswith("Monday")
    assert romaji.endswith("Monday")
    assert "saraba" in romaji
    assert len(hiragana.split()) == len(romaji.split())


def test_an_english_lyric_line_is_copied() -> None:
    line = "It doesn't matter if it's Sunday"
    assert reading_for(line) == (line, line)

from app.align import TimedWord, assign_line_starts


def test_matching_words_set_each_line_start() -> None:
    starts = assign_line_starts(
        ["雨が降る", "空は青い"],
        [
            TimedWord("雨が", 1.0, 1.4),
            TimedWord("降る", 1.4, 2.0),
            TimedWord("空は", 3.0, 3.5),
            TimedWord("青い", 3.5, 4.2),
        ],
    )

    assert starts == [1.0, 3.0]


def test_punctuation_does_not_block_a_match() -> None:
    starts = assign_line_starts(["雨、"], [TimedWord("雨", 2.5, 3.0)])

    assert starts == [2.5]


def test_unmatched_middle_line_falls_between_its_neighbors() -> None:
    starts = assign_line_starts(
        ["あめ", "かぜ", "そら"],
        [TimedWord("あめ", 1.0, 2.0), TimedWord("そら", 5.0, 6.0)],
    )

    assert starts is not None
    assert starts[0] == 1.0
    assert starts[1] == 3.0
    assert starts[2] == 5.0


def test_unrelated_words_still_give_every_line_a_time() -> None:
    starts = assign_line_starts(["雨が降る", "空は青い"], [TimedWord("zzzzzzzz", 4.0, 9.0)])

    assert starts == [4.0, 6.5]


def test_no_words_leaves_every_line_untimed() -> None:
    assert assign_line_starts(["雨", "空"], []) == [None, None]


def test_line_starts_stay_in_order() -> None:
    starts = assign_line_starts(
        ["あ", "い", "う"],
        [TimedWord("あ", 3.0, 3.2), TimedWord("い", 2.0, 2.2), TimedWord("う", 4.0, 4.2)],
    )

    assert starts is not None
    assert starts == sorted(starts)
    assert len(set(starts)) == 3

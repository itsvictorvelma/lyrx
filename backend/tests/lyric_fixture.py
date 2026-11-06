"""One canned LRCLIB lyric for the default tests.

This is not a screen. The app does not list it, and the tests do not call
LRCLIB or Groq.
"""

from app.generation.lrclib import Recording

AME = Recording(title="Ame", artist="Example", text="雨\n[Chorus]\n空")

# Plastic Love as LRCLIB returns it after blank lines and square-bracket labels
# are dropped. Line index 1 has two kanji brackets.
PLASTIC_LOVE_LINES = [
    "突然のキスや 熱いまなざしで",
    "恋のプログラムを 狂わせないでね",
    "出逢いと別れ 上手に打ち込んで",
    "時間がくれば終わる don't hurry",
    "愛に傷ついた あの日からずっと",
    "昼と夜が逆の 暮らしを続けて",
    "はやりの disco で 踊り明かすうちに",
    "おぼえた魔術なのよ I'm sorry",
    "わたしのことを決して 本気で愛さないで",
    "恋なんてただのゲーム 楽しめばそれでいいの",
    "閉ざした心を飾る 派手なドレスも靴も",
    "孤独な友達",
    "わたしを誘う人は 皮肉なものね いつも",
    "彼に似てるわなぜか 思い出と重なり合う",
    "グラスを落として急に 涙ぐんでもわけは",
    "尋ねないでね",
    "夜更けの高速で 眠りにつくころ",
    "ハロゲンライトだけ 妖しく輝く",
    "氷のように冷たい女だと",
    "ささやく声がしても don't worry",
    "I'm just playing games, I know that's plastic love",
    "Dance to the plastic beat, another morning comes",
    "I'm just playing games, I know that's plastic love",
    "Dance to the plastic beat, another morning comes",
    "I'm just playing games, I know that's plastic love",
    "Dance to the plastic beat, another morning comes",
]


def search_ame(title: str, artist: str) -> Recording | None:
    if title.strip().casefold() != "ame":
        return None
    return AME

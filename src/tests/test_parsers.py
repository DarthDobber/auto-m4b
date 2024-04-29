from pathlib import Path

import pytest

from src.lib.audiobook import Audiobook
from src.lib.ffmpeg_utils import get_bitrate_py, is_variable_bitrate
from src.lib.formatters import human_bitrate
from src.lib.parsers import (
    extract_path_info,
    romans,
)
from src.tests.helpers.pytest_statics import PART_ROMANS, ROTK_ROMANS
from src.tests.helpers.pytest_utils import testutils


def test_extract_path_info(benedict_society__mp3):

    assert (
        extract_path_info(benedict_society__mp3).fs_title
        == "The Mysterious Benedict Society"
    )


def test_bitrate_vbr(bitrate_vbr__mp3: Audiobook):

    vbr_file = bitrate_vbr__mp3.sample_audio1

    std_bitrate, actual = get_bitrate_py(vbr_file)
    assert std_bitrate == 48000
    assert actual == 45567

    assert is_variable_bitrate(vbr_file)

    assert human_bitrate(vbr_file) == "~46 kb/s"


def test_bitrate_cbr(bitrate_cbr__mp3: Audiobook):

    cbr_file = bitrate_cbr__mp3.sample_audio1

    std_bitrate, actual = get_bitrate_py(cbr_file)
    assert std_bitrate == 128000
    assert actual == 128000

    assert not is_variable_bitrate(cbr_file)

    assert human_bitrate(cbr_file) == "128 kb/s"


@pytest.mark.parametrize(
    "input, expected",
    [
        ("A", {}),
        ("B", {}),
        ("8", {}),
        ("I", {"I": 1}),
        ("II", {"II": 1}),
        ("III", {"III": 1}),
        ("IV", {"IV": 1}),
        ("V", {"V": 1}),
        ("VI", {"VI": 1}),
        ("VII", {"VII": 1}),
        ("VIII", {"VIII": 1}),
        ("IX", {"IX": 1}),
        ("X", {"X": 1}),
        (["Star Wars", "Episode", "IV", "A New Hope"], {"IV": 1}),
        (["Star Wars", "Episode", "V", "The Empire Strikes Back"], {"V": 1}),
        (["Star Wars", "Episode", "VI", "Return of the Jedi"], {"VI": 1}),
        (["Star Wars", "Episode", "VII", "The Force Awakens"], {"VII": 1}),
        (["Star Wars", "Episode", "VIII", "The Last Jedi"], {"VIII": 1}),
        (["Star Wars", "Episode", "IX", "The Rise of Skywalker"], {"IX": 1}),
        (["Star Trek III: The Search for Spock"], {"III": 1}),
        (
            ["Chapter I", "Chapter II", "Chapter III", "Chapter IV"],
            {"I": 1, "II": 1, "III": 1, "IV": 1},
        ),
    ],
)
def test_get_roman_numerals_dict(input, expected):

    from src.lib.parsers import get_romans_dict

    assert get_romans_dict(input) == expected


@pytest.mark.parametrize(
    "test_files, expected",
    [
        (
            ROTK_ROMANS,
            False,
        ),
        (
            PART_ROMANS,
            True,
        ),
    ],
)
def test_roman_numerals_affect_file_order(
    test_files: list[str], expected, tmp_path: Path
):

    from src.lib.parsers import roman_numerals_affect_file_order

    d = testutils.make_tmp_files(tmp_path, test_files)

    assert roman_numerals_affect_file_order(d) == expected


@pytest.mark.parametrize(
    "test_case, expected",
    [
        ("A", False),
        ("B", False),
        ("8", False),
        ("I", True),
        ("II", True),
        ("III", True),
        ("IV", True),
        ("V", True),
        ("VI", True),
        ("VII", True),
        ("VIII", True),
        ("IX", True),
        ("X", True),
        ("XI", True),
        ("XII", True),
        ("XIII", True),
        ("XIV", True),
        ("XV", True),
        ("XVI", True),
        ("XVII", True),
        ("XVIII", True),
        ("XIX", True),
        ("XX", True),
        ("XXI", True),
        ("XXII", True),
        ("XXIII", True),
        ("XXIV", True),
        ("XXV", True),
        ("XXVI", True),
        ("XXVII", True),
        ("XXVIII", True),
        ("XXIX", True),
        ("XXX", True),
        ("XXXI", True),
        ("XXXII", True),
        ("XXXIII", True),
        ("XXXIV", True),
        ("XXXV", True),
        ("XXXVI", True),
        ("XXXVII", True),
        ("XXXVIII", True),
        ("XXXIX", True),
        ("XL", True),
        ("XLI", True),
        ("XLII", True),
        ("XLIII", True),
        ("XLIV", True),
        ("XLV", True),
        ("XLVI", True),
        ("XLVII", True),
        ("XLVIII", True),
        ("XLIX", True),
        ("L", True),
        ("LI", True),
        ("LII", True),
        ("LIII", True),
        ("LIV", True),
        ("LV", True),
        ("LVI", True),
        ("LVII", True),
        ("LVIII", True),
        ("LIX", True),
        ("LX", True),
        ("LXI", True),
        ("LXII", True),
        ("LXIII", True),
        ("LXIV", True),
        ("LXV", True),
        ("LXVI", True),
        ("LXVII", True),
        ("LXVIII", True),
        ("LXIX", True),
        ("LXX", True),
    ],
)
def test_romans_is_roman_numeral(test_case, expected):

    assert romans.is_roman_numeral(test_case) == expected


@pytest.mark.parametrize(
    "test_case, expected",
    [
        ("A", []),
        ("B", []),
        ("8", []),
        ("I", ["I"]),
        ("II", ["II"]),
        ("Chapter III", ["III"]),
        ("Chapter IV", ["IV"]),
        ("Chapter V", ["V"]),
        ("Chapter VI", ["VI"]),
        ("Chapter VII", ["VII"]),
        ("Chapter VIII", ["VIII"]),
        ("Chapter IX", ["IX"]),
        ("Chapter X", ["X"]),
        ("Chapter XI", ["XI"]),
        ("Chapter XII", ["XII"]),
        ("Chapter XIII", ["XIII"]),
        ("Star Wars Episode IV: A New Hope", ["IV"]),
        ("Star Wars Episode V: The Empire Strikes Back", ["V"]),
        ("Star Wars Episode VI: Return of the Jedi", ["VI"]),
        ("Star Wars Episode VII: The Force Awakens", ["VII"]),
        ("Star Wars Episode VIII: The Last Jedi", ["VIII"]),
        ("Star Wars Episode IX: The Rise of Skywalker", ["IX"]),
        ("Star Trek III: The Search for Spock", ["III"]),
        ("Dune: Parts II & III - Muad'Dib & The Prophet", ["II", "III"]),
    ],
)
def test_romans_find_all(test_case, expected):

    assert romans.find_all(test_case) == expected


@pytest.mark.parametrize(
    "test_case, expected",
    [
        ("Bk1", False),
        ("Bk-1", False),
        ("Book1", False),
        ("Book-1", False),
        ("Book.1", False),
        ("Book_1", False),
        ("Book 1", False),
        ("Book 1 - The Fellowship of the Ring", False),
        ("CD1", True),
        ("CD-1", True),
        ("cd1", True),
        ("Disc-1", True),
        ("Disk.1", True),
        ("Disc_1", True),
        ("CD 1", True),
        ("Disc 1 - The Fellowship of the Ring", True),
        ("The Fellowship of the Ring - CD 1", True),
        ("Disk", False),
        ("Disc", False),
        ("CD", False),
        ("The Fellowship of the Ring", False),
        ("The Fellowship of the Ring - CD", False),
        ("The Fellowship of the Ring - Disc", False),
        ("The Fellowship of the Ring - Disc #3", True),
        ("The Fellowship of the Ring - Disc # 3", True),
        ("The Fellowship of the Ring - Disc.3", True),
        ("The Fellowship of the Ring - Disc.#3", True),
        ("#", False),
        ("#1", False),
        ("#-1", False),
        ("#1", False),
        ("#-1", False),
        ("#1", False),
        ("#1", False),
        ("# 1", False),
        ("Aleron Kong - The Land Alliances (Chaos Seeds #3)", False),
        ("# 3 (Chaos Seeds) - Aleron Kong - The Land Alliances", False),
        ("The Land Alliances (Chaos Seeds #3) - Aleron Kong", False),
        ("#The Land Alliances (Chaos Seeds)", False),
        ("The Land Alliances (Chaos Seeds) - #", False),
        ("The Land Alliances (Disc #1)", True),
    ],
)
def test_is_maybe_multi_disc(test_case, expected):

    from src.lib.parsers import is_maybe_multi_disc

    assert is_maybe_multi_disc(test_case) == expected
    assert is_maybe_multi_disc(test_case.lower()) == expected
    assert is_maybe_multi_disc(test_case.title()) == expected
    assert is_maybe_multi_disc(test_case.capitalize()) == expected
    assert is_maybe_multi_disc(test_case.upper()) == expected


@pytest.mark.parametrize(
    "test_case, expected",
    [
        ("Pt1", True),
        ("part1", True),
        ("part_1", True),
        ("Pt8", True),
        ("Pt-8", True),
        ("Part8", True),
        ("Part-8", True),
        ("Part.8", True),
        ("Part_8", True),
        ("Part 8", True),
        ("Part 8 - Quest for the Spark", True),
        ("Quest for the Spark - Pt 8", True),
        ("Part", False),
        ("Quest for the Spark", False),
        ("Quest for the Spark - Pt", False),
    ],
)
def test_is_maybe_multi_part(test_case, expected):

    from src.lib.parsers import is_maybe_multi_part

    assert is_maybe_multi_part(test_case) == expected
    assert is_maybe_multi_part(test_case.lower()) == expected
    assert is_maybe_multi_part(test_case.title()) == expected
    assert is_maybe_multi_part(test_case.capitalize()) == expected
    assert is_maybe_multi_part(test_case.upper()) == expected


@pytest.mark.parametrize(
    "test_case, expected",
    [
        ("Bk1", True),
        ("Bk-1", True),
        ("Book1", True),
        ("Book-1", True),
        ("Book.1", True),
        ("Book_1", True),
        ("Book 1", True),
        ("Book 1 - The Fellowship of the Ring", True),
        ("The Fellowship of the Ring - Bk 1", True),
        ("Book", False),
        ("The Fellowship of the Ring", False),
        ("The Fellowship of the Ring - Bk", False),
        ("#1", True),
        ("#-1", True),
        ("#1", True),
        ("#-1", True),
        ("#1", True),
        ("#1", True),
        ("# 1", True),
        ("01 - Pride Of Chanur", True),
        ("Old Man's War Series/Old Man's War - John Scalzi", True),
        ("Aleron Kong - The Land Alliances (Chaos Seeds #3)", True),
        ("# 3 (Chaos Seeds) - Aleron Kong - The Land Alliances", True),
        ("The Land Alliances (Chaos Seeds #3) - Aleron Kong", True),
        ("#", False),
        ("#The Land Alliances (Chaos Seeds)", False),
        ("The Land Alliances (Chaos Seeds) - #", False),
        ("The Land Alliances (Disc #1)", False),
    ],
)
def test_is_maybe_multi_book_or_series(test_case, expected):

    from src.lib.parsers import is_maybe_multi_book_or_series

    assert is_maybe_multi_book_or_series(test_case) == expected
    assert is_maybe_multi_book_or_series(test_case.lower()) == expected
    assert is_maybe_multi_book_or_series(test_case.title()) == expected
    assert is_maybe_multi_book_or_series(test_case.capitalize()) == expected
    assert is_maybe_multi_book_or_series(test_case.upper()) == expected

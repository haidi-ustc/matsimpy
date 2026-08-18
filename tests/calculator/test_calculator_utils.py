from matsimpy.calculator.utils import clean_lines, micro_pyawk, str_delimited


def test_clean_lines_removes_comments_and_respects_modes():
    lines = ["  A = 1 # comment  ", "   ", "  indented  "]
    assert list(clean_lines(lines)) == ["A = 1", "indented"]
    assert list(clean_lines(lines, remove_empty_lines=False, rstrip_only=True)) == [
        "  A = 1",
        "",
        "  indented",
    ]


def test_str_delimited_formats_rows_exactly():
    assert str_delimited([["ENCUT", 520], ["ISMEAR", 0]], delimiter=" = ") == (
        "ENCUT = 520\nISMEAR = 0"
    )


def test_micro_pyawk_executes_predicate_and_action(tmp_path):
    path = tmp_path / "sample.out"
    path.write_text("skip 1\nvalue 2\nvalue 3\n")
    result = {"values": []}
    micro_pyawk(
        path,
        [
            (
                r"value (\d+)",
                lambda state, line: "3" not in line,
                lambda state, match: state["values"].append(int(match[1])),
            )
        ],
        result,
    )
    assert result == {"values": [2]}

import json
from pathlib import Path

import pytest
import yaml
from docutils.parsers.rst.directives.admonitions import Admonition, Note
from docutils.parsers.rst.directives.body import Rubric
from markdown_it import MarkdownIt

from myst_parser.parsers.directives import MarkupError, parse_directive_text
from myst_parser.parsers.options import TokenizeError
from myst_parser.parsers.options import to_items as options_to_items

FIXTURE_PATH = Path(__file__).parent.joinpath("fixtures")


@pytest.mark.param_file(FIXTURE_PATH / "option_parsing.yaml", "yaml")
def test_option_parsing(file_params):
    """Test parsing of directive options."""
    result = list(options_to_items(file_params.content))
    file_params.assert_expected(
        json.dumps(result, ensure_ascii=False, indent=2), rstrip_lines=True
    )


@pytest.mark.param_file(FIXTURE_PATH / "option_parsing_errors.yaml", "yaml")
def test_option_parsing_errors(file_params):
    """Test parsing of directive options."""
    try:
        list(options_to_items(file_params.content))
    except TokenizeError as err:
        result = str(err)
    else:
        result = "No error"
    file_params.assert_expected(result, rstrip_lines=True)


@pytest.mark.param_file(FIXTURE_PATH / "directive_parsing.txt")
def test_parsing(file_params):
    """Test parsing of directive text."""
    tokens = MarkdownIt("commonmark").parse(file_params.content)
    assert len(tokens) == 1 and tokens[0].type == "fence"
    name, *first_line = tokens[0].info.split(maxsplit=1)
    if name == "{note}":
        klass = Note
    elif name == "{admonition}":
        klass = Admonition
    else:
        raise AssertionError(f"Unknown directive: {name}")
    try:
        result = parse_directive_text(
            klass, first_line[0] if first_line else "", tokens[0].content, line=0
        )
    except MarkupError as err:
        outcome = f"error: {err}"
    else:
        outcome = yaml.safe_dump(
            {
                "arguments": result.arguments,
                "options": result.options,
                "body": result.body,
                "content_offset": result.body_offset,
                "warnings": result.warnings,
            },
            sort_keys=True,
        )
    file_params.assert_expected(outcome, rstrip_lines=True)


@pytest.mark.parametrize(
    "descript,klass,arguments,content", [("no content", Rubric, "", "a")]
)
def test_parsing_errors(descript, klass, arguments, content):
    with pytest.raises(MarkupError):
        parse_directive_text(klass, arguments, content)


def test_parsing_full_yaml():
    result = parse_directive_text(
        Note, "", "---\na: [1]\n---\ncontent", validate_options=False
    )
    assert not result.warnings
    assert result.options == {"a": [1]}
    assert result.body == ["content"]


def test_additional_options():
    """Allow additional options to be passed to a directive."""
    # this should be fine
    result = parse_directive_text(
        Note, "", "content", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["bar"]}
    assert result.body == ["content"]
    # body on first line should also be fine
    result = parse_directive_text(
        Note, "content", "other", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["bar"]}
    assert result.body == ["content", "other"]
    # additional option should not take precedence
    result = parse_directive_text(
        Note, "content", ":class: foo", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["foo"]}
    assert result.body == ["content"]
    # this should warn about the unknown option
    result = parse_directive_text(
        Note, "", "content", additional_options={"foo": "bar"}
    )
    assert len(result.warnings) == 1
    assert "Unknown option" in result.warnings[0][0]

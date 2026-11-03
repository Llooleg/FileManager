"""Тесты разбора JSON/XML (formats.py): глубина, XXE, billion laughs."""
import pytest

from FileManager.formats import parse_json, parse_xml, xml_to_str


class TestJson:
    def test_valid(self):
        assert parse_json('{"a": [1, 2, {"b": null}]}') == {"a": [1, 2, {"b": None}]}

    def test_too_deep_becomes_valueerror(self):
        raw = "[" * 20000 + "]" * 20000
        with pytest.raises(ValueError):
            parse_json(raw)


class TestXml:
    def test_valid(self):
        root = parse_xml(b"<root><item>1</item></root>")
        assert root.tag == "root" and root[0].text == "1"

    def test_doctype_forbidden(self):
        with pytest.raises(ValueError):
            parse_xml(b'<!DOCTYPE r [<!ENTITY x "y">]><r>&x;</r>')

    def test_billion_laughs_forbidden(self):
        evil = (b'<!DOCTYPE lolz [<!ENTITY lol "lol">'
                b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">]>'
                b"<r>&lol2;</r>")
        with pytest.raises(ValueError):
            parse_xml(evil)

    def test_invalid_xml(self):
        with pytest.raises(ValueError):
            parse_xml(b"<unclosed>")

    def test_xml_to_str_roundtrip(self):
        src = parse_xml(b"<root><item>1</item></root>")
        out = xml_to_str(src)
        assert xml_to_str(parse_xml(out.encode())).strip() == out.strip()

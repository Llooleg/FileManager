"""Безопасный разбор JSON и XML."""
import json
import xml.etree.ElementTree as ET
from xml.parsers import expat


def parse_json(raw: str):
    try:
        return json.loads(raw)
    except RecursionError:
        raise ValueError("JSON слишком глубоко вложен")


def parse_xml(raw: bytes):
    """DOCTYPE запрещён целиком: нет DTD -> нет XXE и billion laughs."""
    p = expat.ParserCreate()

    def forbid(*_):
        raise ValueError("DOCTYPE/ENTITY запрещены (защита от XXE и billion laughs)")

    p.StartDoctypeDeclHandler = forbid
    try:
        p.Parse(raw, True)
    except expat.ExpatError as e:
        raise ValueError(f"Невалидный XML: {e}")
    return ET.fromstring(raw)


def xml_to_str(root) -> str:
    ET.indent(root)
    return ET.tostring(root, encoding="unicode")

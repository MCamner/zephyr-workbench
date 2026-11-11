from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from zephyr.image_import import parse_image


def drawing(tmp_path, arrow=True, reverse=False):
    image = Image.new("RGB", (480, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 40, 160, 120), outline="black", width=2)
    draw.rectangle((320, 40, 460, 120), outline="black", width=2)
    draw.line((161, 80, 319, 80), fill="black", width=2)
    if arrow:
        points = (
            [(165, 80), (177, 73), (177, 87)]
            if reverse
            else [(315, 80), (303, 73), (303, 87)]
        )
        draw.polygon(points, fill="black")
    path = tmp_path / "diagram.png"
    image.save(path)
    return path


@pytest.mark.parametrize("reverse", [False, True])
def test_raster_boxes_and_arrow_direction(tmp_path, monkeypatch, reverse):
    monkeypatch.setattr(
        "zephyr.image_import.extract_text_from_image",
        lambda p: "Client" if "node-0" in str(p) else "Server",
    )
    result = parse_image(drawing(tmp_path, reverse=reverse))
    assert len(result.components) == 2
    flow = result.flows[0]
    assert (flow["source"], flow["target"]) == (
        ("Server", "Client") if reverse else ("Client", "Server")
    )
    assert result.warnings


def test_plain_line_does_not_invent_direction(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "zephyr.image_import.extract_text_from_image",
        lambda p: "Client" if "node-0" in str(p) else "Server",
    )
    result = parse_image(drawing(tmp_path, arrow=False))
    assert result.flows == []
    assert any("direction" in w for w in result.warnings)


def test_blank_image_fails_instead_of_returning_empty_model(tmp_path, monkeypatch):
    monkeypatch.setattr("zephyr.image_import.extract_text_from_image", lambda p: "")
    path = tmp_path / "blank.png"
    Image.new("RGB", (100, 100), "white").save(path)
    with pytest.raises(ValueError, match="rectangular"):
        parse_image(path)


def test_image_of_mermaid_source_still_supported(monkeypatch):
    monkeypatch.setattr(
        "zephyr.image_import.extract_text_from_image",
        lambda p: "graph TD\n A[Client]\n B[Server]\n A --> B",
    )
    assert len(parse_image(Path("syntax.png")).flows) == 1


def test_vertical_raster_arrow(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "zephyr.image_import.extract_text_from_image",
        lambda p: "Top" if "node-0" in str(p) else "Bottom",
    )
    image = Image.new("RGB", (200, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 20, 170, 110), outline="black", width=2)
    draw.rectangle((30, 290, 170, 380), outline="black", width=2)
    draw.line((100, 111, 100, 289), fill="black", width=2)
    draw.polygon([(100, 285), (92, 272), (108, 272)], fill="black")
    path = tmp_path / "vertical.png"
    image.save(path)
    result = parse_image(path)
    assert result.flows == [{"source": "Top", "target": "Bottom"}]

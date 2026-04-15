from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1100
HEIGHT = 700
PADDING = 28
TERMINAL_HEIGHT = 430
PREVIEW_TOP = 490
OUTPUT_PATH = Path("docs/demo.gif")


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Menlo Bold.ttf",
                "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Menlo Regular.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
            "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        ]
    )

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)

    return ImageFont.load_default()


FONT = load_font(20)
FONT_SMALL = load_font(17)
FONT_TITLE = load_font(24, bold=True)


INTRO_BLOCK = [
    "$ python -m zephyr.cli init --minimal",
    "Zephyr Init Wizard",
    "Mode: minimal V1",
    "",
    "Architecture name: secure-workplace",
    "Description []: Secure workplace access model",
    "Add component? [Y/n]: y",
    "Name: user",
    "Type [...]: actor",
    "Domain [...] [business]:",
    "...",
    "Saved: examples/secure-workplace.yaml",
    "Validation succeeded.",
]

RUN_BLOCK = [
    "$ python -m zephyr.cli run examples/secure-workplace.yaml",
    "Warnings:",
    "- W1: only one access-gateway detected (citrix-gateway)",
    "",
    "Validation passed with warnings",
    "",
    "Architecture: secure-workplace",
    "Components: 6",
    "Flows: 5",
    "Risks: 2",
    "",
    "Risks:",
    "- [HIGH] R1: Citrix Gateway single point of failure",
    "- [MEDIUM] R2: MFA dependency not clearly documented",
    "",
    "Diagram generated: output/secure-workplace.mmd",
]


def create_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#0b1220")
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        blend = y / HEIGHT
        r = int(11 + (22 - 11) * blend)
        g = int(18 + (35 - 18) * blend)
        b = int(32 + (56 - 32) * blend)
        draw.line((0, y, WIDTH, y), fill=(r, g, b))
    return image


def draw_terminal(draw: ImageDraw.ImageDraw, lines: list[str], typed_chars: int | None = None) -> None:
    x0 = PADDING
    y0 = PADDING
    x1 = WIDTH - PADDING
    y1 = TERMINAL_HEIGHT

    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill="#111827", outline="#334155", width=2)
    draw.rounded_rectangle((x0, y0, x1, y0 + 42), radius=22, fill="#0f172a")
    draw.rectangle((x0, y0 + 22, x1, y0 + 42), fill="#0f172a")
    draw.text((x0 + 24, y0 + 10), "zephyr demo", fill="#e5e7eb", font=FONT_TITLE)

    for idx, color in enumerate(("#fb7185", "#fbbf24", "#34d399")):
        cx = x1 - 90 + idx * 24
        cy = y0 + 20
        draw.ellipse((cx, cy, cx + 12, cy + 12), fill=color)

    content_y = y0 + 62
    line_height = 25
    for i, line in enumerate(lines):
        text = line
        if typed_chars is not None and i == 0:
            text = line[:typed_chars]
            if typed_chars < len(line):
                text += "▋"
        fill = "#93c5fd" if text.startswith("$ ") else "#e5e7eb"
        if text == "...":
            fill = "#94a3b8"
        draw.text((x0 + 22, content_y + i * line_height), text, fill=fill, font=FONT)


def draw_preview(draw: ImageDraw.ImageDraw, visible: bool) -> None:
    x0 = PADDING
    y0 = PREVIEW_TOP
    x1 = WIDTH - PADDING
    y1 = HEIGHT - PADDING

    draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill="#0f172a", outline="#334155", width=2)
    draw.text((x0 + 24, y0 + 18), "Mermaid preview", fill="#e5e7eb", font=FONT_TITLE)
    draw.text((x1 - 310, y0 + 22), "output/secure-workplace.mmd", fill="#94a3b8", font=FONT_SMALL)

    if not visible:
        draw.text((x0 + 24, y0 + 70), "Diagram appears after `zephyr run` completes.", fill="#94a3b8", font=FONT)
        return

    nodes = {
        "user": ((120, 100), "user", "#1d4ed8"),
        "igel": ((300, 100), "igel", "#0f766e"),
        "gateway": ((520, 100), "citrix-gateway", "#7c3aed"),
        "directory": ((770, 100), "active-directory", "#b45309"),
        "mfa": ((770, 165), "mfa", "#be123c"),
        "entra": ((960, 100), "entra-id", "#0f766e"),
    }

    offset_x = x0 + 20
    offset_y = y0 + 42

    def box(center: tuple[int, int], label: str, color: str) -> tuple[int, int, int, int]:
        cx, cy = center
        left = offset_x + cx - 70
        top = offset_y + cy - 18
        right = offset_x + cx + 70
        bottom = offset_y + cy + 18
        draw.rounded_rectangle((left, top, right, bottom), radius=12, fill=color, outline="#e2e8f0", width=2)
        draw.text((left + 10, top + 8), label, fill="#f8fafc", font=FONT_SMALL)
        return left, top, right, bottom

    boxes = {name: box(center, label, color) for name, (center, label, color) in nodes.items()}

    def arrow(src: str, dst: str, label: str) -> None:
        sx = boxes[src][2]
        sy = (boxes[src][1] + boxes[src][3]) // 2
        dx = boxes[dst][0]
        dy = (boxes[dst][1] + boxes[dst][3]) // 2
        draw.line((sx, sy, dx, dy), fill="#cbd5e1", width=3)
        draw.polygon([(dx, dy), (dx - 10, dy - 5), (dx - 10, dy + 5)], fill="#cbd5e1")
        tx = (sx + dx) // 2 - 20
        ty = min(sy, dy) - 24
        draw.text((tx, ty), label, fill="#94a3b8", font=FONT_SMALL)

    arrow("user", "igel", "signs in")
    arrow("igel", "gateway", "starts session")
    arrow("gateway", "directory", "validates")
    arrow("directory", "mfa", "triggers")
    arrow("directory", "entra", "sync")


def frame(lines: list[str], typed_chars: int | None = None, show_preview: bool = False) -> Image.Image:
    image = create_background()
    draw = ImageDraw.Draw(image)
    draw_terminal(draw, lines, typed_chars=typed_chars)
    draw_preview(draw, visible=show_preview)
    return image


def build_frames() -> tuple[list[Image.Image], list[int]]:
    frames: list[Image.Image] = []
    durations: list[int] = []

    command_1 = INTRO_BLOCK[0]
    for progress in range(2, len(command_1) + 1, 5):
        frames.append(frame(INTRO_BLOCK, typed_chars=progress, show_preview=False))
        durations.append(70)

    for _ in range(6):
        frames.append(frame(INTRO_BLOCK, typed_chars=None, show_preview=False))
        durations.append(220)

    command_2 = RUN_BLOCK[0]
    for progress in range(2, len(command_2) + 1, 6):
        lines = [RUN_BLOCK[0], *INTRO_BLOCK[1:5]]
        frames.append(frame(lines, typed_chars=progress, show_preview=False))
        durations.append(60)

    for _ in range(10):
        frames.append(frame(RUN_BLOCK, typed_chars=None, show_preview=True))
        durations.append(220)

    return frames, durations


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames, durations = build_frames()
    frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

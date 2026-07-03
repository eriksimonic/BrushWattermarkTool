from PIL import Image

LEGACY_COLORS = {
    "white": "#ffffff",
    "black": "#000000",
    "gray": "#808080",
    "grey": "#808080",
}

FIXED_SWATCH_RGB = (
    (255, 255, 255),
    (128, 128, 128),
    (0, 0, 0),
)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def parse_rgb(color: str) -> tuple[int, int, int]:
    normalized = normalize_text_color(color)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def normalize_text_color(value: str | None, fallback: str = "#ffffff") -> str:
    if value is None:
        return fallback
    raw = str(value).strip().lower()
    if raw in LEGACY_COLORS:
        return LEGACY_COLORS[raw]
    if raw.startswith("#") and len(raw) == 7:
        try:
            int(raw[1:], 16)
        except ValueError:
            return fallback
        return raw
    return fallback


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def closest_swatch_color(color: str, swatches: list[str]) -> str:
    if not swatches:
        return normalize_text_color(color)
    target = parse_rgb(color)
    best = swatches[0]
    best_dist = color_distance(target, parse_rgb(best))
    for candidate in swatches[1:]:
        dist = color_distance(target, parse_rgb(candidate))
        if dist < best_dist:
            best = candidate
            best_dist = dist
    return best


def color_short(color: str) -> str:
    return normalize_text_color(color)[1:4]


def extract_image_palette(image: Image.Image, count: int = 8) -> list[tuple[int, int, int]]:
    sample = image.convert("RGB")
    width, height = sample.size
    target = 128
    if width >= height:
        new_w = target
        new_h = max(1, int(height * target / max(1, width)))
    else:
        new_h = target
        new_w = max(1, int(width * target / max(1, height)))
    sample = sample.resize((new_w, new_h), Image.Resampling.LANCZOS)
    quantized = sample.quantize(colors=max(2, count), method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    colors: list[tuple[int, int, int]] = []
    for index in range(count):
        offset = index * 3
        if offset + 2 >= len(palette):
            break
        rgb = (palette[offset], palette[offset + 1], palette[offset + 2])
        if rgb not in colors:
            colors.append(rgb)
    fallback = [(64, 64, 64), (128, 128, 128), (192, 192, 192), (96, 96, 96)]
    for rgb in fallback:
        if len(colors) >= count:
            break
        if rgb not in colors:
            colors.append(rgb)
    return colors[:count]


def build_swatch_palette(image: Image.Image) -> list[str]:
    sampled = extract_image_palette(image, count=8)
    image_swatches: list[str] = []
    for rgb in sampled:
        hex_color = rgb_to_hex(rgb)
        if hex_color not in image_swatches:
            image_swatches.append(hex_color)
    fallback = [(64, 64, 64), (96, 96, 96), (160, 160, 160), (192, 192, 192), (32, 32, 32), (48, 48, 48)]
    for rgb in fallback:
        if len(image_swatches) >= 8:
            break
        hex_color = rgb_to_hex(rgb)
        if hex_color not in image_swatches:
            image_swatches.append(hex_color)
    while len(image_swatches) < 8:
        tone = 32 + len(image_swatches) * 24
        hex_color = rgb_to_hex((tone, tone, tone))
        if hex_color not in image_swatches:
            image_swatches.append(hex_color)
    fixed = [rgb_to_hex(rgb) for rgb in FIXED_SWATCH_RGB]
    return image_swatches[:8] + fixed

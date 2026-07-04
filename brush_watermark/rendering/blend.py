from PIL import Image, ImageChops

BLEND_MODE_CHOICES: list[tuple[str, str]] = [
    ("normal", "Normal"),
    ("soft_light", "Soft light"),
    ("lighten", "Lighten"),
    ("darken", "Darken"),
    ("difference", "Difference"),
    ("overlay", "Overlay"),
    ("screen", "Screen"),
    ("multiply", "Multiply"),
    ("hard_light", "Hard light"),
]

VALID_BLEND_MODES = {mode for mode, _ in BLEND_MODE_CHOICES}
DEFAULT_BLEND_MODE = "soft_light"


def normalize_blend_mode(value: str | None, fallback: str = DEFAULT_BLEND_MODE) -> str:
    mode = str(value or fallback).strip().lower()
    if mode in VALID_BLEND_MODES:
        return mode
    return fallback


def blend_mode_label(mode: str) -> str:
    for key, label in BLEND_MODE_CHOICES:
        if key == mode:
            return label
    return mode.replace("_", " ").title()


def blend_mode_short(mode: str) -> str:
    short_names = {
        "normal": "norm",
        "soft_light": "soft",
        "lighten": "litn",
        "darken": "drkn",
        "difference": "diff",
        "overlay": "ovrl",
        "screen": "scrn",
        "multiply": "mult",
        "hard_light": "hard",
    }
    return short_names.get(mode, mode[:4])


def _blend_rgb(base_rgb: Image.Image, overlay_rgb: Image.Image, mode: str) -> Image.Image:
    if mode == "lighten":
        return ImageChops.lighter(base_rgb, overlay_rgb)
    if mode == "darken":
        return ImageChops.darker(base_rgb, overlay_rgb)
    if mode == "difference":
        return ImageChops.difference(base_rgb, overlay_rgb)
    if mode == "screen":
        return ImageChops.screen(base_rgb, overlay_rgb)
    if mode == "multiply":
        return ImageChops.multiply(base_rgb, overlay_rgb)
    if mode == "overlay":
        return ImageChops.overlay(base_rgb, overlay_rgb)
    if mode == "soft_light":
        return ImageChops.soft_light(base_rgb, overlay_rgb)
    if mode == "hard_light":
        return ImageChops.hard_light(base_rgb, overlay_rgb)
    raise ValueError(f"Unsupported blend mode: {mode}")


def _scaled_mask(mask: Image.Image, strength: float) -> Image.Image:
    strength = max(0.0, min(1.0, strength))
    if strength >= 0.999:
        return mask
    scale = int(round(strength * 255))
    return mask.point(lambda value: int(value * scale / 255))


def overlay_rgb_layer(size: tuple[int, int], text_color: str) -> Image.Image:
    from brush_watermark.rendering.colors import parse_rgb

    return Image.new("RGB", size, parse_rgb(text_color))


def composite_rgba_layer(
    base: Image.Image,
    layer_rgba: Image.Image,
    blend_mode: str,
    strength: float,
) -> Image.Image:
    mode = normalize_blend_mode(blend_mode)
    strength = max(0.0, min(1.0, strength))
    if strength <= 0.0:
        return base.convert("RGBA")

    alpha = layer_rgba.getchannel("A")
    if alpha.getbbox() is None:
        return base.convert("RGBA")

    result = base.convert("RGBA")
    weight = _scaled_mask(alpha, strength)

    if mode == "normal":
        tinted = layer_rgba.copy()
        tinted.putalpha(weight)
        result.alpha_composite(tinted)
        return result

    base_rgb = result.convert("RGB")
    overlay_rgb = layer_rgba.convert("RGB")
    blended_rgb = _blend_rgb(base_rgb, overlay_rgb, mode)
    mixed_rgb = Image.composite(blended_rgb, base_rgb, weight)
    return Image.merge("RGBA", (*mixed_rgb.split(), result.getchannel("A")))


def composite_watermark_layer(
    base: Image.Image,
    watermark_rgba: Image.Image,
    text_color: str,
    blend_mode: str,
    strength: float,
) -> Image.Image:
    mode = normalize_blend_mode(blend_mode)
    strength = max(0.0, min(1.0, strength))
    if strength <= 0.0:
        return base

    mask = watermark_rgba.getchannel("A")
    if mask.getbbox() is None:
        return base

    result = base.convert("RGBA")
    weight = _scaled_mask(mask, strength)

    if mode == "normal":
        from brush_watermark.rendering.colors import parse_rgb

        tinted = Image.new("RGBA", result.size, (0, 0, 0, 0))
        r, g, b = parse_rgb(text_color)
        tinted.paste((r, g, b, 255), mask=weight)
        result.alpha_composite(tinted)
        return result

    base_rgb = result.convert("RGB")
    overlay_rgb = overlay_rgb_layer(result.size, text_color)
    blended_rgb = _blend_rgb(base_rgb, overlay_rgb, mode)
    mixed_rgb = Image.composite(blended_rgb, base_rgb, weight)
    result = Image.merge("RGBA", (*mixed_rgb.split(), result.getchannel("A")))
    return result

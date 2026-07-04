__all__ = [
    "FONT_SIZE_RATIO",
    "TEXT_SPAN_FILL",
    "apply_erase_mask",
    "build_glyph_cache",
    "composite_watermark",
    "compute_text_span",
    "draw_text_on_path",
    "find_font_path",
    "fitted_font_size",
    "font_candidates",
    "font_size_from_brush",
    "load_font",
    "make_preview_image",
    "make_stroke_mask",
    "make_watermark_layer",
    "text_dimensions",
]

_LAZY_EXPORTS = {
    "FONT_SIZE_RATIO": "brush_watermark.rendering.fonts",
    "TEXT_SPAN_FILL": "brush_watermark.rendering.fonts",
    "find_font_path": "brush_watermark.rendering.fonts",
    "font_candidates": "brush_watermark.rendering.fonts",
    "font_size_from_brush": "brush_watermark.rendering.fonts",
    "load_font": "brush_watermark.rendering.fonts",
    "apply_erase_mask": "brush_watermark.rendering.masks",
    "make_stroke_mask": "brush_watermark.rendering.masks",
    "build_glyph_cache": "brush_watermark.rendering.watermark",
    "composite_watermark": "brush_watermark.rendering.watermark",
    "compute_text_span": "brush_watermark.rendering.watermark",
    "draw_text_on_path": "brush_watermark.rendering.watermark",
    "fitted_font_size": "brush_watermark.rendering.watermark",
    "make_preview_image": "brush_watermark.rendering.watermark",
    "make_watermark_layer": "brush_watermark.rendering.watermark",
    "text_dimensions": "brush_watermark.rendering.watermark",
}


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name = _LAZY_EXPORTS[name]
    import importlib

    module = importlib.import_module(module_name)
    return getattr(module, name)

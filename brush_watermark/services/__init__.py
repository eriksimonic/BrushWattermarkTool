__all__ = ["Document"]


def __getattr__(name: str):
    if name == "Document":
        from brush_watermark.services.document import Document

        return Document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

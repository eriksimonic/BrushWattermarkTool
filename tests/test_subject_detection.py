"""Tests for the ONNX-backed subject saliency detector."""
import numpy as np
from PIL import Image, ImageDraw

from brush_watermark.services.subject_detection import saliency_map, subject_protect_mask


def _image_with_bright_blob():
    img = Image.new("RGB", (400, 300), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.ellipse([150, 100, 250, 200], fill=(230, 210, 190))
    return img


class TestSaliencyMap:
    def test_matches_source_size_and_mode(self):
        img = _image_with_bright_blob()
        sal = saliency_map(img)
        assert sal.size == img.size
        assert sal.mode == "L"

    def test_blob_is_more_salient_than_flat_background(self):
        img = _image_with_bright_blob()
        sal = saliency_map(img)
        center = sal.getpixel((200, 150))
        corner = sal.getpixel((10, 10))
        assert center > corner


class TestSubjectProtectMask:
    def test_matches_source_size_and_mode(self):
        img = _image_with_bright_blob()
        mask = subject_protect_mask(img)
        assert mask.size == img.size
        assert mask.mode == "L"

    def test_protects_the_blob_region(self):
        img = _image_with_bright_blob()
        mask = subject_protect_mask(img)
        assert mask.getpixel((200, 150)) == 255

    def test_leaves_far_corners_unprotected(self):
        img = _image_with_bright_blob()
        mask = subject_protect_mask(img)
        assert mask.getpixel((5, 5)) == 0
        assert mask.getpixel((395, 295)) == 0

    def test_larger_margin_ratio_grows_the_protected_area(self):
        img = _image_with_bright_blob()
        tight = subject_protect_mask(img, margin_ratio=0.02)
        loose = subject_protect_mask(img, margin_ratio=0.30)
        tight_count = int(np.count_nonzero(np.asarray(tight)))
        loose_count = int(np.count_nonzero(np.asarray(loose)))
        assert loose_count > tight_count

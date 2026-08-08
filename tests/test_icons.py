from brush_watermark.ui.icons import _recolor_svg


class TestRecolorSvg:
    def test_replaces_current_color(self):
        svg = '<svg><path stroke="currentColor" d="M0 0" /></svg>'
        assert _recolor_svg(svg, "#3D7FFF") == '<svg><path stroke="#3D7FFF" d="M0 0" /></svg>'

    def test_replaces_multiple_occurrences(self):
        svg = '<svg stroke="currentColor"><path stroke="currentColor" /></svg>'
        result = _recolor_svg(svg, "#FFFFFF")
        assert "currentColor" not in result
        assert result.count("#FFFFFF") == 2

    def test_no_op_when_placeholder_absent(self):
        svg = '<svg><path stroke="#000000" d="M0 0" /></svg>'
        assert _recolor_svg(svg, "#3D7FFF") == svg

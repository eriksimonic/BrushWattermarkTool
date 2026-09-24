# UI redesign — deferred features

The redesign (docs/superpowers/specs/2026-09-24-ui-redesign-design.md) shows these controls, but the app has no feature behind them yet. They were left out of the UI rather than drawn as dead buttons. Decide per item whether to build it.

| Control in the design | Where it would go | What's missing |
|---|---|---|
| Undo / Redo | Top bar, centre-left | No edit history in `Document` |
| Pan tool (H), Space-to-pan | Tool rail | No free panning; the canvas is fit or 1:1 with scrollbars |
| Zoom tool (Z), zoom −/+, editable % | Tool rail; zoom pill | Only Fit / 1:1 exist; % is read-only |
| Pick colour from image (I) | Brush swatches, dashed "+" swatch | No eyedropper on the canvas |
| Add images tile | Filmstrip, after the thumbnails | Images only arrive via CLI/Explorer/picker at launch |
| Prev / next image buttons, Ctrl+←/→ | Filmstrip title column; footer hint | Only clicking a thumbnail switches images |
| Copy serial button | Top bar serial chip | Serial is display-only |
| Edit menu | Top bar menus | Nothing to put in it until undo/redo exists |
| Ctrl+S shortcut | Save menu "Ctrl S" badge | No keyboard shortcut for saving |
| Del deletes the selected layer | Layers "Delete" button badge; footer hint | Del only removes a Path anchor |

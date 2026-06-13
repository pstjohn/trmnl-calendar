# LaTeX Renderer Backend Plan

## Goal

Evaluate and, if worthwhile, add a LaTeX-based renderer backend for the TRMNL weekly and monthly calendar images. The near-term motivation is better small-text shaping and rasterization than Pillow provides for Roboto Flex in dense month event rows.

This is a deferred plan. Do not start implementation until explicitly requested.

## Proposed Shape

- Keep `calendar_data.py` as the source of normalized weekly/month event data.
- Add a new renderer module, likely `src/trmnl_weekly_calendar/latex_render.py`.
- Keep the current Pillow renderer as the default while the LaTeX backend is experimental.
- Add an environment switch such as `TRMNL_RENDER_BACKEND=pillow|latex`.
- Reuse the existing server cache and 4-bit PNG encoder after rasterization.

## Rendering Pipeline

1. Convert normalized calendar data into a `.tex` document.
2. Compile with LuaLaTeX or XeLaTeX.
3. Rasterize the generated PDF to `1872x1404`.
4. Convert/raster output to grayscale if needed.
5. Encode with the existing true 4-bit grayscale PNG encoder.

Preferred raster path:

```text
.tex -> .pdf -> pdftoppm -> Pillow/Image -> encode_png_grayscale_4bit
```

## Dependencies

Current machine has `pdftoppm`, but no TeX engine was found. A backend would need:

- `lualatex` or `xelatex`
- LaTeX packages for page geometry and drawing, likely `fontspec`, `tikz`, and `xcolor`
- Existing vendored fonts in `assets/fonts/`

Use LuaLaTeX/XeLaTeX because `fontspec` can load local font files directly.

## Prototype Order

1. Prototype month view first.
   Month rendering has the most visible small-text issues and is simpler than the weekly time-grid layout.

2. Match page geometry exactly.
   Use a PDF page size equivalent to `1872 x 1404` pixels at the chosen raster DPI, then verify the output image dimensions exactly.

3. Recreate month structure.
   Draw title, weekday row, 5-week grid, current-day treatment, event pills, and overflow labels.

4. Test text quality.
   Use problematic strings such as `Summer`, `Trumpet`, `Corbin`, and real live calendar event titles.

5. Wire behind backend flag.
   Keep Pillow as default until the LaTeX output is visually and operationally stable.

6. Port weekly view only if month results justify the dependency cost.

## Open Design Decisions

- Whether to keep Roboto Flex or switch month event text to a static font with more reliable small-size rasterization.
- Whether to use TikZ directly or generate a simpler LaTeX table/layout with positioned boxes.
- Whether the service host should install a TeX distribution system-wide or use a narrower bundled/runtime approach.
- How aggressively to cache intermediate PDFs during manual iteration.

## Risks

- TeX install size and startup time are much larger than the current Pillow-only renderer.
- Forced refresh requests will be slower.
- Font variable-axis behavior may still differ unless static font instances are used.
- LaTeX escaping and text overflow handling must be implemented carefully for arbitrary calendar titles.

## Verification Checklist

- `python3 -m compileall src tests`
- Existing unit tests pass.
- Month output is exactly `1872x1404`.
- Weekly output is exactly `1872x1404` if/when ported.
- Live `/month/image.png` remains `Content-Type: image/png` with integer `Content-Length`.
- Encoded PNG is true 4-bit grayscale: IHDR bit depth `4`, color type `0`.
- `/trmnl.json` stays small and fast by relying on cached rendered bytes.

"""Render Vega-Lite specifications to PNG images using vl-convert-python."""

import json
import os
import tempfile


def render_vegalite_to_png(
    spec: dict | str,
    output_path: str = None,
    scale: float = 2.0
) -> str:
    """
    Render Vega-Lite specification to PNG image.

    Args:
        spec: Vega-Lite JSON specification (dict or JSON string)
        output_path: Output PNG file path. If None, creates temp file.
        scale: Scale factor for higher resolution (default: 2x)

    Returns:
        str: Path to generated PNG file

    Dependencies:
        - vl-convert-python: Native Vega rendering

    Example:
        >>> spec = {"mark": "bar", "encoding": {...}}
        >>> render_vegalite_to_png(spec, "chart.png")
        "chart.png"

    Raises:
        ImportError: If vl-convert-python is not installed
        ValueError: If spec is invalid
    """
    try:
        import vl_convert as vlc
    except ImportError:
        raise ImportError(
            "vl-convert-python is required for chart rendering. "
            "Install with: pip install vl-convert-python"
        )

    # Parse spec if string
    if isinstance(spec, str):
        spec = json.loads(spec)

    # Generate output path if not provided
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Render to PNG
    png_data = vlc.vegalite_to_png(
        vl_spec=spec,
        scale=scale
    )

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(png_data)

    return output_path


def render_vegalite_to_svg(spec: dict | str, output_path: str = None) -> str:
    """
    Render Vega-Lite specification to SVG image.

    Args:
        spec: Vega-Lite JSON specification (dict or JSON string)
        output_path: Output SVG file path. If None, creates temp file.

    Returns:
        str: Path to generated SVG file
    """
    try:
        import vl_convert as vlc
    except ImportError:
        raise ImportError(
            "vl-convert-python is required for chart rendering. "
            "Install with: pip install vl-convert-python"
        )

    if isinstance(spec, str):
        spec = json.loads(spec)

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix='.svg')
        os.close(fd)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    svg_data = vlc.vegalite_to_svg(vl_spec=spec)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_data)

    return output_path


def get_chart_dimensions(spec: dict | str) -> tuple:
    """
    Extract chart dimensions from Vega-Lite spec.

    Args:
        spec: Vega-Lite specification

    Returns:
        tuple: (width, height) or (None, None) if not specified
    """
    if isinstance(spec, str):
        spec = json.loads(spec)

    width = spec.get('width')
    height = spec.get('height')

    return width, height


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Render Vega-Lite spec to image")
    parser.add_argument("input", help="Input Vega-Lite JSON file")
    parser.add_argument("-o", "--output", help="Output image file (PNG or SVG)")
    parser.add_argument("-s", "--scale", type=float, default=2.0,
                        help="Scale factor for PNG (default: 2.0)")
    parser.add_argument("--svg", action="store_true", help="Output SVG instead of PNG")

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        spec = json.load(f)

    if args.svg:
        output = args.output or args.input.replace('.json', '.svg')
        result = render_vegalite_to_svg(spec, output)
    else:
        output = args.output or args.input.replace('.json', '.png')
        result = render_vegalite_to_png(spec, output, args.scale)

    print(f"Rendered to: {result}")

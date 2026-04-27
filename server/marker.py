from pathlib import Path

from PIL import Image, ImageDraw


def mark_click(source: Path, destination: Path, x: float, y: float) -> None:
    with Image.open(source).convert("RGBA") as image:
        width, height = image.size
        center = (int(x * width), int(y * height))
        radius = max(18, int(width * 0.04))

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        bbox = [
            center[0] - radius,
            center[1] - radius,
            center[0] + radius,
            center[1] + radius,
        ]
        draw.ellipse(bbox, outline=(255, 255, 255, 235), width=max(4, radius // 6))
        draw.ellipse(bbox, outline=(230, 38, 38, 210), width=max(3, radius // 8))
        dot = max(4, radius // 7)
        draw.ellipse(
            [center[0] - dot, center[1] - dot, center[0] + dot, center[1] + dot],
            fill=(230, 38, 38, 230),
        )
        Image.alpha_composite(image, overlay).convert("RGB").save(destination, "PNG")

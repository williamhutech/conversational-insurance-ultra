"""Post-processing utilities for DeepSeek-OCR outputs."""

from __future__ import annotations

import ast
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


@dataclass
class Detection:
    """Container storing a detection span and its bounding boxes."""

    raw: str
    label: str
    boxes: List[Tuple[float, float, float, float]]


# Regex capturing ``<|ref|>label<|/ref|><|det|>[[x1,y1,x2,y2], ...]<|/det|>`` spans.
_DETECTION_PATTERN = re.compile(
    r"(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)",
    re.DOTALL,
)


def parse_detections(text: str) -> List[Detection]:
    """Extract detection metadata from the generated text."""

    detections: List[Detection] = []
    for full, label, coords in _DETECTION_PATTERN.findall(text):
        label_clean = label.strip()
        boxes: List[Tuple[float, float, float, float]] = []

        try:
            parsed = ast.literal_eval(coords.strip())
        except (SyntaxError, ValueError):
            parsed = []

        if isinstance(parsed, (list, tuple)):
            for item in parsed:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) == 4
                    and all(isinstance(val, (int, float)) for val in item)
                ):
                    values = tuple(float(val) for val in item)
                    boxes.append(
                        (
                            values[0],
                            values[1],
                            values[2],
                            values[3],
                        )
                    )

        detections.append(Detection(raw=full, label=label_clean, boxes=boxes))

    return detections


def scale_box(
    box: Tuple[float, float, float, float],
    width: int,
    height: int,
) -> Tuple[int, int, int, int]:
    """Scale bbox coordinates from ``[0, 999]`` space into image pixels."""

    if width <= 0 or height <= 0:
        return 0, 0, 0, 0

    x1, y1, x2, y2 = box
    scale = 999.0
    left = max(0, min(width, int(round(x1 / scale * width))))
    top = max(0, min(height, int(round(y1 / scale * height))))
    right = max(0, min(width, int(round(x2 / scale * width))))
    bottom = max(0, min(height, int(round(y2 / scale * height))))
    return left, top, right, bottom


def save_image_crops(
    image: Image.Image,
    detections: Sequence[Detection],
    images_dir: Path,
) -> Dict[str, str]:
    """Persist detected ``image`` regions and return replacement markdown snippets."""

    images_dir.mkdir(parents=True, exist_ok=True)
    width, height = image.size
    counter = 0
    replacements: Dict[str, str] = {}

    for detection in detections:
        if detection.label.lower() != "image":
            continue

        replacement = ""
        for box in detection.boxes:
            left, top, right, bottom = scale_box(box, width, height)
            if right <= left or bottom <= top:
                continue
            crop = image.crop((left, top, right, bottom))
            crop_path = images_dir / f"{counter}.jpg"
            crop.save(crop_path)
            replacement = f"![](images/{counter}.jpg)\n"
            counter += 1
            break

        replacements[detection.raw] = replacement

    return replacements


def annotate_image(
    image: Image.Image,
    detections: Sequence[Detection],
) -> Image.Image:
    """Draw bounding boxes and labels on a copy of the image."""

    annotated = image.copy()
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(annotated)
    overlay_draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    palette = [
        (229, 57, 53),
        (30, 136, 229),
        (67, 160, 71),
        (255, 179, 0),
        (142, 36, 170),
        (0, 150, 136),
    ]

    width, height = annotated.size
    for idx, detection in enumerate(detections):
        color = palette[idx % len(palette)]
        fill = (*color, 40)
        line_width = 4 if detection.label.lower() == "title" else 2

        for box in detection.boxes:
            left, top, right, bottom = scale_box(box, width, height)
            if right <= left or bottom <= top:
                continue
            draw.rectangle([left, top, right, bottom], outline=color, width=line_width)
            overlay_draw.rectangle([left, top, right, bottom], fill=fill)

            label_text = detection.label or "text"
            text_bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = left
            text_y = max(0, top - text_height - 2)
            draw.rectangle(
                [text_x, text_y, text_x + text_width + 4, text_y + text_height + 2],
                fill=(255, 255, 255),
            )
            draw.text((text_x + 2, text_y + 1), label_text, font=font, fill=color)

    annotated.paste(overlay, (0, 0), overlay)
    return annotated


def render_markdown(
    raw_text: str,
    detections: Sequence[Detection],
    image_replacements: Dict[str, str],
) -> str:
    """Convert the raw model output into cleaned markdown."""

    cleaned = raw_text
    for detection in detections:
        if detection.label.lower() == "image":
            replacement = image_replacements.get(detection.raw, "")
        else:
            replacement = ""
        cleaned = cleaned.replace(detection.raw, replacement, 1)

    cleaned = cleaned.replace("<｜end▁of▁sentence｜>", "")
    cleaned = cleaned.replace("\\coloneqq", ":=")
    cleaned = cleaned.replace("\\eqqcolon", "=:")
    return cleaned.strip()


def save_ocr_outputs(image: Image.Image, raw_text: str, output_dir: Path) -> str:
    """Persist markdown, crops, and annotated preview for a single page."""

    detections = parse_detections(raw_text)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"

    image_rgb = image.convert("RGB")
    replacements = save_image_crops(image_rgb, detections, images_dir)
    annotated = (
        annotate_image(image_rgb, detections) if detections else image_rgb.copy()
    )
    annotated.save(output_dir / "result_with_boxes.jpg")

    markdown = render_markdown(raw_text, detections, replacements)
    (output_dir / "result.md").write_text(markdown + "\n", encoding="utf-8")

    return markdown


__all__ = [
    "Detection",
    "parse_detections",
    "scale_box",
    "save_image_crops",
    "annotate_image",
    "render_markdown",
    "save_ocr_outputs",
]

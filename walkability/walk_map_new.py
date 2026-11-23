"""Render the original hallway score grid as a Gazebo floor texture."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import yaml


COLORS = {
    1.0: (102, 204, 102),
    0.7: (255, 204, 51),
    0.4: (255, 102, 0),
    0.1: (204, 0, 102),
    0.0: (102, 178, 255),
}
CELL_PIXELS = 100
GRID_COLOR = (128, 128, 128)


def render(grid_file, output_file):
    grid = yaml.safe_load(grid_file.read_text())["walkability_map"]
    scores = np.asarray(grid["scores"])
    expected_shape = (grid["grid_height"], grid["grid_width"])
    if scores.shape != expected_shape:
        raise ValueError(f"Expected score grid shape {expected_shape}, got {scores.shape}")

    # The YAML starts at minimum world Y. The texture starts at maximum Y.
    colors = np.array([[COLORS[score] for score in row] for row in scores[::-1]], dtype=np.uint8)
    pixels = colors.repeat(CELL_PIXELS, axis=0).repeat(CELL_PIXELS, axis=1)
    pixels[::CELL_PIXELS, :, :] = GRID_COLOR
    pixels[:, ::CELL_PIXELS, :] = GRID_COLOR
    output_file.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(output_file)


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, default=directory / "hallway_scores.yaml")
    parser.add_argument("--output", type=Path, default=directory / "generated/walkability_map.png")
    args = parser.parse_args()
    render(args.scores, args.output)

"""Hide laser beams in the temporary PMB2 demo container."""

import sys
from pathlib import Path
from xml.dom import minidom


LASER_SENSOR_TYPES = {"ray", "gpu_ray", "lidar", "gpu_lidar"}


def hide_laser_beams(package_directories):
    found_laser = False
    visited = set()
    for directory in package_directories:
        for source in sorted(directory.rglob("*.xacro")):
            source = source.resolve()
            if source in visited:
                continue
            visited.add(source)
            text = source.read_text()
            if "<sensor" not in text or "<visualize" not in text:
                continue
            document = minidom.parseString(text)
            changed = False
            for sensor in document.getElementsByTagName("sensor"):
                sensor_type = sensor.getAttribute("type")
                child_elements = {
                    child.tagName: child
                    for child in sensor.childNodes
                    if child.nodeType == child.ELEMENT_NODE
                }
                if sensor_type not in LASER_SENSOR_TYPES and not (
                    LASER_SENSOR_TYPES & child_elements.keys()
                ):
                    continue
                found_laser = True
                visualize = child_elements.get("visualize")
                if visualize is None:
                    # SDF disables sensor visualization by default.
                    continue
                if visualize.firstChild is not None and visualize.firstChild.nodeValue == "false":
                    continue
                while visualize.firstChild is not None:
                    visualize.removeChild(visualize.firstChild)
                visualize.appendChild(document.createTextNode("false"))
                changed = True
            if changed:
                source.write_text(document.toxml(encoding="utf-8").decode("utf-8"))

    if not found_laser:
        print("No explicit laser visualization settings found in the PMB2 description packages.", file=sys.stderr)


if __name__ == "__main__":
    hide_laser_beams(map(Path, sys.argv[1:]))

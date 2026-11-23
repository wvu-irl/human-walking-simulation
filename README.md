# Human Walking Simulation

A hallway simulation with HuNavSim pedestrians, a saved occupancy map for RViz, and a walkability score map in Gazebo. The demo supports one PMB2 or four WalkabiliBots. Each robot exposes ROS 2 velocity command and odometry topics.

The pedestrian simulation and Gazebo integration are based on software from the Service Robotics Lab at Universidad Pablo de Olavide. [HuNavSim](https://github.com/robotics-upo/hunav_sim) · [HuNavSim Gazebo wrapper](https://github.com/robotics-upo/hunav_gazebo_wrapper)

## Quick start

Use Docker on a Linux desktop with X11 access. The tested setup uses ROS 2 Humble and Gazebo Classic 11 inside Docker. Build the image from the root of the cloned repository:

```bash
docker build -t human-walking-simulation:local .
xhost +SI:localuser:root
```

Launch either demo from the same desktop terminal:

```bash
# One PMB2
HUNAVSIM_IMAGE=human-walking-simulation:local ./run-docker.sh single

# Press Ctrl+C to stop single, then launch four WalkabiliBots.
HUNAVSIM_IMAGE=human-walking-simulation:local ./run-docker.sh multi
```

Both modes open Gazebo and RViz, load the hallway map, and start the pedestrians automatically. The multi-robot demo spawns the robots in sequence. The robots wait for velocity commands after their controllers activate. The first run of each mode compiles the ROS workspace and caches the build in a Docker volume.

When finished, remove the X11 permission granted above with `xhost -SI:localuser:root`.

## Inspect the simulation

While a demo is running, open a second terminal and enter its container. The default names are `human-walk-single` and `human-walk-multi`.

```bash
docker exec -it human-walk-multi bash
source /hallway-build/install/setup.bash
ros2 topic list -t
```

The launcher removes its default container when it exits. Set `HUNAVSIM_CONTAINER_NAME` to use a different name and keep the container after exit for log inspection. Single uses ROS domain 71 and Gazebo master port 11351. Multi uses domain 72 and port 11352. External ROS tools must use the corresponding domain.

For the single-robot demo, pass `rviz:=false` to skip the standalone RViz window or `navigation:=true` to start Nav2 with its RViz configuration. The Gazebo view hides the PMB2 laser beam while the scan topic remains available.

## Docker dependencies

The Dockerfile builds the PMB2 underlay and LightSFM from the commits in `docker/*.repos`. Apt packages are resolved from the configured package repositories at build time. `docker/packages-installed.tsv` records the package versions from the original working image as a reference. You can supply a base image digest through the `ROS_BASE_IMAGE` build argument.

The launcher also supports the original `hunavsim_gpu` image if it is already available locally. Set `HUNAVSIM_IMAGE` to select a different compatible image. Gazebo and RViz use Mesa software rendering by default.

## Scene and walkability

The shared scene uses `hallway.world`, `agents_hallway.yaml`, and the hallway occupancy map. `walkability/hallway_scores.yaml` contains the numerical score grid. It spans 20 m × 8 m at 1 m per cell, nominally centered on the world origin. Matrix indices are `scores[y][x]`, with columns increasing with world x and rows increasing with world y, starting at the lower corner `(-10, -4)`. The PNG uses the original hallway layout and starts at maximum world Y. The YAML grid starts at minimum world Y.

The score is 1.0 on normal ground, 0.7, 0.4, or 0.1 in the designated lower-score regions, and 0.0 at obstacles. Gazebo uses the original hallway texture, with light-blue cells marking obstacles. Scores are labels for evaluation and visualization. The demo floor uses a single Gazebo friction setting.

To render the original hallway score grid from the included YAML, install NumPy, Pillow, and PyYAML, then run:

```bash
python3 walkability/walk_map_new.py
```

The script writes `walkability/generated/walkability_map.png`. Its pixels match the texture in `src/hunav_gazebo_wrapper/models/walkability_map/materials/textures/`.

## Source and licenses

This repository adapts the upstream simulator for a hallway demonstration with a walkability score map, PMB2 and WalkabiliBot launch configurations, and a Docker build.

- The bundled HuNavSim packages and Gazebo wrapper retain their original Service Robotics Lab copyright and MIT license notices. [HuNavSim license](src/hunav_sim/LICENSE) · [Gazebo wrapper license](src/hunav_gazebo_wrapper/LICENSE)
- The WalkabiliBot description is under Apache-2.0. [Robot description license](src/walkabilibot_description/LICENSE)

PMB2 packages are supplied by the image.

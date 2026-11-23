#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    single)
        container_name=human-walk-single
        launch_file=gazebo_wrapper_hallway.launch.py
        domain_id=71
        gazebo_port=11351
        ;;
    multi)
        container_name=human-walk-multi
        launch_file=gazebo_traj_walkabilibot_multi.launch.py
        domain_id=72
        gazebo_port=11352
        ;;
    *) echo "Usage: $0 {single|multi} [ROS launch arguments]" >&2; exit 2 ;;
esac
shift

if [[ -z "${DISPLAY:-}" ]]; then
    echo "Run this from an X11 desktop terminal with DISPLAY set." >&2
    exit 1
fi

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
image=${HUNAVSIM_IMAGE:-hunavsim_gpu}
image_id=$(docker image inspect "$image" --format '{{.Id}}')
image_key=${image_id#sha256:}

container_args=(--rm --name "$container_name")
if [[ -n "${HUNAVSIM_CONTAINER_NAME:-}" ]]; then
    container_args=(--name "$HUNAVSIM_CONTAINER_NAME")
fi

docker run "${container_args[@]}" -it --init \
    --network host \
    --env DISPLAY \
    --env QT_X11_NO_MITSHM=1 \
    --env "LIBGL_ALWAYS_SOFTWARE=${LIBGL_ALWAYS_SOFTWARE:-1}" \
    --env "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-$domain_id}" \
    --env "GAZEBO_MASTER_URI=${GAZEBO_MASTER_URI:-http://127.0.0.1:$gazebo_port}" \
    --mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly \
    --mount "type=bind,source=$repo_dir,target=/hallway-src,readonly" \
    --mount "type=volume,source=hunavsim-hallway-$USER-$launch_file-${image_key:0:12},target=/hallway-build" \
    --workdir /hallway-build \
    --entrypoint /bin/bash \
    "$image" -ec '
        source /opt/ros/humble/setup.bash
        source /usr/share/gazebo/setup.sh
        if [[ -f /home/pmb2_ws/install/setup.bash ]]; then
            source /home/pmb2_ws/install/setup.bash
        fi
        if [[ "$1" == gazebo_wrapper_hallway.launch.py ]]; then
            if ! ros2 pkg prefix pmb2_gazebo >/dev/null; then
                echo "The single-robot demo requires an image with the PMB2 packages installed." >&2
                exit 1
            fi
            python3 /hallway-src/scripts/hide_pmb2_scan.py \
                "$(ros2 pkg prefix --share pmb2_description)" \
                "$(ros2 pkg prefix --share pal_urdf_utils)"
        fi
        colcon build --base-paths /hallway-src/src --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF
        source install/setup.bash
        exec ros2 launch hunav_gazebo_wrapper "$@"
    ' hallway "$launch_file" "$@"

# syntax=docker/dockerfile:1
ARG ROS_BASE_IMAGE=osrf/ros:humble-desktop-full
FROM ${ROS_BASE_IMAGE}

SHELL ["/bin/bash", "-ec"]

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential git python3-colcon-common-extensions python3-rosdep python3-vcstool \
    python3-numpy python3-pil python3-yaml libgl1-mesa-dri \
    'ros-humble-nav2-*' ros-dev-tools \
    ros-humble-urdf ros-humble-xacro ros-humble-behaviortree-cpp-v3 \
    ros-humble-gazebo-ros-pkgs ros-humble-gazebo-plugins \
    ros-humble-teleop-twist-joy ros-humble-teleop-twist-keyboard ros-humble-laser-proc \
    ros-humble-controller-interface ros-humble-controller-manager ros-humble-ros2-controllers \
    ros-humble-joint-state-broadcaster ros-humble-joint-state-publisher \
    ros-humble-joint-trajectory-controller ros-humble-joint-state-publisher-gui \
    ros-humble-compressed-image-transport ros-humble-slam-toolbox ros-humble-navigation2 \
    ros-humble-interactive-markers ros-humble-vision-msgs ros-humble-tf-transformations \
    ros-humble-launch-param-builder ros-humble-joy-linux ros-humble-joy-teleop \
    ros-humble-pal-maps ros-humble-rmw-cyclonedds-cpp ros-humble-twist-mux \
    ros-humble-pal-gazebo-plugins ros-humble-pal-urdf-utils \
    && rm -rf /var/lib/apt/lists/*

COPY docker/lightsfm.repos docker/pmb2.repos /tmp/hallway-deps/

WORKDIR /home
RUN vcs import /home < /tmp/hallway-deps/lightsfm.repos \
    && make -C /home/lightsfm \
    && make -C /home/lightsfm install \
    && ldconfig

WORKDIR /home/pmb2_ws
RUN mkdir src \
    && vcs import src < /tmp/hallway-deps/pmb2.repos \
    && source /opt/ros/humble/setup.bash \
    && colcon build --symlink-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    map_server = LifecycleNode(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        namespace='/',
        output='screen',
        parameters=[{
            'yaml_filename': LaunchConfiguration('map_yaml'),
            'topic_name': 'map',
            'frame_id': 'map',
            'use_sim_time': True,
        }],
    )
    configure = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(map_server),
        transition_id=Transition.TRANSITION_CONFIGURE,
    ))
    activate = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(map_server),
        transition_id=Transition.TRANSITION_ACTIVATE,
    ))

    return LaunchDescription([
        DeclareLaunchArgument('map_yaml', description='Path to the saved occupancy map YAML'),
        RegisterEventHandler(OnStateTransition(
            target_lifecycle_node=map_server,
            start_state='configuring',
            goal_state='inactive',
            entities=[activate],
        )),
        RegisterEventHandler(OnProcessStart(
            target_action=map_server,
            on_start=[configure],
        )),
        map_server,
    ])

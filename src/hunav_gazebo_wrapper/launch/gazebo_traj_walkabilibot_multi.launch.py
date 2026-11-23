from os import path
from os import environ
from os import pathsep
from scripts import GazeboRosPaths
from ament_index_python.packages import get_package_prefix, get_package_share_directory

from launch import LaunchDescription
from launch.actions import (IncludeLaunchDescription, SetEnvironmentVariable, 
                            DeclareLaunchArgument, ExecuteProcess, Shutdown, 
                            RegisterEventHandler, TimerAction, LogInfo, SetLaunchConfiguration)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (PathJoinSubstitution, LaunchConfiguration, 
                            PythonExpression, EnvironmentVariable, Command)
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import (OnExecutionComplete, OnProcessExit,
                                OnProcessIO, OnProcessStart, OnShutdown)
import launch_ros.parameter_descriptions
import os

def generate_launch_description():

    set_log_level = SetLaunchConfiguration('log_level', 'debug')
    


    # World generation parameters
    world_file_name = LaunchConfiguration('base_world')
    gz_obs = LaunchConfiguration('use_gazebo_obs')
    rate = LaunchConfiguration('update_rate')
    global_frame = LaunchConfiguration('global_frame_to_publish')
    use_navgoal = LaunchConfiguration('use_navgoal_to_start')
    navgoal_topic = LaunchConfiguration('navgoal_topic')
    ignore_models = LaunchConfiguration('ignore_models')

    # Multi-robot parameters
    # hallway
    robot_positions = [
        {'x': 8.0, 'y': 2.0, 'z': 0.25, 'yaw': 0.0},  # Robot 1
        {'x': 8.0, 'y': -2.0, 'z': 0.25, 'yaw': 0.0},  # Robot 2
        {'x': -8.0, 'y': 2.0, 'z': 0.25, 'yaw': 0.0},  # Robot 3
        {'x': -8.0, 'y': -2.0, 'z': 0.25, 'yaw': 0.0},  # Robot 4
    ]

    num_robots = len(robot_positions)

    # Agent configuration file
    agent_conf_file = PathJoinSubstitution([
        FindPackageShare('hunav_agent_manager'),
        'config',
        LaunchConfiguration('configuration_file')
    ])

    # Load hunav agent parameters
    hunav_loader_node = Node(
        package='hunav_agent_manager',
        executable='hunav_loader',
        output='screen',
        parameters=[agent_conf_file]
    )

    # World base file
    world_file = PathJoinSubstitution([
        FindPackageShare('hunav_gazebo_wrapper'),
        'worlds',
        world_file_name
    ])

    # HuNav world generator node
    hunav_gazebo_worldgen_node = Node(
        package='hunav_gazebo_wrapper',
        executable='hunav_gazebo_world_generator',
        output='screen',
        parameters=[{
            'base_world': world_file,
            'use_gazebo_obs': gz_obs,
            'update_rate': rate,
            'robot_name': 'robot1',  # Primary robot for HuNav tracking
            'global_frame_to_publish': global_frame,
            'use_navgoal_to_start': use_navgoal,
            'navgoal_topic': navgoal_topic,
            'ignore_models': ignore_models
        }]
    )

    # Launch world generator after loader starts
    ordered_launch_event = RegisterEventHandler(
        OnProcessStart(
            target_action=hunav_loader_node,
            on_start=[
                LogInfo(msg='HunNavLoader started, launching HuNav_Gazebo_world_generator after 3 seconds...'),
                TimerAction(
                    period=3.0,
                    actions=[hunav_gazebo_worldgen_node],
                )
            ]
        )
    )
    

    # Gazebo models path
    my_gazebo_models = PathJoinSubstitution([
        FindPackageShare('hunav_gazebo_wrapper'),
        'models',
    ])

    config_file_name = 'params.yaml' 
    pkg_dir = get_package_share_directory('hunav_gazebo_wrapper') 
    config_file = path.join(pkg_dir, 'launch', config_file_name) 

    
    model, plugin, media = GazeboRosPaths.get_paths()
    set_env_gazebo_model = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[my_gazebo_models, pathsep, model, pathsep, environ.get('GAZEBO_MODEL_PATH', '')],
    )
    set_env_gazebo_resource = SetEnvironmentVariable(
        name='GAZEBO_RESOURCE_PATH',
        value=[my_gazebo_models, pathsep, media, pathsep, environ.get('GAZEBO_RESOURCE_PATH', '')],
    )
    set_env_gazebo_plugin = SetEnvironmentVariable(
        name='GAZEBO_PLUGIN_PATH',
        value=[path.join(get_package_prefix('hunav_gazebo_wrapper'), 'lib'),
               pathsep, plugin, pathsep, environ.get('GAZEBO_PLUGIN_PATH', '')],
    )

    world_path = PathJoinSubstitution([
        FindPackageShare('hunav_gazebo_wrapper'),
        'worlds',
        'generatedWorld.world'
    ])

    # Gazebo server command
    gzserver_cmd = [
        'gzserver ',
        world_path, 
        _boolean_command('verbose'), '',
        '-s ', 'libgazebo_ros_init.so',
        '-s ', 'libgazebo_ros_factory.so',
        '--ros-args',
        '--params-file', config_file,
    ]

    # Gazebo client command
    gzclient_cmd = [
        'gzclient',
        _boolean_command('verbose'), ' ',
    ]

    gzserver_process = ExecuteProcess(
        cmd=gzserver_cmd,
        output='screen',
        shell=True,
        on_exit=Shutdown(),
    )

    gzclient_process = ExecuteProcess(
        cmd=gzclient_cmd,
        output='screen',
        shell=True,
        on_exit=Shutdown(),
    )


    # HuNav agent manager node
    hunav_manager_node = Node(
        package='hunav_agent_manager',
        executable='hunav_agent_manager',
        name='hunav_agent_manager',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    metrics_file = PathJoinSubstitution([
        FindPackageShare('hunav_evaluator'),
        'config',
        LaunchConfiguration('metrics_file')
    ])

    # HuNav evaluator node
    hunav_evaluator_node = Node(
        package='hunav_evaluator',
        executable='hunav_evaluator_node',
        output='screen',
        parameters=[metrics_file]
    )

    # Static TF publishers: map -> robot*/odom for each robot
    # This creates a unified TF tree with map as the root
    static_tf_nodes = []
    for i in range(num_robots):
        robot_namespace = f'robot{i+1}'
        pos = robot_positions[i]
        
        static_tf_node = Node(
            package = "tf2_ros", 
            executable = "static_transform_publisher",
            name = f'static_tf_map_to_{robot_namespace}_odom',
            output='screen',
            arguments = [
                str(pos['x']), str(pos['y']), '0.0',  # x, y, z translation
                '0', '0', '0',  # roll, pitch, yaw rotation
                'map',  # parent frame
                f'{robot_namespace}/odom'  # child frame
            ]
        )
        static_tf_nodes.append(static_tf_node)

    # Map server to publish the map for RViz visualization
    map_yaml_file = PathJoinSubstitution([
        FindPackageShare('hunav_rviz2_panel'),
        'maps',
        LaunchConfiguration('map_file')
    ])
    
    hallway_map = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path.join(pkg_dir, 'launch', 'hallway_map.launch.py')),
        launch_arguments={'map_yaml': map_yaml_file}.items(),
    )

    # RViz configuration for Multi-WalkabiliBot + HuNav
    rviz_config_file = PathJoinSubstitution([
        FindPackageShare('hunav_gazebo_wrapper'),
        'rviz',
        'walkabilibot_hunav.rviz'
    ])

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': True}]
    )


    # ----------------------------------------------------------
    # ----------------------------------------------------------
    #       MULTI-ROBOT WALKABILIBOT SETUP
    # ----------------------------------------------------------
    # ----------------------------------------------------------
    
    def create_robot_launch_nodes(robot_id, x_pos, y_pos, z_pos, yaw):
        """
        Create all necessary nodes and actions for a single WalkabiliBot robot
        
        Args:
            robot_id: Integer ID of the robot (1, 2, 3, ...)
            x_pos, y_pos, z_pos: Initial position coordinates
            yaw: Initial yaw angle
            
        Returns:
            Dictionary containing spawn event and controller events
        """
        robot_namespace = f'robot{robot_id}'
        robot_entity_name = f'robot{robot_id}'
        
        # Get WalkabiliBot description package path
        urdf_package_path = get_package_share_directory('walkabilibot_description')
        default_xacro_path = os.path.join(urdf_package_path, 'urdf', 'walkabilibot/walkabilibot.urdf.xacro')
        
        # Robot description using xacro
        # Note: We don't pass namespace to xacro as the original walkabilibot may not support it
        # The namespace will be handled by ROS 2 nodes instead
        substituted_command_result = Command(['xacro ', default_xacro_path])
        robot_description_value = launch_ros.parameter_descriptions.ParameterValue(
            substituted_command_result, value_type=str
        )

        # Robot state publisher (namespaced)
        # Important: This must be launched BEFORE spawning the robot in Gazebo
        # so that gazebo_ros2_control can find the robot_description service
        robot_state_publisher = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=robot_namespace,
            output='screen',
            parameters=[{
                'robot_description': robot_description_value,
                'use_sim_time': True,
                'frame_prefix': f'{robot_namespace}/'
            }]
        )

        # Spawn WalkabiliBot in Gazebo with unique entity name
        # The robot_description topic is published by robot_state_publisher
        # IMPORTANT: Use -robot_namespace to tell gazebo_ros2_control where to find services
        robot_spawn_entity = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            output='screen',
            arguments=[
                '-topic', f'/{robot_namespace}/robot_description',
                '-entity', robot_entity_name,
                '-robot_namespace', robot_namespace,
                '-x', str(x_pos),
                '-y', str(y_pos),
                '-z', str(z_pos),
                '-Y', str(yaw),
                '-unpause'  # Unpause physics after spawning
            ]
        )

        # Load joint state broadcaster controller
        robot_load_joint_state_controller = ExecuteProcess(
            cmd=[
                'ros2', 'control', 'load_controller',
                '--controller-manager', f'/{robot_namespace}/controller_manager',
                'walkabilibot_joint_state_broadcaster',
                '--set-state', 'active'
            ],
            output='screen'
        )

        # Load differential drive controller
        robot_load_diff_driver_controller = ExecuteProcess(
            cmd=[
                'ros2', 'control', 'load_controller',
                '--controller-manager', f'/{robot_namespace}/controller_manager',
                'walkabilibot_diff_drive_controller',
                '--set-state', 'active'
            ],
            output='screen'
        )

        # Calculate spawn delay (stagger robot spawning to avoid conflicts)
        # Robot 1: 8s, Robot 2: 11s, Robot 3: 14s
        # Increased initial delay to ensure Gazebo is fully ready
        spawn_delay = 8.0 + (robot_id - 1) * 3.0
        
        # Delay between launching robot_state_publisher and spawning entity
        # This ensures robot_description topic is available before spawning
        entity_spawn_delay = 2.0

        # Event: Launch robot_state_publisher first
        robot_state_pub_event = RegisterEventHandler(
            OnProcessStart(
                target_action=gzserver_process,
                on_start=[
                    LogInfo(msg=f'Gazebo started, launching {robot_entity_name} robot_state_publisher after {spawn_delay} seconds...'),
                    TimerAction(
                        period=spawn_delay,
                        actions=[robot_state_publisher],
                    )
                ]
            )
        )
        
        # Event: Spawn robot entity after robot_state_publisher is running
        robot_spawn_event = RegisterEventHandler(
            OnProcessStart(
                target_action=robot_state_publisher,
                on_start=[
                    LogInfo(msg=f'{robot_entity_name} robot_state_publisher started, spawning entity after {entity_spawn_delay} seconds...'),
                    TimerAction(
                        period=entity_spawn_delay,
                        actions=[robot_spawn_entity],
                    )
                ]
            )
        )

        # Events: Load controllers sequentially after robot spawns
        robot_controller_events = [
            RegisterEventHandler(
                OnProcessExit(
                    target_action=robot_spawn_entity,
                    on_exit=[
                        LogInfo(msg=f'{robot_entity_name} spawned, loading joint state controller...'),
                        robot_load_joint_state_controller
                    ],
                )
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=robot_load_joint_state_controller,
                    on_exit=[
                        LogInfo(msg=f'{robot_entity_name} joint state controller loaded, loading diff drive controller...'),
                        robot_load_diff_driver_controller
                    ],
                )
            )
        ]

        return {
            'state_pub_event': robot_state_pub_event,
            'spawn_event': robot_spawn_event,
            'controller_events': robot_controller_events
        }


    # ----------------------------------------------------------
    # Declare launch arguments
    # ----------------------------------------------------------
    declare_agents_conf_file = DeclareLaunchArgument(
        'configuration_file', default_value='agents_hallway.yaml',
        description='Specify configuration file name in the config directory'
    )
    declare_metrics_conf_file = DeclareLaunchArgument(
        'metrics_file', default_value='metrics.yaml',
        description='Specify the name of the metrics configuration file in the config directory'
    )
    declare_arg_world = DeclareLaunchArgument(
        'base_world', default_value='hallway.world',
        description='Specify world file name'
    )
    declare_arg_map = DeclareLaunchArgument(
        'map_file', default_value='hallway.yaml',
        description='Specify map yaml file name for visualization in RViz'
    )
    declare_gz_obs = DeclareLaunchArgument(
        'use_gazebo_obs', default_value='True',
        description='Whether to fill the agents obstacles with closest Gazebo obstacle or not'
    )
    declare_update_rate = DeclareLaunchArgument(
        'update_rate', default_value='100.0',
        description='Update rate of the plugin'
    )
    declare_frame_to_publish = DeclareLaunchArgument(
        'global_frame_to_publish', default_value='map',
        description='Name of the global frame in which the position of the agents are provided'
    )
    declare_use_navgoal = DeclareLaunchArgument(
        'use_navgoal_to_start', default_value='False',
        description='Whether to start the agents movements when a navigation goal is received or not'
    )
    declare_navgoal_topic = DeclareLaunchArgument(
        'navgoal_topic', default_value='human_trigger_goal',
        description='Name of the topic in which navigation goal for the robot will be published'
    )
    declare_ignore_models = DeclareLaunchArgument(
        'ignore_models', default_value='ground_plane walkability_floor',
        description='list of Gazebo models that the agents should ignore as obstacles'
    )
    declare_arg_verbose = DeclareLaunchArgument(
        'verbose', default_value='False',
        description='Set "true" to increase messages written to terminal.'
    )


    # ----------------------------------------------------------
    # Event handlers for launching in sequence
    # ----------------------------------------------------------
    
    # Launch Gazebo after world generation
    gz_launch_event = RegisterEventHandler(
        OnProcessStart(
            target_action=hunav_gazebo_worldgen_node,
            on_start=[
                LogInfo(msg='GenerateWorld started, launching Gazebo after 3 seconds...'),
                TimerAction(
                    period=3.0,
                    actions=[gzserver_process, gzclient_process],
                )
            ]
        )
    )

    # ----------------------------------------------------------
    # Build Launch Description
    # ----------------------------------------------------------
    
    ld = LaunchDescription()

    # Set environment variables
    ld.add_action(set_env_gazebo_model)
    ld.add_action(set_env_gazebo_resource)
    ld.add_action(set_env_gazebo_plugin)

    # Declare all launch arguments
    ld.add_action(declare_agents_conf_file)
    ld.add_action(declare_metrics_conf_file)
    ld.add_action(declare_arg_world)
    ld.add_action(declare_arg_map)
    ld.add_action(declare_gz_obs)
    ld.add_action(declare_update_rate)
    ld.add_action(declare_frame_to_publish)
    ld.add_action(declare_use_navgoal)
    ld.add_action(declare_navgoal_topic)
    ld.add_action(declare_ignore_models)
    ld.add_action(declare_arg_verbose)

    # Launch sequence:
    # 1. Load agent configuration
    ld.add_action(hunav_loader_node)
    ld.add_action(ordered_launch_event)

    # 2. HuNav behavior manager and evaluator
    ld.add_action(hunav_manager_node)
    ld.add_action(hunav_evaluator_node)

    # 3. Launch Gazebo after world generation
    ld.add_action(gz_launch_event)
    
    # 4. Static TF publishers for each robot (map->robot*/odom)
    for static_tf_node in static_tf_nodes:
        ld.add_action(static_tf_node)

    # 5. Publish the saved hallway map
    ld.add_action(hallway_map)

    # 6. RViz for visualization
    ld.add_action(rviz_node)

    # 7. Create and spawn multiple WalkabiliBot robots
    for i in range(num_robots):
        robot_nodes = create_robot_launch_nodes(
            robot_id=i+1,
            x_pos=robot_positions[i]['x'],
            y_pos=robot_positions[i]['y'],
            z_pos=robot_positions[i]['z'],
            yaw=robot_positions[i]['yaw']
        )
        
        # Add state publisher event (launches robot_state_publisher)
        ld.add_action(robot_nodes['state_pub_event'])
        
        # Add spawn event (spawns robot in Gazebo after state publisher is ready)
        ld.add_action(robot_nodes['spawn_event'])
        
        # Add controller events (loads controllers after robot is spawned)
        for event in robot_nodes['controller_events']:
            ld.add_action(event)

    return ld


# Helper function for boolean command arguments
def _boolean_command(arg):
    cmd = ['"--', arg, '" if "true" == "', LaunchConfiguration(arg), '" else ""']
    py_cmd = PythonExpression(cmd)
    return py_cmd

import numpy as np
import pybullet as p

# Ids of the control points in the urdf robot
sphere_1_id = 8  # in between frame 3 and the wrist
sphere_2_id = 7  # wrist (frame 4)
sphere_3_id = 6  # tip of the gripper
sphere_ids = np.array([sphere_1_id, sphere_2_id, sphere_3_id])


def get_target_points(target_pose, d6):
    """gives the target 3d location for the control points on the robot
    point_3 is the tip of the gripper
    point_2 is the origin of frame 6
    point_1 is only used to calculate repulsive forces

    Args:
      target_pose: A Pose specifying the target pose for the robot
      d6: the length of the gripper

    Returns:
      a 3 vector [x,y,z] for each control point on the robot
    """
    x_3, y_3, z_3 = target_pose.x, target_pose.y, target_pose.z
    point_3 = np.array([x_3, y_3, z_3])

    t = target_pose.get_euler_matrix()
    x_2 = x_3 - d6 * t[0, 2]
    y_2 = y_3 - d6 * t[1, 2]
    z_2 = z_3 - d6 * t[2, 2]
    point_2 = np.array([x_2, y_2, z_2])

    point_1 = None  # we only need two points for the attractive force

    return point_1, point_2, point_3


def get_attractive_force_world(control_points, target_points, attractive_cutoff_distance, weights=None):
    """Calculates the vectors pointing from the control points on the robot to the target points
    The vectors will have a norm of max attractive_cutoff_distance

    Args:
        control_points: An array of the current 3d positions of every control point on the robot
        target_points: An array of the 3d positions of the target points
        attractive_cutoff_distance: Distance after which the vector will start to decrease
        weights: a 3 vector of relative importance of the control points.
    Returns:
        workspace_forces: a 3x3 matrix for every control point a vector
                          pointing to the target position of the control point
        total_distance: the sum of distances between the control points and their targets,
                        can be used to determine if the robot has reached the target position
    """
    number_of_control_points = control_points.size

    if number_of_control_points != target_points.size:
        raise Exception("control points and target points should have the same dimension!")
    number_of_control_points = control_points.shape[0]

    if weights is None:
        weights = np.ones(number_of_control_points)
    workspace_forces = np.zeros((number_of_control_points, 3))

    total_distance = 0

    for control_point_id in range(number_of_control_points):
        vector = control_points[control_point_id] - target_points[control_point_id]
        distance = np.linalg.norm(vector)
        if distance == 0:
            pass
        elif distance > attractive_cutoff_distance:
            workspace_forces[control_point_id][0] = -attractive_cutoff_distance * weights[control_point_id] * vector[0] / distance
            workspace_forces[control_point_id][1] = -attractive_cutoff_distance * weights[control_point_id] * vector[1] / distance
            workspace_forces[control_point_id][2] = -attractive_cutoff_distance * weights[control_point_id] * vector[2] / distance
        elif distance <= attractive_cutoff_distance:
            workspace_forces[control_point_id][0] = -weights[control_point_id] * vector[0]
            workspace_forces[control_point_id][1] = -weights[control_point_id] * vector[1]
            workspace_forces[control_point_id][2] = -weights[control_point_id] * vector[2]
        total_distance += distance

    return workspace_forces, total_distance


def get_control_point_pos(robot_body_id, point_id):
    """Get the 3d position of a control point on the robot

    Args:
        robot_body_id: the id of the simulated robot arm
        point_id: the id of the control point on the robot arm
    Returns: A 3d array of the coordinates of the control point
    """
    _, _, _, _, pos, _ = p.getLinkState(robot_body_id, point_id)
    return np.array(pos) * 100  # convert from meters to centimeters
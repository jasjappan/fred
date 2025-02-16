import numpy as np
from src.kinematics.kinematics_utils import Pose
from src.reinforcementlearning.environment.occupancy_grid_util import create_hilbert_curve_from_obstacles
from src.reinforcementlearning.environment.occupancy_grid_util import create_occupancy_grid_from_obstacles
from src.reinforcementlearning.environment.robot_env import RobotEnv
from src.reinforcementlearning.environment.scenario import Scenario, \
    sensible_scenarios
from src.utils.obstacle import BoxObstacle
from tf_agents.specs import array_spec
from tf_agents.trajectories import time_step as ts


class RobotEnvWithObstacles(RobotEnv):

    def __init__(self, use_gui=False, raw_obs=False, scenarios=None, is_eval=False, robot_controller=None,
                 angle_control=False, draw_debug_lines=False, pose_recorder=None):
        if scenarios is None:
            raise ValueError("RobotEnvWithObstacles should be initialized with scenarios, "
                             "otherwise we would default to no obstacle scenarios!")
        super().__init__(use_gui, raw_obs, is_eval=is_eval, scenarios=scenarios, robot_controller=robot_controller,
                         angle_control=angle_control, draw_debug_lines=draw_debug_lines, pose_recorder=pose_recorder)
        self._hilbert_curve_iteration = 3
        self._grid_len_x = 40
        self._grid_len_y = 40
        self._grid_size = 4
        self._observation_spec = {
            'observation': array_spec.BoundedArraySpec(shape=(17,), dtype=np.float32, minimum=-2, maximum=2),
            'grid': array_spec.BoundedArraySpec((10, 10, 1), np.float32, minimum=0, maximum=1)
        }
        self._grid = create_occupancy_grid_from_obstacles(self._obstacles, grid_len_x=self._grid_len_x,
                                                          grid_len_y=self._grid_len_y, grid_size=self._grid_size)

    def _reset(self):
        super(RobotEnvWithObstacles, self)._reset()
        self._grid = create_occupancy_grid_from_obstacles(self._obstacles, grid_len_x=self._grid_len_x,
                                                          grid_len_y=self._grid_len_y, grid_size=self._grid_size)
        observation, _ = self._get_observations()
        return ts.restart(observation)

    def _get_observations(self):
        no_obstacle_obs, total_distance = super()._get_observations()

        grid = self._grid

        total_observation = {
            'observation': np.array(no_obstacle_obs, dtype=np.float32),
            'grid': np.expand_dims(grid, axis=2)
        }

        return total_observation, total_distance

    def show_occupancy_grid_and_curve(self):
        grid = create_occupancy_grid_from_obstacles(self._obstacles, grid_len_x=self._grid_len_x,
                                                          grid_len_y=self._grid_len_y, grid_size=self._grid_size)
        curve = create_hilbert_curve_from_obstacles(self._obstacles, grid_len_x=self._grid_len_x,
                                                          grid_len_y=self._grid_len_y,
                                                          iteration=self._hilbert_curve_iteration)

        import matplotlib.pyplot as plt

        plt.set_cmap('hot')

        fig = plt.figure()
        ax1 = fig.add_subplot(2, 2, 1)

        reshape = 2 ** self._hilbert_curve_iteration
        ax1.imshow(curve.reshape(reshape, reshape))
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.imshow(grid)

        plt.show()


if __name__ == '__main__':
    x = Scenario([BoxObstacle([10, 40, 15], [-10, 35, 0]), BoxObstacle([10, 40, 25], [10, 35, 0])],
             Pose(-25, 20, 10), Pose(30, 30, 10)),
    scenario = Scenario([BoxObstacle([10, 10, 30], [-5, 20, 0], alpha=0),
                         BoxObstacle([10, 20, 20], [5, 35, 0], alpha=np.pi / 4)],
                        Pose(-25, 20, 10), Pose(30, 30, 10))
    env = RobotEnvWithObstacles(use_gui=True, scenarios=sensible_scenarios)
    state = env.observation_spec()
    print(state)
    obs = env.reset()
    print(obs)
    env.show_occupancy_grid_and_curve()
    # print("hoi")

# ░░░░░░░█▐▓▓░████▄▄▄█▀▄▓▓▓▌█ Epic code
# ░░░░░▄█▌▀▄▓▓▄▄▄▄▀▀▀▄▓▓▓▓▓▌█
# ░░░▄█▀▀▄▓█▓▓▓▓▓▓▓▓▓▓▓▓▀░▓▌█
# ░░█▀▄▓▓▓███▓▓▓███▓▓▓▄░░▄▓▐█▌ level is so high
# ░█▌▓▓▓▀▀▓▓▓▓███▓▓▓▓▓▓▓▄▀▓▓▐█
# ▐█▐██▐░▄▓▓▓▓▓▀▄░▀▓▓▓▓▓▓▓▓▓▌█▌
# █▌███▓▓▓▓▓▓▓▓▐░░▄▓▓███▓▓▓▄▀▐█ much quality
# █▐█▓▀░░▀▓▓▓▓▓▓▓▓▓██████▓▓▓▓▐█
# ▌▓▄▌▀░▀░▐▀█▄▓▓██████████▓▓▓▌█▌
# ▌▓▓▓▄▄▀▀▓▓▓▀▓▓▓▓▓▓▓▓█▓█▓█▓▓▌█▌ Wow.
# █▐▓▓▓▓▓▓▄▄▄▓▓▓▓▓▓█▓█▓█▓█▓▓▓▐█

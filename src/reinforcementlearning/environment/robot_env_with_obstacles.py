from tf_agents.specs import array_spec

from src.kinematics.kinematics_utils import Pose
from src.reinforcementlearning.environment.robot_env import RobotEnv
from src.reinforcementlearning.environment.scenario import scenarios_no_obstacles, scenarios_obstacles, Scenario
import numpy as np

from src.reinforcementlearning.occupancy_grid_util import create_hilbert_curve_from_obstacles
from src.utils.obstacle import BoxObstacle


class RobotEnvWithObstacles(RobotEnv):

    def __init__(self, use_gui=False, raw_obs=False, no_obstacles=True):
        super().__init__(use_gui, raw_obs)

        self._observation_spec = (array_spec.BoundedArraySpec(
            shape=(20,),
            dtype=np.float32, minimum=-1, maximum=1, name='observation'),
          array_spec.BoundedArraySpec(
              shape=(2 ** (2 * self._hilbert_curve_iteration), ),
              dtype=np.float32, minimum=0, maximum=1, name='hilbert curve'),
        )
        self.scenarios = scenarios_no_obstacles + scenarios_obstacles
        self._max_steps_to_take_before_failure = 1000
        self._update_step_size = 0.005

    def _get_observations(self):
        no_obstacle_obs, total_distance = super()._get_observations()

        curve = create_hilbert_curve_from_obstacles(self._obstacles, grid_len_x=self._grid_len_x,
                                                    grid_len_y=self._grid_len_y,
                                                    iteration=self._hilbert_curve_iteration)

        total_observation = (np.array(no_obstacle_obs, dtype=np.float32),
                             np.array(np.array(curve.tolist()), dtype=np.float32))

        return total_observation, total_distance

    def show_occupancy_grid_and_curve(self):
        from src.reinforcementlearning.occupancy_grid_util import create_occupancy_grid_from_obstacles

        len_x = 40
        len_y = 40
        curve_iteration = 3

        grid = create_occupancy_grid_from_obstacles(self._obstacles, grid_len_x=len_x, grid_len_y=len_y, grid_size=4)
        curve = create_hilbert_curve_from_obstacles(self._obstacles, grid_len_x=len_x, grid_len_y=len_y,
                                                    iteration=curve_iteration)

        import matplotlib.pyplot as plt

        plt.set_cmap('hot')

        fig = plt.figure()
        ax1 = fig.add_subplot(2, 2, 1)

        reshape = 2 ** curve_iteration
        ax1.imshow(curve.reshape(reshape, reshape))
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.imshow(grid)

        plt.show()


if __name__ == '__main__':
    env = RobotEnvWithObstacles(use_gui=True)
    state = env.observation_spec()
    print(state)
    env._externally_set_scenario = Scenario([BoxObstacle([10, 10, 30], [-5, 35, 0], alpha=0),
                                             BoxObstacle([10, 20, 20], [5, 35, 0], alpha=np.pi / 4)],
                                            Pose(-25, 20, 10), Pose(30, 30, 10))
    obs = env.reset()
    env.show_occupancy_grid_and_curve()
    print("hoi")


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
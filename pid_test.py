from time import sleep, time
from src.global_objects import get_robot
from src.kinematics.kinematics_utils import Pose
from src.utils.movement_utils import line, b_spline_curve
from src.workspace_limits import WorkSpaceLimits
import matplotlib.pyplot as plt

servo_id = 4
target = 2048

robot = get_robot('COM5')
robot.enable_servos()
                                    #p  i  d
robot.set_pid_single_servo(servo_id, 2500, 0, 3500)

x = []
y = []
y_target = []

prev_pos = robot.get_servo_position(servo_id)
if prev_pos > 1500:
    target = 1024
else:
    target = 3072


robot.set_servo_position(servo_id, target)
elapsed_time = 0
for i in range(200):
    start = time()
    pos = robot.get_servo_position(servo_id)
    stop = time()

    elapsed_time += stop - start
    x.append(elapsed_time)

    y.append(pos)
    y_target.append(target)

# robot.disable_servos()

plt.plot(x, y, 'g')
plt.plot(x, y_target, 'r')
plt.show()



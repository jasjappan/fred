import json
from src.robot_controllers.dynamixel_robot.servo import Servo, ServoEncoder, ServoDecoder
from numpy import pi

servo1 = Servo(0, 6144, 0, pi, 100, 20, p=1500, i=0, d=1500)
servo2 = Servo(0, 6144, 0, pi, 50, 10, p=1500, i=100, d=1500)
servo3 = Servo(6144, 0, -pi/2, pi/2, 100, 20, p=1500, i=0, d=1500)
servo4 = Servo(0, 4095, -pi, pi, 400, 80, p=1000, i=0, d=200)
servo5 = Servo(0, 4095, -pi, pi, 150, 50, p=2500, i=0, d=500)
servo6 = Servo(0, 4095, -pi, pi, 150, 50, p=1500, i=0, d=500)
servo7 = Servo(0, 4095, -pi, pi, 150, 50, p=2500, i=0, d=500)

servos = {
    "servo1": servo1,
    "servo2": servo2,
    "servo3": servo3,
    "servo4": servo4,
    "servo5": servo5,
    "servo6": servo6,
    "servo7": servo7,
}

json_string = json.dumps(servos, cls=ServoEncoder,  indent=4)

# print(json_string)

with open("resources/servo_config.json", "w") as outfile:
    outfile.write(json_string)

decoded_servo = ServoDecoder().decode(json_string)

print(decoded_servo)

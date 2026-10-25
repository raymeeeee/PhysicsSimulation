import math
import sys
import pathlib
# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

# Use config_manager
from config_manager import get_config_manager
cfg = get_config_manager()


class FrictionManager:

    # -- Init --

    def __init__(self, plane, plane_angle, moving_object, friction_coefficient):
        self.plane = plane
        self.plane_angle = plane_angle   # degrees
        self.moving_object = moving_object
        self.friction_coefficient = friction_coefficient

        self.angle_rad = math.radians(self.plane_angle)

    # -- Utility --

    def _gravity_components(self):
        weight = self.moving_object.mass * cfg.GRAVITY
        return (
            weight * math.sin(self.angle_rad),  # pulls object down the slope
            weight * math.cos(self.angle_rad),  # presses object into slope
        )

    def get_velocity_component_along_plane(self, vel_x, vel_y):
        plane_dir_x = math.cos(self.angle_rad)
        plane_dir_y = math.sin(self.angle_rad)
        return vel_x * plane_dir_x + vel_y * plane_dir_y

    def calculate_forces(self):
        gravity_parallel, gravity_perp = self._gravity_components()
        normal_force = gravity_perp
        max_friction = self.friction_coefficient * normal_force

        vel_x = self.moving_object.get_velocity_x()
        vel_y = self.moving_object.get_velocity_y()
        velocity_along_plane = self.get_velocity_component_along_plane(vel_x, vel_y)

        velocity_threshold = 0.1  # m/s — below this considered stopped

        # determine friction force
        if abs(velocity_along_plane) > velocity_threshold:
            # object is moving — friction opposes motion
            friction_force = -math.copysign(max_friction, velocity_along_plane)
            
        elif abs(velocity_along_plane) <= velocity_threshold and gravity_parallel != 0.0:
            # object is stopped — friction opposes gravity
            if abs(gravity_parallel) <= max_friction:
                # friction can hold object in place
                self.moving_object.set_velocity_x(0.0)
                self.moving_object.set_velocity_y(0.0)
                friction_force = -gravity_parallel  # Cancel gravity exactly
            else:
                # gravity overcomes friction — object will slide
                friction_force = -math.copysign(max_friction, gravity_parallel)
                
        else:
            # flat plane, no velocity, no gravity component
            return 0.0, 0.0

        # calculate net force
        net_force_along_plane = gravity_parallel + friction_force

        # prevent oscillation when nearly stopped
        if abs(velocity_along_plane) < velocity_threshold:
            if gravity_parallel != 0.0 and (
                math.copysign(1.0, net_force_along_plane) !=
                math.copysign(1.0, gravity_parallel)
            ):
                net_force_along_plane = 0.0

        # convert to world coordinates
        force_x = net_force_along_plane * math.cos(self.angle_rad)
        force_y = net_force_along_plane * math.sin(self.angle_rad)
        return force_x, force_y

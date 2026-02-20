"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> tuple[bool, "Command | None"]:
        """
        Falliable create (instantiation) method to create a Command object.
        """
        if connection is None:
            local_logger.error("Connection Not Provided")
            return False, None

        return True, cls(cls.__private_key, connection, target, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        self.connection = connection
        self.target = target
        self.local_logger = local_logger
        self.runcount = 0
        self.total_velocity = Position(0.0, 0.0, 0.0)

    def run(self, telemetry_data: telemetry.TelemetryData) -> str:
        """
        Make a decision based on received telemetry data.
        """
        # Log average velocity for this trip so far
        self.runcount += 1
        self.total_velocity.x += telemetry_data.x_velocity
        self.total_velocity.y += telemetry_data.y_velocity
        self.total_velocity.z += telemetry_data.z_velocity
        average_velocity = Position(
            self.total_velocity.x / self.runcount,
            self.total_velocity.y / self.runcount,
            self.total_velocity.z / self.runcount,
        )
        self.local_logger.info(
            f"Average velocity so far: ({average_velocity.x}, {average_velocity.y}, {average_velocity.z})"
        )

        # Calculating vertical
        dz = self.target.z - telemetry_data.z
        if abs(dz) > 0.5:
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                1.0,
                0,
                0,
                0,
                0,
                0,
                self.target.z,
            )
            return f"CHANGE ALTITUDE: {dz}"

        # Calculating yaw adjustment
        target_yaw_rad = math.atan2(
            self.target.y - telemetry_data.y, self.target.x - telemetry_data.x
        )
        target_yaw_deg = math.degrees(target_yaw_rad)
        current_yaw_deg = math.degrees(telemetry_data.yaw)
        delta_yaw = target_yaw_deg - current_yaw_deg

        if delta_yaw > 180:
            delta_yaw -= 360
        elif delta_yaw < -180:
            delta_yaw += 360

        if abs(delta_yaw) > 5:
            direction = 1 if delta_yaw > 0 else -1
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                abs(delta_yaw),
                5.0,
                direction,
                1,  # Relative angle
                0,
                0,
                0,
            )
            return f"CHANGE YAW: {delta_yaw}"
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

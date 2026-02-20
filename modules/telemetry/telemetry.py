"""
Telemetry gathering logic.
"""

import time

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> tuple[bool, "Telemetry | None"]:
        """
        Factory method to create Telemetry object. Checks that connection is not None and initializes the logger.
        """
        if connection is None:
            local_logger.error("Telemetry: No connection provided")
            return False, None
        return True, cls(cls.__private_key, connection, local_logger)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"
        self.__connection = connection
        self._local_logger = local_logger

    def run(
        self,
    ) -> tuple[bool, TelemetryData | None]:
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        # Read MAVLink message LOCAL_POSITION_NED (32)
        # Read MAVLink message ATTITUDE (30)
        # Return the most recent of both, and use the most recent message's timestamp

        attitude_msg = None
        position_msg = None

        # Requirement: 1 second timeout to get both
        # We'll use a loop to keep checking the buffer
        start_time = time.time()

        while time.time() - start_time < 1.0:
            msg = self.__connection.recv_match(
                type=["ATTITUDE", "LOCAL_POSITION_NED"], blocking=True, timeout=0.1
            )

            if msg is None:
                continue
            if msg.get_type() == "ATTITUDE":
                attitude_msg = msg
            elif msg.get_type() == "LOCAL_POSITION_NED":
                position_msg = msg

            if attitude_msg and position_msg:
                # Calculate the latest timestamp
                timestamp = max(attitude_msg.time_boot_ms, position_msg.time_boot_ms)

                data = TelemetryData(
                    roll=attitude_msg.roll,
                    pitch=attitude_msg.pitch,
                    yaw=attitude_msg.yaw,
                    x=position_msg.y,  # East is X
                    y=position_msg.x,  # North is Y
                    z=-position_msg.z,  # -Down is Up
                    time_since_boot=timestamp,
                )
                return True, data

        return False, None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

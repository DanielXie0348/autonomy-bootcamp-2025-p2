"""
Heartbeat sending logic.
"""

from pymavlink import mavutil


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatSender:
    """
    HeartbeatSender class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls, connection: mavutil.mavfile
    ) -> "tuple[True, HeartbeatSender] | tuple[False, None]":
        """
        Create a HeartbeatSender instance if the connection is valid, otherwise return False and None.
        """
        if connection is not None:
            return (True, cls(cls.__private_key, connection))
        return (False, None)

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
    ) -> None:
        assert key is HeartbeatSender.__private_key, "Use create() method"
        # Do any intializiation here
        self.connection = connection

    def run(
        self,  # Put your own arguments here
    ) -> None:
        """
        Run the heartbeat sender logic. This method will be called in a loop, so it should not block for too long.
        """
        self.connection.mav.srcSystem = 255
        self.connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

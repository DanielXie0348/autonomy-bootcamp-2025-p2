"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import Logger  # pylint: disable=unused-import


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        threshold: int,
    ) -> tuple[bool, "HeartbeatReceiver | None"]:
        """
        Factory method to create a HeartbeatReceiver instance.
        """

        return True, cls(cls.__private_key, threshold, connection)

    def __init__(
        self,
        key: object,
        threshold: int,
        connection: mavutil.mavfile,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"
        self.__threshold = threshold
        self.__connection = connection
        self.missed_heartbeats = 0

    def run(self) -> bool:
        """
        Run the heartbeat receiver logic.
        """
        msg = self.__connection.recv_match(type="HEARTBEAT", blocking=True, timeout=1.0)
        if msg is None:
            self.missed_heartbeats += 1
            if self.missed_heartbeats >= self.__threshold:
                return False
            return True

        self.missed_heartbeats = 0
        return True


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

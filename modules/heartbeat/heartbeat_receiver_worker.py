"""
Heartbeat worker that sends heartbeats periodically.
"""

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import heartbeat_receiver
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_receiver_worker(
    connection: mavutil.mavfile,
    controller: worker_controller.WorkerController,
    queue_wrapper: queue_proxy_wrapper.QueueProxyWrapper,
    threshold: int,
) -> None:
    """
    Worker function that receives heartbeats from the drone and puts the connection status in a queue.
    """

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (heartbeat_receiver.HeartbeatReceiver)
    result, receiver = heartbeat_receiver.HeartbeatReceiver.create(
        connection,
        threshold,
    )

    if not result:
        local_logger.error("Failed to create HeartbeatReceiver object")
        return

    local_logger.info("HeartbeatReceiver object created successfully")
    # Main loop: do work.

    num_missed_consec = 0
    while controller.is_exit_requested() is False:
        is_connected = receiver.run()
        queue_wrapper.queue.put(is_connected)

        if is_connected:
            local_logger.info("Heartbeat received")
            num_missed_consec = 0
        else:
            num_missed_consec += 1
            local_logger.error(
                f"Connection Lost! Consecutive missed heartbeats: {num_missed_consec}"
            )


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================

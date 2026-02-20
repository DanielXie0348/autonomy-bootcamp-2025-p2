"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
HEARTBEAT_QUEUE_MAXSIZE = 10
TELEMETRY_QUEUE_MAXSIZE = 10
COMMAND_QUEUE_MAXSIZE = 10

# Set worker counts
HEARTBEAT_SENDER_COUNT = 1
HEARTBEAT_RECEIVER_COUNT = 1
TELEMETRY_COUNT = 1
COMMAND_COUNT = 1

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues
    manager = mp.Manager()

    # Create queues
    heartbeat_to_main_queue = queue_proxy_wrapper.QueueProxyWrapper(
        manager, HEARTBEAT_QUEUE_MAXSIZE
    )
    telemetry_to_command_queue = queue_proxy_wrapper.QueueProxyWrapper(
        manager, TELEMETRY_QUEUE_MAXSIZE
    )
    command_to_main_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, COMMAND_QUEUE_MAXSIZE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender
    result, heartbeat_sender_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_SENDER_COUNT,  # How many workers
        target=heartbeat_sender_worker.heartbeat_sender_worker,  # What's the function that this worker runs
        work_arguments=(  # The function's arguments excluding input/output queues and controller
            connection,
        ),
        input_queues=[],  # Note that input/output queues must be in the proper order
        output_queues=[],
        controller=controller,  # Worker controller
        local_logger=main_logger,  # Main logger to log any failures during worker creation
    )
    if not result:
        print("Failed to create arguments for heartbeat sender worker")
        return -1
    # Heartbeat receiver
    assert heartbeat_sender_properties is not None

    result, heartbeat_receiver_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_RECEIVER_COUNT,
        target=heartbeat_receiver_worker.heartbeat_receiver_worker,
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[heartbeat_to_main_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create arguments for heartbeat receiver worker")
        return -1

    # Telemetry
    assert heartbeat_receiver_properties is not None

    result, telemetry_properties = worker_manager.WorkerProperties.create(
        count=TELEMETRY_COUNT,
        target=telemetry_worker.telemetry_worker,
        work_arguments=(connection,),
        input_queues=[],
        output_queues=[telemetry_to_command_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        print("Failed to create arguments for telemetry worker")
        return -1

    # Command
    assert telemetry_properties is not None
    result, command_properties = worker_manager.WorkerProperties.create(
        count=COMMAND_COUNT,
        target=command_worker.command_worker,
        work_arguments=(
            connection,
            command.Position(0, 0, 0),  # Just a dummy position command to test with
        ),
        input_queues=[telemetry_to_command_queue],
        output_queues=[command_to_main_queue],
        controller=controller,
        local_logger=main_logger,
    )

    assert command_properties is not None

    # Create the workers (processes) and obtain their managers
    result, heartbeat_sender_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_sender_properties,
        local_logger=main_logger,
    )
    result, heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_receiver_properties,
        local_logger=main_logger,
    )
    result, telemetry_manager = worker_manager.WorkerManager.create(
        worker_properties=telemetry_properties,
        local_logger=main_logger,
    )
    result, command_manager = worker_manager.WorkerManager.create(
        worker_properties=command_properties,
        local_logger=main_logger,
    )
    workers = [
        heartbeat_sender_manager,
        heartbeat_receiver_manager,
        telemetry_manager,
        command_manager,
    ]
    # Start worker processes
    for worker in workers:
        worker.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects
    start_time = time.time()
    controller_is_active = True
    while (time.time() - start_time < 100) and controller_is_active:
        # Check heartbeat receiver queue
        try:
            heartbeat_msg = heartbeat_to_main_queue.get(timeout=0.1)
            main_logger.info(f"Received heartbeat message: {heartbeat_msg}")
        except queue.Empty:
            continue

        # Check telemetry queue
        try:
            telemetry_msg = telemetry_to_command_queue.get(timeout=0.1)
            main_logger.info(f"Received telemetry message: {telemetry_msg}")
        except queue.Empty:
            continue

        # Check command queue
        try:
            command_msg = command_to_main_queue.get(timeout=0.1)
            main_logger.info(f"Received command message: {command_msg}")
        except queue.Empty:
            continue

    # Stop the processes
    main_logger.info("Requested exit")
    controller.request_exit()

    # Fill and drain queues from END TO START
    command_to_main_queue.fill_and_drain_queue()
    telemetry_to_command_queue.fill_and_drain_queue()

    heartbeat_to_main_queue.fill_and_drain_queue()
    main_logger.info("Queues cleared")

    # Clean up worker processes
    for worker in workers:
        worker.join()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    controller.clear_exit()

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")

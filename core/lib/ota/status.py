# esp32_ota module for MicroPython on ESP32
# MIT license; Copyright (c) 2023 Glenn Moloney @glenn20

# Based on OTA class by Thorsten von Eicken (@tve):
#   https://github.com/tve/mqboard/blob/master/mqrepl/mqrepl.py


import binascii
import struct
import sys
import time

import machine
from esp32 import Partition
from flashbdev import bdev
from micropython import const

from logging import logger

OTA_UNSUPPORTED = const(-261)
ESP_ERR_OTA_VALIDATE_FAILED = const(-5379)
OTA_MIN: int = const(16)  # type: ignore
OTA_MAX: int = const(32)  # type: ignore

OTA_SIZE = 0x20  # The size of an OTA record in bytes (32 bytes)
OTA_BLOCKS = (0, 1)  # The offsets of the OTA records in the otadata partition
OTA_FMT = b"<L20sLL"  # The format for reading/writing binary OTA records
OTA_LABEL = b"\xff" * OTA_SIZE  # The expected label field in the OTA record
OTA_CRC_INIT = 0xFFFFFFFF  # The initial value for the CRC32 checksum
OTADATA_TYPE = (1, 0)  # The type and subtype of the otadata partition

otastate = {
    0: "NEW",
    1: "PENDING",
    2: "VALID",
    3: "INVALID",
    4: "ABORTED",
    0xFFFFFFFF: "UNDEFINED",
}

otadata_part = p[0] if (p := Partition.find(*OTADATA_TYPE)) else None
current_ota = Partition(Partition.RUNNING)  # Partition we booted from
next_ota = None  # Partition for the next OTA update (if device is OTA enabled)
try:
    if otadata_part:  # Avoid IDF error messages by checking for otadata partition
        next_ota = current_ota.get_next_update()
except OSError:
    pass


# Return the partition we will boot from on next boot
def boot_ota() -> Partition:  # Partition we will boot from on next boot
    if next_ota:  # Avoid IDF debug messages by checking for otadata partition
        try:
            return Partition(Partition.BOOT)
        except OSError:  # OTA support is not available, return current partition
            pass
    return Partition(Partition.RUNNING)


# Return True if the device is configured for OTA updates
def ready() -> bool:
    return next_ota is not None


# Return a list of OTA partitions sorted by partition subtype number
def ota_partitions() -> list[Partition]:
    partitions: list[Partition] = [
        p
        for p in Partition.find(Partition.TYPE_APP)
        if OTA_MIN <= p.info()[1] < OTA_MAX
    ]
    # Sort by the OTA partition subtype: ota_0 (16), ota_1 (17), ota_2 (18), ...
    partitions.sort(key=lambda p: p.info()[1])
    return partitions


# Print the status of the otadata partition
def otadata_check() -> None:
    if not otadata_part:
        return
    valid_seq = 1
    for i in (0, 1):
        otadata_part.readblocks(i, (b := bytearray(OTA_SIZE)))
        seq, _, state_num, crc = struct.unpack(OTA_FMT, b)
        state = otastate[state_num]
        is_valid = (
            state == "VALID"
            and binascii.crc32(struct.pack(b"<L", seq), OTA_CRC_INIT) == crc
        )
        if is_valid and seq > valid_seq:
            valid_seq = seq
        logger.info(
            f"OTA record: state={state}, seq={seq}, crc={crc}, valid={is_valid}"
        )
        logger.info(
            f"OTA record is {state}."
            + (" Will be updated on next boot." if state == "VALID" else "")
        )
    p = ota_partitions()
    logger.info(f"Next boot is '{p[(valid_seq - 1) % len(p)].info()[4]}'.")


# Print a detailed summary of the OTA status of the device
def status() -> None:
    upyversion, pname = sys.version.split(" ")[2], current_ota.info()[4]
    logger.info(f"Micropython {upyversion} has booted from partition '{pname}'.")
    logger.info(f"Will boot from partition '{boot_ota().info()[4]}' on next reboot.")
    if not ota_partitions():
        logger.warning("There are no OTA partitions available.")
    elif not next_ota:
        logger.warning("No spare OTA partition is available for update.")
    else:
        logger.info(f"The next OTA partition for update is '{next_ota.info()[4]}'.")
    logger.info(f"The / filesystem is mounted from partition '{bdev.info()[4]}'.")
    otadata_check()


# Reboot the device after the provided delay
def ota_reboot(delay=10) -> None:
    logger.info("Rebooting...")
    time.sleep(1)
    machine.reset()  # Reboot into the new image


# Micropython does not support forcing an OTA rollback, so we do it by hand:
# - find the previous ota partition, validate the image and set it bootable.
# Raises OSError(-5379) if validation of the boot image fails.
# Raises OSError(-261) if no OTA partitions are available.
def force_rollback(reboot=False) -> None:
    partitions = ota_partitions()
    for i, p in enumerate(partitions):
        if p.info() == current_ota.info():  # Compare by partition offset
            partitions[i - 1].set_boot()  # Set the previous partition to be bootable
            if reboot:
                ota_reboot()
            return
    raise OSError(OTA_UNSUPPORTED)


# Mark this boot as successful: prevent rollback to last image on next reboot.
# Raises OSError(-261) if bootloader is not OTA capable.
def cancel() -> None:
    try:
        Partition.mark_app_valid_cancel_rollback()
    except OSError as e:
        if e.args[0] == -261:
            logger.error(
                f"{__name__}.cancel(): The bootloader does not support OTA rollback."
            )
        else:
            raise e


# Force a rollback on the next reboot to the previously booted ota partition
def force() -> None:
    force_rollback()


# Undo a previous force rollback: i.e. boot off the current partition on next reboot
def cancel_force() -> None:
    current_ota.set_boot()

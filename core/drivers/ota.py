import machine
from esp32 import Partition


def switch_partition():

    current_partition = Partition(Partition.RUNNING)
    (type, subtype, addr, size, label, encrypted) = current_partition.info()

    next_update = current_partition.get_next_update()
    next_update.set_boot()
    machine.reset()


def confirm_partition():
    Partition.mark_app_valid_cancel_rollback()

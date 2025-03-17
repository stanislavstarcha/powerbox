import argparse
import os

import esptool
from ampy import pyboard
from ampy.files import Files


parser = argparse.ArgumentParser(
    prog="Code initializer",
    description="Erase core and upload fresh code",
)

parser.add_argument("-a", "--address", default="0x1000")
parser.add_argument("-e", "--erase", action="store_true")
parser.add_argument("-n", "--nocode", action="store_true")
parser.add_argument("-b", "--baud_rate", type=int, default=115200)
parser.add_argument("-p", "--port", required=True)
parser.add_argument("-d", "--directory", default="core")
parser.add_argument("-v", "--version", default="1.23")

args = parser.parse_args()
script_dir = os.path.dirname(os.path.abspath(__file__))


def upload_firmware():
    source_directory = f"{script_dir}/{args.directory}"
    target_directory = ""

    # Initialize connection to the board
    pyb = pyboard.Pyboard(args.port, baudrate=args.baud_rate)
    fh = Files(pyb)

    for root, dirs, files_list in os.walk(source_directory):
        rel_path = os.path.relpath(root, source_directory)
        remote_path = os.path.join(target_directory, rel_path)
        try:
            print(f"Creating directory {remote_path}")
            fh.mkdir(remote_path)
        except Exception as e:
            print(f"Directory {remote_path} already exists")
        for file in files_list:
            local_file = os.path.join(root, file)
            remote_file = os.path.join(remote_path, file)
            print(f"Uploading {local_file} to {remote_file}")
            with open(local_file, "rb") as f:
                fh.put(remote_file, f.read())


if args.erase:
    firmware_path = f"{script_dir}/resources/firmware/{args.version}.bin"
    print(f"Writing firmware {firmware_path}")
    esptool.main(["--port", args.port, "erase_flash"])
    esptool.main(
        [
            "--port",
            args.port,
            "write_flash",
            "-z",
            args.address,
            firmware_path,
        ]
    )

if not args.nocode:
    upload_firmware()

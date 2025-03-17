import argparse
import hashlib
import json
import shutil
from pathlib import Path


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Process firmware file.")
    parser.add_argument("--version", required=True, type=str, help="Firmware version")
    parser.add_argument("--path", required=True, type=Path, help="Path to input file")
    parser.add_argument(
        "--output", type=Path, default=script_dir / "build", help="Output directory"
    )
    args = parser.parse_args()

    build_dir = (
        (script_dir / args.output).resolve()
        if not args.output.is_absolute()
        else args.output.resolve()
    )
    build_dir.mkdir(parents=True, exist_ok=True)

    input_file = args.path.resolve()
    if not input_file.exists() or not input_file.is_file():
        print(f"Error: File '{input_file}' does not exist.")
        exit(1)

    firmware_path = build_dir / "firmware.bin"
    shutil.copy(input_file, firmware_path)

    file_length = input_file.stat().st_size
    file_sha256 = calculate_sha256(input_file)

    firmware_json = {
        "firmware": f"https://github.com/stanislavstarcha/powerbox/releases/download/{args.version}/firmware.bin",
        "version": args.version,
        "sha": file_sha256,
        "length": file_length,
    }

    with open(build_dir / "firmware.json", "w") as f:
        json.dump(firmware_json, f, indent=4)

    print("Firmware processing complete.")


if __name__ == "__main__":
    main()

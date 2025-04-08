import argparse
import hashlib
import json
import shutil
from pathlib import Path
import importlib.util
import subprocess
import requests

REPO = "stanislavstarcha/powerbox"


def import_variable(file_path, variable_name):
    """
    Dynamically imports a variable from a Python file.

    Args:
        file_path (str): Path to the Python file.
        variable_name (str): Name of the variable to import.

    Returns:
        Any: The value of the specified variable, or None if not found.
    """
    spec = importlib.util.spec_from_file_location("module_name", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, variable_name, None)


def calculate_sha256(file_path):
    """
    Calculates the SHA-256 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: Hexadecimal SHA-256 hash of the file content.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def build(lvgl_path):
    """
    Builds the firmware for ESP32 using the specified LVGL path and predefined arguments.

    Args:
        lvgl_path (str or Path): Path to the LVGL build system directory.

    Raises:
        RuntimeError: If the build process exits with a non-zero return code.
    """
    source_dir = (Path(__file__).resolve().parent / "..").resolve()
    args = [
        "python",
        "make.py",
        "esp32",
        "BOARD=ESP32_GENERIC_S3",
        "DISPLAY=ILI9488",
        f"FROZEN_MANIFEST={source_dir}/manifest.py",
        "BOARD_VARIANT=SPIRAM_OCT",
        "--flash-size=16",
        "--ota",
    ]

    with subprocess.Popen(
        args,
        cwd=lvgl_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as proc:
        for line in proc.stdout:
            print(line, end="")

    if proc.returncode != 0:
        raise RuntimeError(f"Process failed with code {proc.returncode}")


def stage(lvgl_path, version):
    """
    Prepares firmware and metadata for release by copying the built binary and
    generating a firmware.json file with hash, size, and version info.

    Args:
        lvgl_path (str or Path): Path to the LVGL build system directory.
        version (str): Firmware version to include in the metadata.
    """
    script_dir = Path(__file__).resolve().parent
    stage_dir = (script_dir / "build").resolve()
    stage_dir.mkdir(parents=True, exist_ok=True)

    firmware_stage_path = stage_dir / "firmware.bin"
    firmware_source_path = Path(
        f"{lvgl_path}/lib/micropython/ports/esp32/build-ESP32_GENERIC_S3-SPIRAM_OCT/micropython.bin"
    )
    shutil.copy(firmware_source_path, firmware_stage_path)

    file_length = firmware_source_path.stat().st_size
    file_sha256 = calculate_sha256(firmware_source_path)

    firmware_json = {
        "firmware": f"https://github.com/stanislavstarcha/powerbox/releases/download/{version}/firmware.bin",
        "version": version,
        "sha": file_sha256,
        "length": file_length,
    }

    with open(stage_dir / "firmware.json", "w") as f:
        json.dump(firmware_json, f, indent=4)

    return True


def publish(version, token):
    """
    Publishes a new firmware release on GitHub by creating a release and uploading
    the firmware binary and metadata JSON.

    Args:
        version (str): The version tag to use for the GitHub release.
        token (str): Github token.

    Raises:
        HTTPError: If any HTTP request fails during the release or upload process.
    """
    script_dir = Path(__file__).resolve().parent
    bin_path = script_dir / "build" / "firmware.bin"
    json_path = script_dir / "build" / "firmware.json"

    RELEASE_NAME = "Release " + version
    API_URL = f"https://api.github.com/repos/{REPO}/releases"
    headers = {"Authorization": f"token {token}"}

    release_data = {
        "tag_name": version,
        "name": RELEASE_NAME,
        "draft": False,
        "prerelease": False,
    }

    r = requests.post(API_URL, headers=headers, data=json.dumps(release_data))
    r.raise_for_status()
    upload_url = r.json()["upload_url"].split("{")[0]

    # Step 3: Attach binaries
    for file_path in [bin_path, json_path]:
        with open(file_path, "rb") as f:
            headers.update({"Content-Type": "application/octet-stream"})
            params = {"name": file_path.name}
            upload = requests.post(upload_url, headers=headers, params=params, data=f)
            upload.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description="Build and publish release.")
    parser.add_argument(
        "--lvgl",
        required=True,
        type=Path,
        help="Path to LVGL directory",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Github token",
    )

    args = parser.parse_args()

    version = import_variable(
        "core/version.py",
        "FIRMWARE",
    )

    succeeded = build(args.lvgl)

    if succeeded:
        succeeded = stage(args.lvgl, version)

    if succeeded:
        publish(version, args.token)

    print("Firmware processing complete.")


if __name__ == "__main__":
    main()

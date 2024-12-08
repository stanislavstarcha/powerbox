# setup ESP32 chip

### ESP32 S3

1. Find port `ls /dev/tty*`

A typical serial port should look like this 
- `/dev/tty.usbmodem11101`
- `/dev/cu.usbserial-0001`
- `/dev/tty.usbmodem1234561`

In case serial port does not respond, a host restart might be needed 

2. Update firmware 

**ESP32S3 (usb-c)**

Download firmware https://micropython.org/resources/firmware/ESP32_GENERIC_S3-20240602-v1.23.0.bin
or specific version at
https://micropython.org/download/ESP32_GENERIC_S3/

```
esptool.py --chip esp32s3 --baud 9600 --port /dev/tty.usbmodem1234561 erase_flash
esptool.py --chip esp32s3 --baud 9600 write_flash -z 0 ./resources/firmware/ESP32_GENERIC_S3-20240602-v1.23.0.bin
```

ESP32 (microusb)

Download firmware https://micropython.org/resources/firmware/ESP32_GENERIC-20240602-v1.23.0.bin
or specific version at
https://micropython.org/download/ESP32_GENERIC/

```
esptool.py --chip esp32 --baud 115200 --port /dev/cu.usbserial-0001 erase_flash
esptool.py --chip esp32 --baud 460800 --port /dev/cu.usbserial-0001 write_flash -z 0x1000 ./resources/firmware/ESP32_GENERIC-20240602-v1.23.0.bin
```

```
python initialize.py \
--baud_rate 115200 \
--port /dev/cu.usbserial-0001 \
--erase

mpremote connect /dev/cu.usbserial-0001 exec "import machine; machine.reset()"
```

Building OTA micropython

1. Install esp-idf (see README.md)
```
cd esp-idf
./install.sh
source export.sh
```
2. Build micropython with OTA support


```
export $POWERBOX_HOME="~/workspace/powerbox"
cd micropython/ports/esp32
make BOARD=ESP32_GENERIC FROZEN_MANIFEST=$POWERBOX_HOME/manifest.py BOARD_VARIANT=OTA
```

```
python -m esptool --chip esp32 -b 460800 --port /dev/cu.usbserial-0001 \
--before default_reset --after hard_reset write_flash \
--flash_mode dio --flash_size 4MB --flash_freq 40m \
0x1000 build-ESP32_GENERIC-OTA/bootloader/bootloader.bin \
0x8000 build-ESP32_GENERIC-OTA/partition_table/partition-table.bin \
0xd000 build-ESP32_GENERIC-OTA/ota_data_initial.bin \
0x10000 $POWERBOX_HOME/resources/firmware/ota-0.8.0.bin \
0x190000 $POWERBOX_HOME/resources/firmware/ota-0.10.0.bin
```
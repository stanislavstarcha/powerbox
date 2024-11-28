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

Building micropython
```
cd micropython/ports/esp32
make BOARD=MYBOARD FROZEN_MANIFEST=/path/to/my/project/manifest.py
```

Freeze codebase
```
```

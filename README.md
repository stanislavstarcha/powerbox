# Install and run firmware

```shell
cd $HOME
git clone https://github.com/stanislavstarcha/powerbox
export POWERBOX_HOME=$HOME/powerbox
```

Connect ESP32 to USB and find the port `ls /dev/tty*`

A typical serial port should look like this 
- `/dev/tty.usbmodem11101`
- `/dev/cu.usbserial-0001`
- `/dev/tty.usbmodem1234561`


## Build firmware

Install LVGL micropython
```shell
cd $HOME
git clone https://github.com/lvgl-micropython/lvgl_micropython
export LVGL_HOME=$HOME/workspace/lvgl_micropython
```

### Copy fonts
```shell
cp ./resources/fonts/Roboto-Black.ttf $LVGL_HOME/lib/lvgl/scripts/built_in_font
cp ./resources/fonts/Roboto-Regular.ttf $LVGL_HOME/lib/lvgl/scripts/built_in_font
cp ./resources/fonts/Material-Sharp-28.ttf $LVGL_HOME/lib/lvgl/scripts/built_in_font

```

### Build fonts

Modify `$LVGL_HOME/lib/lvgl/scripts/built_in_font/generate_all.py` and add 

```python
print("\nGenerating 12 px Roboto Ukrainian")
os.system("lv_font_conv --no-compress --no-prefilter --bpp 2 --size 12 --font Roboto-Regular.ttf --format lvgl -o lv_font_roboto_12.c -r 0xB0,0x20-0x22,0x25,0x27-0x40,0x5B-0x5F,0x7B-0x7D,0xA0,0xA7,0xA9,0xAB,0xBB,0x2BC,0x404,0x406-0x407,0x410-0x429,0x42C,0x42E-0x449,0x44C,0x44E-0x44F,0x454,0x456-0x457,0x490-0x491,0x2011,0x2013,0x2019,0x201C,0x201E,0x2030,0x20AC,0x2116")

print("\nGenerating 24 px Glyphs")
os.system("lv_font_conv --no-compress --no-prefilter --bpp 2 --size 24 --font Material-Sharp-28.ttf --format lvgl -o lv_font_material_24.c -r 0xEAC3,0xEAC9,0xEAD0,0xEACF,0xE000,0xe1a7,0xe1a8,0xf156,0xE7EE,0xe5d3,0xe322,0xe87d")

print("\nGenerating 24 px Roboto")
os.system("lv_font_conv --no-compress --no-prefilter --bpp 2 --size 26 --font Roboto-Black.ttf --format lvgl -o lv_font_roboto_24.c -r 0x20,0x30-0x39,0x412,0x442")

print("\nGenerating 120 px Roboto")
os.system("lv_font_conv --no-compress --no-prefilter --bpp 2 --size 120 --font Roboto-Black.ttf --format lvgl -o lv_font_roboto_120.c --symbols 0123456789%")
```

and then build the fonts

```shell
cd $LVGL_HOME/lib/lvgl/scripts/built_in_font
python generate_all.py
```


### Modify headers

Open `$LVGL_HOME/lib/lvconf.h`

And set to 0 (disable) all `#define LV_FONT_MONTSERRAT_*`
and define custom fonts we've built earlier

```
#define LV_FONT_MONTSERRAT_14 0
...

#define LV_FONT_CUSTOM_DECLARE LV_FONT_DECLARE(lv_font_roboto_12) LV_FONT_DECLARE(lv_font_roboto_24) LV_FONT_DECLARE(lv_font_roboto_120) LV_FONT_DECLARE(lv_font_material_24)

#define LV_FONT_DEFAULT &lv_font_roboto_12
```


### Build binaries

ESP32 version 

```shell
cd $LVGL_HOME
python make.py esp32 BOARD=ESP32_GENERIC DISPLAY=ILI9488 FROZEN_MANIFEST=$POWERBOX_HOME/manifest.py
```

ESP32-S3 OTA version
```shell
cd $LVGL_HOME
python make.py esp32 BOARD=ESP32_GENERIC_S3 DISPLAY=ILI9488 \
FROZEN_MANIFEST=$POWERBOX_HOME/manifest.py BOARD_VARIANT=SPIRAM_OCT \
--flash-size=16 \ 
--ota
```

### Flash firmware

Instead of `/dev/cu.usbserial-0001` use the actual port 

```shell
cd $LVGL_HOME

    python -m esptool --chip esp32s3 -p /dev/tty.wchusbserial59710258441 \
-b 460800 --before default_reset --after hard_reset write_flash \
--flash_mode dio --flash_size 16MB --flash_freq 80m --erase-all \
0x0 /Users/stasstarcha/workspace/lvgl_micropython/build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin
```

Manually write second partition
```
python -m esptool --chip esp32s3 -p /dev/tty.wchusbserial59710258441 -b 460800 \
--before default_reset --after no_reset write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m \
0x280000 lib/micropython/ports/esp32/build-ESP32_GENERIC_S3-SPIRAM_OCT/micropython.bin
```


The above puts micropython, LVGL library, and the actual code into the firmware.


### Development mode

During development, it's easier to update files one by one.

```shell
python initialize.py \
--baud_rate 115200 \
--port /dev/cu.usbserial-0001
```
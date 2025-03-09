import lvgl as lv  # NOQA
import random

from drivers.display.screens import BaseScreen


class IdleScreen(BaseScreen):

    BASE_X = 200
    BASE_Y = 120

    progress_body = None
    left_eye = None
    right_eye = None
    capacity = None

    def create_widgets(self):

        self._screen.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)

        self._screen.set_style_pad_all(0, lv.PART.MAIN)
        self._screen.set_style_margin_all(0, lv.PART.MAIN)
        self._screen.set_style_pad_gap(0, lv.PART.MAIN)

        self.capacity = self.create_label(
            None,
            None,
            is_hidden=False,
            x=self.BASE_X + 45,
            y=self.BASE_Y + 50,
        )
        self.progress_body = self.create_arc(
            x=self.BASE_X,
            y=self.BASE_Y,
            rotation=340,
            start_angle=0,
            end_angle=290,
            radius=53,
            thickness=5,
            value=90,
        )

        # head
        self.create_arc(
            x=self.BASE_X + 46,
            y=self.BASE_Y - 26,
            rotation=200,
            start_angle=0,
            end_angle=32,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X - 15,
            y=self.BASE_Y - 35,
            rotation=330,
            start_angle=0,
            end_angle=20,
            radius=43,
            thickness=5,
        )

        self.create_arc(
            x=self.BASE_X + 17,
            y=self.BASE_Y - 3,
            rotation=280,
            start_angle=0,
            end_angle=32,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X + 67,
            y=self.BASE_Y - 3,
            rotation=230,
            start_angle=0,
            end_angle=20,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X + 15,
            y=self.BASE_Y - 37,
            rotation=350,
            start_angle=0,
            end_angle=62,
            radius=43,
            thickness=5,
        )

        self.create_arc(
            x=self.BASE_X + 44,
            y=self.BASE_Y - 8,
            rotation=55,
            start_angle=0,
            end_angle=90,
            radius=26,
            thickness=5,
        )

        # arc(scr, x=self.BASE_X+57, y=self.BASE_Y+12, rotation=60, start_angle=0, end_angle=110, radius=6, thickness=3,)
        # arc(scr, x=self.BASE_X+70, y=self.BASE_Y+18, rotation=60, start_angle=0, end_angle=110, radius=6, thickness=3,)

        # eyes
        self.left_eye = self.create_arc(
            x=self.BASE_X + 57,
            y=self.BASE_Y + 12,
            rotation=60,
            start_angle=0,
            end_angle=110,
            radius=6,
            thickness=3,
        )
        self.right_eye = self.create_arc(
            x=self.BASE_X + 70,
            y=self.BASE_Y + 18,
            rotation=60,
            start_angle=0,
            end_angle=110,
            radius=6,
            thickness=3,
        )

    def set_eyes(self, is_open):

        if is_open:
            self.left_eye.set_bg_end_angle(350)
            self.right_eye.set_bg_end_angle(350)
        else:
            self.left_eye.set_bg_end_angle(110)
            self.right_eye.set_bg_end_angle(110)

    def set_capacity(self, value):
        if value is None:
            return

        start_angle = self.progress_body.get_bg_angle_start()
        end_angle = self.progress_body.get_bg_angle_end()
        offset = int((100 - value) * (end_angle - start_angle) / 100)
        self.progress_body.set_angles(start_angle + offset, end_angle)
        self.capacity.set_text(f"{value}%")

    def generate_random_state(self):
        self.set_eyes(random.randint(0, 1))
        self.set_capacity(random.randint(0, 100))

    def on_bms_state(self, state):
        self.set_capacity(state.soc)
        self.set_eyes(random.randint(0, 100) > 80)

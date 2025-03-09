import lvgl as lv  # NOQA


class BaseScreen:

    _screen = None

    def __init__(self):
        self._screen = lv.obj(None)

    @staticmethod
    def hide_widget(widget):
        widget.add_flag(lv.obj.FLAG.HIDDEN)

    @staticmethod
    def show_widget(widget):
        widget.remove_flag(lv.obj.FLAG.HIDDEN)

    def get_screen(self):
        return self._screen

    def create_widgets(self):
        pass

    def create_glyph(
        self, col, row, code, col_span=1, row_span=1, color="white", is_hidden=True
    ):
        glyph = lv.label(self._screen)
        glyph.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        glyph.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        glyph.set_style_text_font(lv.font_material_24, 0)
        glyph.set_style_text_color(self.color_to_hex(color), 0)
        glyph.set_text(chr(code))
        glyph.set_grid_cell(
            lv.GRID_ALIGN.CENTER, col, col_span, lv.GRID_ALIGN.CENTER, row, row_span
        )
        if is_hidden:
            self.hide_widget(glyph)
        return glyph

    def create_bar(self, col, row, col_span=1, row_span=1, is_hidden=True):
        bar = lv.bar(self._screen)
        bar.set_size(200, 20)
        bar.set_value(75, lv.ANIM.OFF)

        bar.set_style_bg_color(self.color_to_hex("green"), lv.PART.INDICATOR)

        bar.set_style_radius(3, lv.PART.MAIN)
        bar.set_style_radius(3, lv.PART.INDICATOR)
        bar.set_grid_cell(
            lv.GRID_ALIGN.CENTER, col, col_span, lv.GRID_ALIGN.CENTER, row, row_span
        )
        if is_hidden:
            self.hide_widget(bar)
        return bar

    def create_label(
        self,
        col=None,
        row=None,
        t="",
        col_span=1,
        row_span=1,
        font_size=12,
        color="white",
        x=None,
        y=None,
        is_hidden=True,
    ):
        label = lv.label(self._screen)
        label.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        label.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        label.set_style_text_color(self.color_to_hex(color), 0)

        if font_size == 12:
            label.set_style_text_font(lv.font_roboto_12, 0)

        if font_size == 120:
            label.set_style_text_font(lv.font_roboto_120, 0)

        if font_size == 10:
            label.set_style_text_font(lv.font_montserrat_10, 0)

        if font_size == 24:
            label.set_style_text_font(lv.font_roboto_24, 0)

        if x is not None:
            label.set_style_x(x, lv.PART.MAIN)

        if y is not None:
            label.set_style_y(y, lv.PART.MAIN)

        label.set_text(t)

        if col is not None and row is not None:
            label.set_grid_cell(
                lv.GRID_ALIGN.CENTER,
                col,
                col_span,
                lv.GRID_ALIGN.CENTER,
                row,
                row_span,
            )

        if is_hidden:
            self.hide_widget(label)

        return label

    def create_arc(
        self,
        x=0,
        y=0,
        rotation=0,
        start_angle=0,
        end_angle=360,
        radius=53,
        thickness=5,
        value=None,
    ):

        arc = lv.arc(self._screen)

        arc.set_x(x)
        arc.set_y(y)
        arc.set_size(radius * 2, radius * 2)
        arc.set_rotation(rotation)

        arc.remove_style(None, lv.PART.KNOB)

        arc.set_style_arc_rounded(False, lv.PART.MAIN | lv.STATE.DEFAULT)
        arc.set_style_arc_rounded(False, lv.PART.INDICATOR | lv.STATE.DEFAULT)

        arc.set_style_arc_width(thickness, lv.PART.MAIN | lv.STATE.DEFAULT)
        arc.set_style_arc_width(thickness, lv.PART.INDICATOR | lv.STATE.DEFAULT)

        if value:
            arc.set_style_arc_color(self.color_to_hex("grey"), lv.PART.MAIN)
            arc.set_bg_angles(start_angle, end_angle)

            offset = int(value * (end_angle - start_angle) / 100)
            arc.set_style_arc_color(self.color_to_hex("white"), lv.PART.INDICATOR)
            arc.set_angles(start_angle + offset, end_angle)
        else:
            arc.remove_style(None, lv.PART.INDICATOR)

            arc.set_style_arc_color(self.color_to_hex("white"), lv.PART.MAIN)
            arc.set_bg_angles(start_angle, end_angle)

        return arc

    @staticmethod
    def color_to_hex(color):
        if color == "white":
            return lv.color_hex(0x000000)

        if color == "grey":
            return lv.color_hex(0x888888)

        if color == "red":
            return lv.color_hex(0x44FFFF)

        if color == "green":
            return lv.color_hex(0xFF44FF)

        return lv.color_hex(0x000000)

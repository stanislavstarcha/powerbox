import lvgl as lv  # NOQA

class BaseScreen:
    """
    BaseScreen class to manage screen elements using the LVGL library.
    
    Attributes:
        _screen (lv.obj): The LVGL object representing the screen.
    """

    _screen = None

    def __init__(self):
        """
        Initializes the BaseScreen by creating a new LVGL object.
        """
        self._screen = lv.obj(None)

    @staticmethod
    def hide_widget(widget):
        """
        Hides the given widget by adding the HIDDEN flag.

        Args:
            widget (lv.obj): The widget to hide.
        """
        widget.add_flag(lv.obj.FLAG.HIDDEN)

    @staticmethod
    def show_widget(widget):
        """
        Shows the given widget by removing the HIDDEN flag.

        Args:
            widget (lv.obj): The widget to show.
        """
        widget.remove_flag(lv.obj.FLAG.HIDDEN)

    def get_screen(self):
        """
        Retrieves the underlying screen object.

        Returns:
            lv.obj: The screen object.
        """
        return self._screen

    def create_widgets(self):
        """
        Creates and arranges widgets on the screen.
        This method should be overridden by subclasses.
        """
        pass

    def create_glyph(
        self, col, row, code, col_span=1, row_span=1, color="white", is_hidden=True
    ):
        """
        Creates a glyph (label) widget on the screen.

        Args:
            col (int): The column position for the glyph.
            row (int): The row position for the glyph.
            code (int): The Unicode code corresponding to the glyph.
            col_span (int, optional): Number of columns the glyph spans. Defaults to 1.
            row_span (int, optional): Number of rows the glyph spans. Defaults to 1.
            color (str, optional): The color of the glyph. Defaults to "white".
            is_hidden (bool, optional): Whether the glyph is initially hidden. Defaults to True.

        Returns:
            lv.label: The created glyph widget.
        """
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
        """
        Creates a bar widget on the screen.

        Args:
            col (int): The column position for the bar.
            row (int): The row position for the bar.
            col_span (int, optional): Number of columns the bar spans. Defaults to 1.
            row_span (int, optional): Number of rows the bar spans. Defaults to 1.
            is_hidden (bool, optional): Whether the bar is initially hidden. Defaults to True.

        Returns:
            lv.bar: The created bar widget.
        """
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
        """
        Creates a label widget on the screen.

        Args:
            col (int, optional): The column position for the label.
            row (int, optional): The row position for the label.
            t (str, optional): The text content of the label. Defaults to "".
            col_span (int, optional): Number of columns the label spans. Defaults to 1.
            row_span (int, optional): Number of rows the label spans. Defaults to 1.
            font_size (int, optional): The font size of the label. Defaults to 12.
            color (str, optional): The text color of the label. Defaults to "white".
            x (int, optional): x-coordinate for the label position. Defaults to None.
            y (int, optional): y-coordinate for the label position. Defaults to None.
            is_hidden (bool, optional): Whether the label is initially hidden. Defaults to True.

        Returns:
            lv.label: The created label widget.
        """
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
        """
        Creates an arc widget on the screen.

        Args:
            x (int, optional): The x-coordinate of the arc. Defaults to 0.
            y (int, optional): The y-coordinate of the arc. Defaults to 0.
            rotation (int, optional): The rotation angle of the arc. Defaults to 0.
            start_angle (int, optional): The starting angle for the arc. Defaults to 0.
            end_angle (int, optional): The ending angle for the arc. Defaults to 360.
            radius (int, optional): The radius of the arc. Defaults to 53.
            thickness (int, optional): The thickness of the arc. Defaults to 5.
            value (int, optional): The value used to adjust the arc. Defaults to None.

        Returns:
            lv.arc: The created arc widget.
        """
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
        """
        Converts the given color name into an LVGL hexadecimal color.

        Args:
            color (str): The color name.

        Returns:
            lv.color_hex: The corresponding LVGL color in hexadecimal.
        """
        if color == "white":
            return lv.color_hex(0x000000)

        if color == "grey":
            return lv.color_hex(0x888888)

        if color == "red":
            return lv.color_hex(0x44FFFF)

        if color == "green":
            return lv.color_hex(0xFF44FF)

        if color == "blue":
            return lv.color_hex(0xBB3200)

        return lv.color_hex(0x000000)

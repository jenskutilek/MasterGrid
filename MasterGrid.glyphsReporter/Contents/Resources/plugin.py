import objc
from AppKit import (
    NSApplication,
    NSBezierPath,
    NSClassFromString,
    NSColor,
    NSMenuItem,
    NSNotificationCenter,
    NSPoint,
)
from GlyphsApp import OFFCURVE, Glyphs, Message
from GlyphsApp.plugins import ReporterPlugin

plugin_id = "de.kutilek.MasterGrid"

KEY_GRID_VALUE = f"{plugin_id}.value"
KEY_GRID_TYPE = f"{plugin_id}.type"
KEY_GRID_COLOR = f"{plugin_id}.color"
KEY_MARKER_COLOR = f"{plugin_id}.markercolor"

can_display_ui = True


def getGrid(master) -> tuple[int, int, str]:
    grid = master.userData[KEY_GRID_VALUE]
    if grid is not None:
        gx, gy = grid
    else:
        gx = gy = 0

    grid_type = master.userData[KEY_GRID_TYPE]
    if grid_type is None:
        grid_type = "units"

    return gx, gy, grid_type


def setGrid(
    master, x: float | None, y: float | None = None, grid_type: str | None = None
) -> None:
    if x is None:
        x = 0
    if x == 0:
        deleteGrid(master)
        return
    if y is None:
        y = x
    master.userData[KEY_GRID_VALUE] = [x, y]
    if grid_type is None:
        if master.userData[KEY_GRID_TYPE] is not None:
            del master.userData[KEY_GRID_TYPE]
    else:
        master.userData[KEY_GRID_TYPE] = grid_type


def deleteGrid(master) -> None:
    for key in (KEY_GRID_VALUE, KEY_GRID_TYPE):
        if master.userData[key] is not None:
            del master.userData[key]


def CurrentMaster():
    font = NSApplication.sharedApplication().font
    if font is None or font.selectedLayers is None:
        return None
    layer = font.selectedLayers[0]
    master = layer.parent.parent.masters[layer.layerId]
    return master


class GridDialog:
    def __init__(self) -> None:
        global can_display_ui
        if not can_display_ui:
            return
        try:
            import vanilla
        except ImportError:
            Message(
                message=(
                    "Please install vanilla to enable UI dialogs for "
                    "Master Grid. You can install vanilla through "
                    "Glyphs > Window > Plugin Manager > Modules."
                ),
                title="Missing Module",
            )
            can_display_ui = False
            return

        self.w = vanilla.Window(
            (220, 160),
            "Master Grid",
        )
        y = 8
        self.w.master_name = vanilla.TextBox(
            (8, y, -8, 35), "Set local grid for master:\nNone"
        )

        y += 46
        x = 8
        self.w.label_x = vanilla.TextBox((x, y, 30, 17), "X:")
        self.w.x = vanilla.EditText((x + 22, y - 3, 40, 24))
        x = 88
        self.w.label_y = vanilla.TextBox((x, y, 30, 17), "Y:")
        self.w.y = vanilla.EditText((x + 22, y - 3, 40, 24))

        y += 28
        self.w.grid_type_label = vanilla.TextBox((8, y, 66, 17), "Grid is in:")
        self.w.grid_type = vanilla.RadioGroup(
            (74, y, -8, 40),
            ["Absolute font units", "UPM subdivision"],
            isVertical=True,
        )

        self.w.button_delete = vanilla.Button(
            (10, -30, 102, -10),
            "Remove Grid",
            callback=self.callback_delete,
        )
        self.w.button_set = vanilla.Button(
            (118, -30, 74, -10),
            "Set Grid",
            callback=self.callback_set,
        )
        self.update()
        self.w.open()
        self.w.makeKey()

    def update(self) -> None:
        self.master = CurrentMaster()
        if self.master is None:
            self.w.master_name.set("Set local grid for master:\nNone")
            self.w.x.set("0")
            self.w.y.set("0")

            self.w.x.enable(False)
            self.w.y.enable(False)
            self.w.grid_type.enable(False)
            self.w.button_delete.enable(False)
            self.w.button_set.enable(False)
        else:
            self.w.master_name.set("Set local grid for master:\n" + self.master.name)
            gx, gy, grid_type = getGrid(self.master)
            self.w.x.set(gx)
            self.w.y.set(gy)
            if grid_type == "div":
                self.w.grid_type.set(1)
            else:
                self.w.grid_type.set(0)

            self.w.x.enable(True)
            self.w.y.enable(True)
            self.w.grid_type.enable(True)
            self.w.button_delete.enable(True)
            self.w.button_set.enable(True)

    def callback_cancel(self, info) -> None:
        self.w.close()

    def callback_delete(self, info) -> None:
        deleteGrid(self.master)
        self.w.close()

    def callback_set(self, info) -> None:
        gx = self.w.x.get()
        gy = self.w.y.get()
        grid_type = self.w.grid_type.get()
        if grid_type == 0:
            grid_type = "units"
        else:
            grid_type = "div"
        try:
            gxi = abs(int(gx))
            gyi = abs(int(gy))
            gxf = abs(float(gx))
            gyf = abs(float(gy))
        except ValueError:
            print("Please enter a floating point number or an integer number.")
            return
        if gxf == gxi:
            gx = gxi
        else:
            gx = gxf
        if gyf == gyi:
            gy = gyi
        else:
            gy = gyf
        setGrid(self.master, gx, gy, grid_type)
        self.w.close()
        NSNotificationCenter.defaultCenter().postNotificationName_object_(
            "GSRedrawEditView", None
        )


class MasterGrid(ReporterPlugin):
    @objc.python_method
    def settings(self):
        self.menuName = Glyphs.localize({"en": "Master Grid", "de": "Master-Raster"})

    @objc.python_method
    def start(self):
        mainMenu = NSApplication.sharedApplication().mainMenu()
        s = objc.selector(self.editMasterGrid, signature=b"v@:@")
        newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            Glyphs.localize({"en": "Master Grid…", "de": "Master-Raster…"}), s, ""
        )
        newMenuItem.setTarget_(self)
        submenu = mainMenu.itemAtIndex_(2).submenu()
        submenu.addItem_(newMenuItem)
        self.grid_color = Glyphs.defaults.get(KEY_GRID_COLOR, (0.0, 0.0, 0.0, 0.1))
        self.marker_color = Glyphs.defaults.get(KEY_MARKER_COLOR, (0.0, 0.0, 0.0, 0.25))

    @objc.python_method
    def background(self, layer) -> None:
        # Check if the grid should be drawn

        currentController = None
        if self.controller is not None:
            currentController = self.controller.view().window().windowController()
        if currentController:
            tool = currentController.toolDrawDelegate()
            if tool.isKindOfClass_(
                NSClassFromString("GlyphsToolText")
            ) or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand")):
                return

        try:
            master = layer.master
        except:  # noqa: E722
            return
        if master is None:
            return

        gx, gy, grid_type = getGrid(master)
        if gx == 0 and gy == 0:
            return

        upm = layer.parent.parent.upm
        if grid_type == "div":
            if gx != 0:
                gx = upm / gx
            if gy != 0:
                gy = upm / gy

        NSColor.colorWithCalibratedRed_green_blue_alpha_(*self.grid_color).set()
        NSBezierPath.setDefaultLineWidth_(0.6 / self.getScale())

        max_xx = layer.width
        min_yy = int(layer.descender)
        max_yy = int(layer.ascender)

        if gy == 0 or gy == upm:
            min_y = min_yy
            max_y = max_yy
        else:
            min_y = int(layer.descender // gy)
            max_y = int(layer.ascender // gy + 1)
            min_yy = min_y * gy
            max_yy = max_y * gy

        if gx != 0:
            max_x = int(layer.width // gx + 1)
            max_xx = max_x * gx

            for x in range(max_x + 1):
                xx = gx * x
                NSBezierPath.strokeLineFromPoint_toPoint_(
                    NSPoint(xx, min_yy), NSPoint(xx, max_yy)
                )

        if gy not in (0, upm):
            for y in range(min_y, max_y + 1):
                yy = gy * y
                NSBezierPath.strokeLineFromPoint_toPoint_(
                    NSPoint(0, yy), NSPoint(max_xx, yy)
                )
        else:
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(0, min_yy), NSPoint(max_xx, min_yy)
            )
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(0, max_yy), NSPoint(max_xx, max_yy)
            )

        # Draw markers for nodes and anchors that are on the grid

        s = round(12 / self.getScale())
        s2 = s * 0.25
        sel = round(13 / self.getScale())

        NSColor.colorWithCalibratedRed_green_blue_alpha_(*self.marker_color).set()

        for p in layer.paths:
            for n in p.nodes:
                if n.type != OFFCURVE:
                    if n.selected:
                        s1 = sel
                    else:
                        s1 = s
                    self.drawMarker(n.position.x, n.position.y, s1, s2, gx, gy, upm)
        for a in layer.anchors:
            if a.selected:
                s1 = sel
            else:
                s1 = s
            self.drawMarker(a.position.x, a.position.y, s1, s2, gx, gy, upm)

    @objc.python_method
    def drawMarker(
        self, x: float, y: float, s1: float, s2: float, gx: float, gy: float, upm: int
    ) -> None:
        """
        If x or y are on the grid, draw a marker.

        Args:
            x (float): The x coordinate of the point to be checked.
            y (float): The y coordinate of the point to be checked.
            s1 (float): The length of the marker in grid direction.
            s2 (float): The offset of the marker from the point.
            gx (float): The x grid.
            gy (float): The y grid.
            upm (int): The units per em value.
        """
        if gx not in (0, upm) and abs((abs(x) + 1) % gx - 1) < 0.5:
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(x - s2, y - s1), NSPoint(x - s2, y + s1)
            )
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(x + s2, y - s1), NSPoint(x + s2, y + s1)
            )
        if gy not in (0, upm) and abs((abs(y) + 1) % gy - 1) < 0.5:
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(x - s1, y - s2), NSPoint(x + s1, y - s2)
            )
            NSBezierPath.strokeLineFromPoint_toPoint_(
                NSPoint(x - s1, y + s2), NSPoint(x + s1, y + s2)
            )

    def editMasterGrid(self) -> None:
        GridDialog()

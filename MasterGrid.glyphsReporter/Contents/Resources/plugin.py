# encoding: utf-8

from GlyphsApp.plugins import *

try:
	import vanilla
	can_display_ui = True
except:
	can_display_ui = False
	print "Please install vanilla to enable UI dialogs for MasterGrid. You can install vanilla through Glyphs > Preferences > Addons > Modules."


plugin_id = "de.kutilek.MasterGrid"




def getGrid(master):
	grid = master.userData["%s.value" % plugin_id]
	if grid is not None:
		gx, gy = grid
	else:
		gx = gy = 0

	grid_type = master.userData["%s.type" % plugin_id]
	if grid_type is None:
		grid_type = "units"

	return gx, gy, grid_type


def setGrid(master, x, y=None, grid_type=None):
	if x is None:
		x = 0
	if x == 0:
		deleteGrid(master)
		return
	if y is None:
		y = x
	master.userData["%s.value" % plugin_id] = [x, y]
	if grid_type is None:
		if master.userData["%s.type" % plugin_id] is not None:
			del master.userData["%s.type" % plugin_id]
	else:
		master.userData["%s.type" % plugin_id] = grid_type


def deleteGrid(master):
	for key in ("value", "type"):
		full_key = "%s.%s" % (plugin_id, key)
		if master.userData[full_key] is not None:
			del master.userData[full_key]


def CurrentMaster():
	font = NSApplication.sharedApplication().font
	if font is None:
		return None
	layer = font.selectedLayers[0]
	master = layer.parent.parent.masters[layer.layerId]
	return master



class GridDialog(object):

	def __init__(self):
		self.w = vanilla.Window(
			(300, 160),
			"Master Grid", 
		)
		y = 8
		self.w.master_name = vanilla.TextBox((8, y, -8, 17), "Set local grid for master: None")
		
		y += 28
		x = 8
		self.w.label_x = vanilla.TextBox((x, y, 30, 17), "X:")
		self.w.x = vanilla.EditText((x + 22, y-3, 40, 24))
		x = 88
		self.w.label_y = vanilla.TextBox((x, y, 30, 17), "Y:")
		self.w.y = vanilla.EditText((x + 22, y-3, 40, 24))
		
		y += 32
		self.w.grid_type_label = vanilla.TextBox((8, y, 66, 17), "Grid is in:")
		self.w.grid_type = vanilla.RadioGroup(
			(74, y, -8, 40),
			["Absolute font units", "UPM subdivision"],
			isVertical = True,
		)
		
		self.w.button_cancel = vanilla.Button(
			(-272, -30, -204, -10),
			"Cancel",
			callback=self.callback_cancel,
		)
		self.w.button_delete = vanilla.Button(
			(-196, -30, -92, -10),
			"Remove Grid",
			callback=self.callback_delete,
		)
		self.w.button_set = vanilla.Button(
			(-84, -30, -8, -10),
			"Set Grid",
			callback=self.callback_set,
		)
		self.update()
		self.w.open()
		self.w.makeKey()
	
	
	def update(self):
		self.master = CurrentMaster()
		if self.master is None:
			self.w.master_name.set("Set local grid for master: None")
			self.w.x.set("0")
			self.w.y.set("0")
			
			self.w.x.enable(False)
			self.w.y.enable(False)
			self.w.grid_type.enable(False)
			self.w.button_delete.enable(False)
			self.w.button_set.enable(False)
		else:
			self.w.master_name.set("Set local grid for master: %s" % self.master.name)
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
		
	
	def callback_cancel(self, info):
		self.w.close()
	
	
	def callback_delete(self, info):
		deleteGrid(self.master)
		self.w.close()
	
	
	def callback_set(self, info):
		gx = self.w.x.get()
		gy = self.w.y.get()
		grid_type = self.w.grid_type.get()
		if grid_type == 0:
			grid_type = "units"
		else:
			grid_type = "div"
		try:
			gxi = int(gx)
			gyi = int(gy)
			gxf = float(gx)
			gyf = float(gy)
		except ValueError:
			print "Please enter a floating point number or an integer number."
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




class MasterGrid(ReporterPlugin):

	def settings(self):
		self.menuName = Glyphs.localize({'en': u'Master Grid', 'de': u'Master-Raster'})


	def start(self):
		if can_display_ui:
			mainMenu = NSApplication.sharedApplication().mainMenu()
			s = objc.selector(self.editMasterGrid,signature='v@:')
			newMenuItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
				Glyphs.localize({
					'en': u"Master Grid…",
					'de': u'Master-Raster…'
				}),
				s,
				""
			)
			newMenuItem.setTarget_(self)
			submenu = mainMenu.itemAtIndex_(2).submenu()
			submenu.insertItem_atIndex_(newMenuItem, submenu.numberOfItems())

		
	def background(self, layer):

		# Check if the grid should be drawn
		
		currentController = self.controller.view().window().windowController()
		if currentController:
			tool = currentController.toolDrawDelegate()
			if tool.isKindOfClass_(NSClassFromString("GlyphsToolText")) or tool.isKindOfClass_(NSClassFromString("GlyphsToolHand")):
				return
		
		master = layer.parent.parent.masters[layer.layerId]
		if master is None:
			return

		gx, gy, grid_type = getGrid(master)
		if gx == 0 or gy == 0:
			return

		if grid_type == "div":
			upm = layer.parent.parent.upm
			gx = upm / gx
			gy = upm / gy

		NSColor.lightGrayColor().set()
		NSBezierPath.setDefaultLineWidth_(0.6/self.getScale())

		max_x = int(layer.width // gx + 2) * gx
		min_y = int(master.descender // gy) * gy
		max_y = int(master.ascender // gy + 1) * gy
		
		for x in range(-gx, max_x + gx, gx):
			NSBezierPath.strokeLineFromPoint_toPoint_(
				NSPoint(x, min_y),
				NSPoint(x, max_y)
			)
		
		for y in range(min_y, max_y + gy, gy):
			NSBezierPath.strokeLineFromPoint_toPoint_(
				NSPoint(-gx, y),
				NSPoint(max_x, y)
			)

		#NSBezierPath.setDefaultLineWidth_(1.0/self.getScale())
		s = int(round(12.0 / self.getScale()))
		s2 = s * 0.25
		sel = int(round(13.0 / self.getScale()))

		for p in layer.paths:
			for n in p.nodes:
				if n.type != OFFCURVE:
					x = n.position.x
					y = n.position.y
					if n.selected:
						s1 = sel
					else:
						s1 = s
					if x!= 0 and abs(x % gx) < 1:
						NSBezierPath.strokeLineFromPoint_toPoint_(
							NSPoint(x - s2, y - s1),
							NSPoint(x - s2, y + s1)
						)
						NSBezierPath.strokeLineFromPoint_toPoint_(
							NSPoint(x + s2, y - s1),
							NSPoint(x + s2, y + s1)
						)
					if y != 0 and abs(y % gy) < 1:
						NSBezierPath.strokeLineFromPoint_toPoint_(
							NSPoint(x - s1, y - s2),
							NSPoint(x + s1, y - s2)
						)
						NSBezierPath.strokeLineFromPoint_toPoint_(
							NSPoint(x - s1, y + s2),
							NSPoint(x + s1, y + s2)
						)


	def editMasterGrid(self):
		GridDialog()

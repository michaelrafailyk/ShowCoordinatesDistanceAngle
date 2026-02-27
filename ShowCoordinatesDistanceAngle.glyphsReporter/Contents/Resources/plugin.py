# encoding: utf-8
from __future__ import division
import objc
from GlyphsApp import Glyphs, GSNode, OFFCURVE, addPoints, distance
from GlyphsApp.plugins import ReporterPlugin, NSCommandKeyMask, NSPoint, NSColor, NSAffineTransform
from math import degrees, atan2
from AppKit import NSGraphicsContext

class ShowCoordinatesDistanceAngle(ReporterPlugin):
	
	@objc.python_method
	def settings(self):
		self.menuName = 'Coordinates Distance Angle'
		# shortcut: ⌘L
		self.keyboardShortcut = 'l'
		self.keyboardShortcutModifier = NSCommandKeyMask
	
	@objc.python_method
	def angle(self, a, b):
		# "degree" is the real angle which is angled at 90 degrees to fit the label along the line
		# "label" is the angle divided by 4 to always show 0 to 90 degrees, which is handy for italics
		degree = degrees(atan2(b.y - a.y, b.x - a.x))
		label = -degree - 90
		if label < -90: label += 180
		if label == -90: label = 90
		if degree <= -90: degree += 180
		elif degree > 90: degree -= 180
		return {'degree': degree, 'label': label}
	
	@objc.python_method
	def pointOnSegment(self, p, a, b, tolerance=0.01):
		# check collinearity using cross product
		cross = (p.y - a.y) * (b.x - a.x) - (p.x - a.x) * (b.y - a.y)
		if abs(cross) > tolerance:
			return False
		# check bounding box
		dot = (p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)
		if dot < 0:
			return False
		squaredLength = (b.x - a.x)**2 + (b.y - a.y)**2
		if dot > squaredLength:
			return False
		return True
	
	@objc.python_method
	def foreground(self, layer):
		# light mode colors
		black = NSColor.textColor().colorWithAlphaComponent_(0.7)
		blue = NSColor.colorWithString_('#345EA4')
		green = NSColor.colorWithString_('#1E7D41')
		# dark mode colors
		if self.controller.graphicView().drawDark():
			black = NSColor.textColor().colorWithAlphaComponent_(0.9)
			blue = NSColor.colorWithString_('#80BFFF')
			green = NSColor.colorWithString_('#4FE084')
		scale = self.getScale()
		offset = 3 / scale
		shift = 1 / scale
		# positioning correction at high zoom (before the grid mode)
		if scale > 6:
			offset = 8 / scale
			shift = 6 / scale
		toolSelect = Glyphs.font.tool == 'SelectTool'
		toolPen = Glyphs.font.tool == 'DrawTool'
		toolTempPreview = Glyphs.font.parent.windowController().toolTempSelection() != None
		selection = layer.selection
		nodeLast = {'x': 0, 'y': 0}
		# intersections
		intersections = []
		inter = layer.intersections()
		for i in range(inter.count()):
			intersections.append(inter.pointAtIndex_(i))
		# display labels if selected 12 or less nodes
		# display labels only when Select or Draw tools are active, and not during quick preview (Space key)
		# display labels if the the glyph is not too small and if the grid is not displayed
		if selection and len(selection) < 13 and (toolSelect or toolPen) and not toolTempPreview and scale > 0.2 and scale < 8:
			for path in layer.paths:
				nodes = path.nodes
				nodesCount = len(nodes)
				for i in range(nodesCount):
					nodePrev = nodes[(i-1) % nodesCount]
					node = nodes[i]
					nodeNext = nodes[(i+1) % nodesCount]
					
					# show node coordinates
					if node in selection:
						# show labels only when just one or two nodes selected
						# do not show (duplicate) node coordinates if it is located in the same position as the previous one (like a handles can)
						notDuplicate = node.x != nodeLast['x'] or node.y != nodeLast['y']
						if len(selection) <= 2 and type(node) is GSNode and notDuplicate:
							# show labels only if two nodes are not too close horizontally
							nodesNotTooClose = True
							if nodePrev in selection and node.y == nodePrev.y:
								distanceBetweenNodes = node.x - nodePrev.x if node.x > nodePrev.x else nodePrev.x - node.x
								nodesNotTooClose = distanceBetweenNodes * scale > 45
							elif nodeNext in selection and node.y == nodeNext.y:
								distanceBetweenNodes = node.x - nodeNext.x if node.x > nodeNext.x else nodeNext.x - node.x
								nodesNotTooClose = distanceBetweenNodes * scale > 45
							if nodesNotTooClose:
								nodeX = node.x
								nodeY = node.y
								# save last node coordinates to compare it with the next node coordinates
								nodeLast['x'] = nodeX
								nodeLast['y'] = nodeY
								# find previous and next oncurve nodes to analyze the vertical path segment direction (ignore the handles)
								nodePrevOncurve = nodePrev
								nodeNextOncurve = nodeNext
								if nodePrevOncurve.type == OFFCURVE: nodePrevOncurve = nodes[(i-2) % nodesCount]
								if nodePrevOncurve.type == OFFCURVE: nodePrevOncurve = nodes[(i-3) % nodesCount]
								if nodeNextOncurve.type == OFFCURVE: nodeNextOncurve = nodes[(i+2) % nodesCount]
								if nodeNextOncurve.type == OFFCURVE: nodeNextOncurve = nodes[(i+3) % nodesCount]
								# move label below the node if the path segment moves up but not orthogonal
								prevUp = nodePrevOncurve.y > nodeY and nodePrevOncurve.x != nodeX
								nextUp = nodeNextOncurve.y > nodeY and nodeNextOncurve.x != nodeX
								prevSame = nodePrevOncurve.y == nodeY
								nextSame = nodeNextOncurve.y == nodeY
								y = nodeY + offset
								alignRight = 'bottomright'
								alignLeft = 'bottomleft'
								if (prevUp and nextUp) or (prevUp and nextSame) or (nextUp and prevSame):
									y = nodeY - offset
									if Glyphs.versionNumber < 3.2:
										# a hack for Glyphs 3.1 that incorrectly displays topleft positioning
										y = y - 12 / scale - 1.4
									else:
										alignRight = 'topright'
										alignLeft = 'topleft'
								positionLeft = NSPoint(nodeX - offset + shift, y)
								positionRight = NSPoint(nodeX + offset - shift, y)
								textLeft = str(nodeX).replace('.0', '')
								textRight = str(nodeY).replace('.0', '')
								# show x coordinate left of center
								self.drawTextAtPoint(textLeft, positionLeft, fontColor = black, align = alignRight)
								# show y coordinate right of center
								self.drawTextAtPoint(textRight, positionRight, fontColor = black, align = alignLeft)
					
					# show distance and angle
					betweenHandles = nodePrev.type == OFFCURVE and node.type == OFFCURVE
					betweenOpenPath = not path.closed and i == 0
					# do not display labels between the handles, as well as between the last and first node of an open path
					if (nodePrev in selection or node in selection) and not betweenHandles and not betweenOpenPath:
						pointOne = nodePrev.position
						pointTwo = node.position
						# add intersections (if present) into segment
						splitPoints = [pointOne]
						for p in intersections:
							if self.pointOnSegment(p, pointOne, pointTwo):
								if distance((p.x, p.y), (pointOne.x, pointOne.y)) < 0.01:
									continue
								if distance((p.x, p.y), (pointTwo.x, pointTwo.y)) < 0.01:
									continue
								splitPoints.append(p)
						splitPoints.append(pointTwo)
						splitPoints.sort(key=lambda pt: (pt.x - pointOne.x)**2 + (pt.y - pointOne.y)**2)
						for j in range(len(splitPoints)-1):
							posOne = splitPoints[j]
							posTwo = splitPoints[j+1]
							posMid = addPoints(posOne, posTwo)
							position = NSPoint(posMid.x * 0.5, posMid.y * 0.5)
							distanceValue = distance((posOne.x, posOne.y), (posTwo.x, posTwo.y))
							distanceTreshold = distanceValue * scale > 50
							if len(selection) > 2:
								distanceTreshold = distanceValue * scale > 30
							angle = self.angle(posOne, posTwo)
							distanceLabel = ('%.0f' % (distanceValue)).replace('.0', '')
							angleLabel = ('%.1f' % (angle['label'])).replace('.0', '')
							# rotate context if the segment is not horizontal
							if (angleLabel != '90'):
								NSGraphicsContext.saveGraphicsState()
								transform = NSAffineTransform.new()
								transform.translateXBy_yBy_(position.x, position.y)
								transform.rotateByDegrees_(angle['degree'])
								transform.translateXBy_yBy_(-position.x, -position.y)
								transform.concat()
							# show distance
							if distanceTreshold:
								self.drawTextAtPoint(distanceLabel, (position.x, position.y + offset), fontColor = blue, align = 'bottomcenter')
							# show angle
							if angleLabel != '0' and angleLabel != '90' and distanceTreshold:
								self.drawTextAtPoint(angleLabel + '°', (position.x, position.y - offset), fontColor = green, align = 'topcenter')
							# restore context if rotated
							if (angleLabel != '90'):
								NSGraphicsContext.restoreGraphicsState()
	
	@objc.python_method
	def __file__(self):
		return __file__

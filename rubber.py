from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

class RectangleMapTool(QgsMapToolEmitPoint):
  
  onExtentChanged = pyqtSignal(QgsRectangle)
  
  def __init__(self, canvas):
    self.canvas = canvas
    QgsMapToolEmitPoint.__init__(self, self.canvas)
    self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
    self.rubberBand.setColor(Qt.red)
    self.rubberBand.setWidth(1)
    self.reset()

  def reset(self):
      self.startPoint = self.endPoint = None
      self.isEmittingPoint = False
      self.rubberBand.reset(True)

  def canvasPressEvent(self, e):
      self.startPoint = self.toMapCoordinates(e.pos())
      self.endPoint = self.startPoint
      self.isEmittingPoint = True
      self.showRect(self.startPoint, self.endPoint)

  def canvasReleaseEvent(self, e):
      self.isEmittingPoint = False
      r = self.rectangle()
      if r is not None:
        print("Rectangle:", r.xMinimum(), r.yMinimum(), r.xMaximum(), r.yMaximum())
        self.onExtentChanged.emit(r)

  def canvasMoveEvent(self, e):
      if not self.isEmittingPoint:
        return

      self.endPoint = self.toMapCoordinates(e.pos())
      self.showRect(self.startPoint, self.endPoint)
  
  def hideRect(self):
    self.reset()
    self.rubberBand.reset(QgsWkbTypes.LineGeometry)

  def showRect(self, startPoint, endPoint):
      self.rubberBand.reset(QgsWkbTypes.LineGeometry)
      if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
        return

      point1 = QgsPointXY(startPoint.x(), startPoint.y())
      point2 = QgsPointXY(startPoint.x(), endPoint.y())
      point3 = QgsPointXY(endPoint.x(), endPoint.y())
      point4 = QgsPointXY(endPoint.x(), startPoint.y())
      point5 = QgsPointXY(startPoint.x(), startPoint.y())

      self.rubberBand.addPoint(point1, False)
      self.rubberBand.addPoint(point2, False)
      self.rubberBand.addPoint(point3, False)
      self.rubberBand.addPoint(point4, False)
      self.rubberBand.addPoint(point5, True)    # true to update canvas
      self.rubberBand.show()

  def rectangle(self):
      if self.startPoint is None or self.endPoint is None:
        return None
      elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
        return None

      sourceCrs = self.canvas.mapSettings().destinationCrs()
      destCrs = QgsCoordinateReferenceSystem(4326)
      tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())

      p1 = QgsGeometry.fromPointXY(self.startPoint)
      p1.transform(tr)
      p2 = QgsGeometry.fromPointXY(self.endPoint)
      p2.transform(tr)

      return QgsRectangle(p1.asPoint(), p2.asPoint())

  def deactivate(self):
    # Do whatever you want here
    QgsMapTool.deactivate(self)

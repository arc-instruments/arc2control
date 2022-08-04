import copy
import sys
import numpy as np
import itertools
import math
from PyQt6 import QtCore, QtWidgets, QtGui
from collections import namedtuple
from functools import partial


GRIDPEN = QtGui.QPen(QtGui.QBrush(QtCore.Qt.GlobalColor.lightGray), 1.0)
TEXTPEN = QtGui.QPen(QtGui.QBrush(QtCore.Qt.GlobalColor.black), 1.0)
SELPEN = QtGui.QPen(QtGui.QBrush(QtCore.Qt.GlobalColor.black), 2.0,
    cap=QtCore.Qt.PenCapStyle.FlatCap, join=QtCore.Qt.PenJoinStyle.MiterJoin)
SECSELPEN = QtGui.QPen(QtGui.QBrush(QtCore.Qt.GlobalColor.blue), 3.0,
    cap=QtCore.Qt.PenCapStyle.FlatCap, join=QtCore.Qt.PenJoinStyle.MiterJoin)
RANPEN = QtGui.QPen(QtGui.QBrush(QtCore.Qt.GlobalColor.red), 3.0,
    cap=QtCore.Qt.PenCapStyle.FlatCap, join=QtCore.Qt.PenJoinStyle.MiterJoin)

DX = lambda x: max(int(round(-0.769*x+36.6)), 12)
DY = lambda x: max(int(round(-0.769*x+36.6)), 12)

CBPADX = lambda x: max(int(round(-0.385*x+37.3)), 25)
CBPADY = lambda x: max(int(round(-0.385*x+37.3)), 25)

GRAD = []

MIN_RES = 100
MAX_RES = 1000000000


def _rainbow(x=0):
    # clip values between 0 and 256
    if x > 255:
        x = 255
    elif x < 0:
        x = 0

    r = np.abs(2.0 * x/255.0 - 0.5)
    g = np.sin(x/255.0 * np.pi)
    b = np.cos(x/255.0 * np.pi/2)

    return (
        1.0 if r > 1.0 else r,
        1.0 if g > 1.0 else g,
        1.0 if b > 1.0 else b)

for i in range(256):
    color = QtGui.QColor()
    (r, g, b) = _rainbow(i)
    color.setRgbF(r, g, b, 1.0)
    GRAD.insert(0, color)


Cell = namedtuple('Cell', ['w', 'b'])


def _clip(value, low, high, inclusive=False):
    if value < 0:
        return low
    if inclusive and value > high:
        return high
    if (not inclusive) and value >= high:
        return high-1
    return value


class CachedBackground:

    def __init__(self, data, bits, words, mask):
        self._data = data
        self._bits = bits
        self._words = words
        self._cbpad = min(CBPADX(self._words), CBPADY(self._bits))
        self._dd = min(DX(self._words), DY(self._bits))
        self._mask = mask
        self._pixmap = self.makePixmap()

    @property
    def words(self):
        return self._words

    @property
    def bits(self):
        return self._bits

    @property
    def pixmap(self):
        return self._pixmap

    def makePixmap(self):
        CBPAD = self._cbpad
        DD = self._dd

        pxm = QtGui.QPixmap(self._words*DD+1+2*CBPAD, self._bits*DD+1+2*CBPAD)
        pxm.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pxm)
        painter.translate(QtCore.QPoint(CBPAD, CBPAD))
        painter.setPen(GRIDPEN)
        for row in range(self._bits):
            for col in range(self._words):
                if self._mask is not None and self._mask[row][col] == 0:
                    continue
                val = self._data[row][col]
                if (val is not np.nan) and (val < np.iinfo(np.int32).max):
                    #idx = int(val*7.9)
                    #painter.fillRect(col*DX,row*DY,DX,DY, GRAD[idx])
                    minR = np.log10(MIN_RES)
                    normR = np.log10(MAX_RES) - minR

                    try:
                        idx = int((np.log10(val) - minR)*255/normR)
                    except (OverflowError, ValueError):
                        idx = -1
                    if idx < 256 and idx >= 0:
                        painter.fillRect(col*DD, row*DD, DD, DD, GRAD[idx])
                    else:
                        painter.fillRect(col*DD, row*DD, DD, DD, GRAD[-1])
                else: ##### here
                    painter.fillRect(col*DD, row*DD, DD, DD, QtCore.Qt.GlobalColor.white)
                painter.drawRect(QtCore.QRect(col*DD, row*DD, DD, DD))

        font = painter.font()
        font.setPointSize(8);
        painter.setFont(font)
        painter.setPen(TEXTPEN)
        for row in range(self._bits):
            painter.drawText(-CBPAD, int((row+1-0.25)*DD), '%02d' % (row+1))

        for col in range(self._words):
            painter.save()
            painter.translate(int((col+0.2)*DD), (self._bits+0.7)*DD)
            painter.rotate(90)
            #painter.drawText(int((col+0.2)*DX(self._words)), (self._words+1)*DY, '%02d' % (col+1))
            painter.drawText(0, 0, '%02d' % (col+1))
            painter.restore()

        return pxm

    def refreshPixmap(self):
        self._pixmap = self.makePixmap()

    def blitPixmap(self, indices):
        CBPAD = self._cbpad
        DD = self._dd

        pxm = QtGui.QPixmap(self._words*DD+1+2*CBPAD, self._bits*DD+1+2*CBPAD)
        pxm.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pxm)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.translate(QtCore.QPoint(CBPAD, CBPAD))
        painter.setPen(GRIDPEN)
        for coord in indices:
            (row, col) = (coord[0], coord[1])
            if self._mask is not None and self._mask[row][col] == 0:
                continue
            val = self._data[row][col]
            if (val is not np.nan) and (val > 0.0) and (val < np.iinfo(np.int32).max):
                # idx = int(val*7.9)
                minR = np.log10(MIN_RES)
                normR = np.log10(MAX_RES) - minR

                idx = int((np.log10(val) - minR)*255/normR)
                if idx < 256 and idx >= 0:
                    painter.fillRect(col*DD,row*DD, DD, DD, GRAD[idx])
                else:
                    painter.fillRect(col*DD, row*DD, DD, DD, GRAD[-1])
            else:
                painter.fillRect(col*DD, row*DD, DD, DD, QtCore.Qt.GlobalColor.white)
            painter.drawRect(QtCore.QRect(col*DD, row*DD, DD, DD))

        return pxm

    # def update(self, data):

    #     unchanged = (self._data == data)

    #     if unchanged.all():
    #         return
    #     else:
    #         diffs = np.where(unchanged == False)
    #         self._data = np.copy(data)
    #         self._pixmap = self.blitPixmap(zip(*diffs))

    def update(self, xs, ys, vals):

        self._pixmap = self.blitPixmap(zip(xs, ys, vals))


class PaintWidget(QtWidgets.QWidget):

    mousePositionChanged = QtCore.pyqtSignal(Cell)
    selectionChanged = QtCore.pyqtSignal(set)

    def __init__(self, shape=(32, 32), mask=None, parent=None):
        super().__init__(parent)
        self.selection = set()
        self.secselection = set()
        self.events = True
        if self.events:
            self.setMouseTracking(True)
        self.mousePosition = (-1, -1)
        self.mouseDragging = False
        self.rangeStart = None
        self.rangeEnd = None

        self._bits = shape[0]
        self._words = shape[1]
        self._data = np.zeros(shape=(self._bits, self._words))
        self._data[:] = np.nan
        self._cbpad = min(CBPADX(self._words), CBPADY(self._bits))
        self._dd = min(DX(self._words), DY(self._bits))
        self._mask = mask

        self.setMinimumSize(self._dd*self._words+2*self._cbpad, self._dd*self._bits+2*self._cbpad)
        self.setMaximumSize(self._dd*self._words+2*self._cbpad, self._dd*self._bits+2*self._cbpad)
        self.background = CachedBackground(self._data, self._bits, self._words, mask)

    def paintEvent(self, evt):
        painter = QtGui.QPainter(self)
        self.paint(painter)

    def setEnableEvents(self, enable):
        self.events = enable
        self.setMouseTracking(self.events)

    def setSize(self, words, bits):
        self._words = words
        self._bits = bits
        self._data = np.zeros(shape=(self._bits, self._words))
        self._data[:] = np.nan
        self.setMinimumSize(DD*self._words+2*CBPAD, DD*self._bits+2*CBPAD)
        self.setMaximumSize(DD*self._words+2*CBPAD, DD*self._bits+2*CBPAD)
        self.background = CachedBackground(self._data, self._bits, self._words, self._mask)
        self.repaint()

    def setMask(self, mask):
        self._mask = mask
        self.background = CachedBackground(self._data, self._bits, self._words, self._mask)
        self.repaint()

    @property
    def size(self):
        return self._data.shape

    @property
    def data(self):
        return self._data

    def paint(self, painter):
        CBPAD = self._cbpad
        DD = self._dd

        painter.save()
        painter.setPen(GRIDPEN)
        # for row in range(WORDS):
        #     for col in range(BITS):
        #         val = DATA[col][row]
        #         if (val is not np.nan) and (val < np.iinfo(np.int32).max):
        #             idx = int(val*7.9)
        #             painter.fillRect(col*DX,row*DY,DX,DY, GRAD[idx])
        #         else:
        #             painter.fillRect(col*DX,row*DY,DX,DY, QtCore.Qt.white)
        #         painter.drawRect(QtCore.QRect(col*DX, row*DY, DX, DY))
        # self.background.update(DATA)
        painter.drawPixmap(0, 0, self.background.pixmap)

        painter.translate(QtCore.QPoint(CBPAD, CBPAD))

        for cell in self.secselection - self.selection:
            if cell.b < 0 or cell.w < 0:
                continue
            if self._mask is not None and self._mask[cell.b][cell.w] == 0:
                continue

            painter.setPen(SECSELPEN)
            painter.drawRect(QtCore.QRect(cell.w*DD, cell.b*DD, DD, DD))

        for cell in self.selection:
            if cell.b < 0 or cell.w < 0:
                continue
            if self._mask is not None and self._mask[cell.b][cell.w] == 0:
                continue
            painter.setPen(SELPEN)
            painter.drawRect(QtCore.QRect(cell.w*DD+1, cell.b*DD+1, DD-1, DD-1))

        if (self.rangeStart is not None) and (self.rangeEnd is not None):

            painter.setPen(RANPEN)
            (w0, b0) = self.__coordsToCell(self.rangeStart.x(), self.rangeStart.y())
            (wf, bf) = self.__coordsToCell(self.rangeEnd.x(), self.rangeEnd.y())
            minw = min(w0, wf)
            maxw = max(w0, wf)+1
            minb = min(b0, bf)
            maxb = max(b0, bf)+1

            painter.drawRect(QtCore.QRect(QtCore.QPoint(minw*DD, minb*DD),
                QtCore.QPoint(maxw*DD, maxb*DD)))

        # font = painter.font()
        # font.setPointSize(8);
        # painter.setFont(font)
        # painter.setPen(TEXTPEN)
        # for row in range(WORDS):
        #     painter.drawText(-CBPADX, int((row+1-0.25)*DY), '%02d' % (row+1))

        # for col in range(BITS):
        #     painter.drawText(int((col+0.2)*DX), (WORDS+1)*DY, '%02d' % (col+1))
        painter.restore()

    def updateData(self, y, x, val):
        if self._data[x][y] != val:
            self._data[x][y] = val
            self.background.update([x], [y], [val])
            self.repaint()

    def setData(self, data):
        self._data[:] = data
        self.background.refreshPixmap()
        self.repaint()

    # def updateRow(self, rowidx, data, colidx=None):
    #     if colidx is None:
    #         self._data[rowidx][:] = data
    #     else:
    #         self._data[colidx,rowidx] = data[colidx]

    #     self.background.refreshPixmap()
    #     self.repaint()

    def selectAll(self):
        for w in range(self._words):
            for b in range(self._bits):
                if self._mask is not None and self._mask[b][w] == 0:
                    continue
                self.selection.add(Cell(w, b))
        self.selectionChanged.emit(self.selection)
        self.repaint()

    def secselect(self, cells):
        new = set(cells)
        if new != self.secselection:
            self.secselection = new
            self.repaint()

    def mouseDoubleClickEvent(self, evt):
        if not self.events:
            return

        CBPAD = self._cbpad
        DD = self._dd
        self.mouseDragging = False

        if evt.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        (x, y) = (evt.position().x(), evt.position().y())
        if x >= DD*self._words+CBPAD or y >= DD*self._bits+CBPAD:
            return
        if x < CBPAD+1 or y < CBPAD+1:
            return
        (w, b) = (int((x-CBPAD)/DD), int((y-CBPAD)/DD))

        if self._mask is not None and self._mask[b][w] == 0:
            return

        cells = set([Cell(w, b)])

        # if ctrl is NOT held down clear the selection
        if not (QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.selection.clear()

        if (self.selection | cells) == self.selection:
            return
        else:
            self.selection.update(cells)
            self.selectionChanged.emit(self.selection)

        self.repaint()

    def mousePressEvent(self, evt):
        if not self.events:
            return

        if evt.button() == QtCore.Qt.MouseButton.RightButton:
            self.selection.clear()
            self.rangeStart = None
            self.rangeEnd = None
            self.selectionChanged.emit(self.selection)
            self.repaint()
            return

        CBPAD = self._cbpad
        DD = self._dd

        self.mouseDragging = True
        #(stepsX, stepsY) = (round((evt.x()+CBPADX)/DX), round((evt.y()+CBPADY)/DY))
        (stepsX, stepsY) = (math.floor((evt.position().x()-CBPAD)/DD),
            math.floor((evt.position().y()-CBPAD)/DD))
        stepsX = _clip(stepsX, low=0, high=self._words)
        stepsY = _clip(stepsY, low=0, high=self._bits)
        self.rangeStart = QtCore.QPoint(stepsX*DD+CBPAD, stepsY*DD+CBPAD)
        self.rangeEnd = None
        self.repaint()

    def mouseReleaseEvent(self, evt):

        if not self.events:
            return

        emit = False
        CBPAD = self._cbpad
        DD = self._dd

        if self.mouseDragging:
            self.mouseDragging = False
            (stepsX, stepsY) = (int((evt.position().x()-CBPAD)/DD), int((evt.position().y()-CBPAD)/DD))
            stepsX = _clip(stepsX, low=0, high=self._words)
            stepsY = _clip(stepsY, low=0, high=self._bits)
            #self.rangeEnd = QtCore.QPoint(stepsX*DX, stepsY*DY)
            append = (QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
            selection = self.__cellsInSelection()
            self.rangeStart = None
            self.rangeEnd = None

            # emit a signal only if new selection is different than current
            if (selection | self.selection) != self.selection:
                emit = True
            else:
                return

            if not append:
                self.selection = selection
            else:
                self.selection.update(selection)

            if emit:
                self.selectionChanged.emit(self.selection)

            self.repaint()

    def mouseMoveEvent(self, evt):

        if not self.events:
            return

        CBPAD = self._cbpad
        DD = self._dd

        # if not a click-and-drag operation is underway just report
        # the current mouse position to the listeners
        if not self.mouseDragging:
            (x, y) = (evt.position().x(), evt.position().y())
            if x >= DD*self._words+(CBPAD) or y >= DD*self._bits+(CBPAD):
                newPos = (-1, -1)
            elif x < (CBPAD+1) or y < (CBPAD+1):
                newPos = (-1, -1)
            else:
                newPos = (int((x-CBPAD)/DD), int((y-CBPAD)/DD))

            # only emit the event if the mouse moved to a different
            # cell than the one it's currently on
            if newPos != self.mousePosition:
                self.mousePosition = newPos
                cell = Cell(*newPos)
                if self._mask is not None and self._mask[cell.b][cell.w] == 0:
                    cell = Cell(-1, -1)
                self.mousePositionChanged.emit(cell)

        else:
            # this is a click-and-drag operation but check first
            # if the mouse has set a start position first!
            if self.rangeStart is None:
                return

            # endpoint is the current mouse position
            endPoint = QtCore.QPoint(int(evt.position().x()), int(evt.position().y()))
            startPoint = self.rangeStart

            dx = abs(startPoint.x() - endPoint.x())
            # if selection lies outside the first cell
            # and not within its X boundaries adjust the
            # offset required before selecting the cell
            # |   |
            # |   |
            # |   |
            # |   |
            # +---+
            # | C |  <- starting cell
            # +---+
            # |   |
            # |   |
            # |   |
            # |   |
            #   ^
            #   |
            #   +--- mouse is OUTSIDE these boundaries
            if dx >= DX(self._words):
                # if the end point is "left"er than the
                # original point then snap to the rightmost
                # cell
                if startPoint.x() <= endPoint.x():
                    funcx = math.floor
                    stepxoffset = -1
                    pxxoffset = int(DX(self._words)/2)
                # else snap to the leftmost cell
                else:
                    funcx = math.ceil
                    stepxoffset = 0
                    pxxoffset = -int(DX(self._words)/2)
            # otherwise the mouse is still within the original
            # cell; just select the cell without offset
            else:
                funcx = math.floor
                stepxoffset = 0
                pxxoffset = 0

            # same for the Y axis; if we're still within
            # the extended boundaries of the original cell
            # -----------+---+----------
            #            | C |            <-----+
            # -----------+---+----------        |
            #                                   |
            #              the mouse is OUTSIDE these boundaries
            #
            dy = abs(startPoint.y() - endPoint.y())
            if dy >= DD:
                if startPoint.y() <= endPoint.y():
                    funcy = math.floor
                    stepyoffset = -1
                    pxyoffset = int(DD/2)
                else:
                    funcy = math.ceil
                    stepyoffset = 0
                    pxyoffset = -int(DD/2)
            else:
                funcy = math.floor
                stepyoffset = 0
                pxyoffset = 0

            # calculate how many steps (cells) the mouse has moved
            (stepsX, stepsY) = (funcx((evt.position().x()-CBPAD+pxxoffset)/DD) + stepxoffset,
                funcy((evt.position().y()-CBPAD+pxyoffset)/DD) + stepyoffset)
            # and clip them between 0 and BITS or WORDS
            stepsX = _clip(stepsX, low=0, high=self._words)
            stepsY = _clip(stepsY, low=0, high=self._bits)
            # then convert that into absolute coordinates plus the padding
            self.rangeEnd = QtCore.QPoint(stepsX*DD+CBPAD, stepsY*DD+CBPAD)
            self.repaint()

    def __cellsInSelection(self):

        if self.rangeEnd is None:
            return set()

        selectedCells = self.selection

        (w0, b0) = self.__coordsToCell(self.rangeStart.x(), self.rangeStart.y())
        (wf, bf) = self.__coordsToCell(self.rangeEnd.x(), self.rangeEnd.y())

        minw = min((w0, wf))
        maxw = max((w0, wf))+1
        minb = min((b0, bf))
        maxb = max((b0, bf))+1

        if self._mask is None:
            cells = set([Cell(w, b) for (w, b)
                in itertools.product(range(minw, maxw), range(minb, maxb))])
        else:
            cells = set([Cell(w, b) for (w, b)
                in itertools.product(range(minw, maxw), range(minb, maxb))
                    if self._mask[b][w] == 1])

        return cells

    def __coordsToCell(self, x, y):
        CBPAD = self._cbpad
        DD = self._dd
        (w, b) = (int((x-CBPAD)/DD), int((y-CBPAD)/DD))
        return (w, b)

    @property
    def selectedCells(self):
        return sorted(self.selection)

    @property
    def allCells(self):
        w = np.where(self._mask == 1)
        return sorted(set(Cell(w, b) for (w, b) in zip(w[0], w[1])))

    def valueOf(self, selection):
        (b, w) = (selection.b, selection.w)
        return self._data[b][w]


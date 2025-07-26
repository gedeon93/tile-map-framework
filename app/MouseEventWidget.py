from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt as Qt
from PyQt5.QtCore import QEvent, QPoint

class MouseEventWidget(QWidget):
    clickedZoomIn = pyqtSignal()
    clickedZoomOut = pyqtSignal()

    def __init__(self, parent=None):
        super(MouseEventWidget, self).__init__(parent=parent)
        self.clickPos: QPoint = None
    
    def mousePressEvent(self, event: QEvent) -> None:
        """
        Method for handling mouse input events (click, scroll, etc.).

        Args:
            event (QEvent): recognized input event from the mouse input modality.

        Returns:
            None.
        """
        if event.pos() in self.rect():
            if event.button() == Qt.LeftButton:
                self.clickPos = event.pos()
                self.clickedZoomIn.emit()
            elif event.button() == Qt.RightButton:
                self.clickPos = event.pos()
                self.clickedZoomOut.emit()

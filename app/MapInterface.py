import numpy as np
from typing import Tuple
from pathlib import Path
from win32api import GetMonitorInfo, MonitorFromPoint
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtWidgets import QPushButton, QWidget, QSizePolicy
from PyQt5.QtCore import Qt as Qt
from PyQt5.QtCore import QRect, QSize

from app.MapView import MapView
from app.MouseEventWidget import MouseEventWidget

class MapInterface(QMainWindow):
    def __init__(self, window_width_px: int = None, window_height_px: int = None, 
                 storage_path: str = None, update_interval: int = 1000):
        super(MapInterface, self).__init__(parent=None)
        self.update_interval: int = update_interval
        self.storage_path: str = storage_path
        self.tile_dimensions: np.array = np.array([256, 256])
        self.control_panel_height: int = 80
        self.max_tile_width: int = 8
        self.max_tile_height: int = 8

        self.app_width, self.app_height = self.compute_interface_size(window_width_px= window_width_px, window_height_px= window_height_px)

        self.setGeometry(0, 0, self.app_width, self.app_height)
        self.setFocusPolicy(Qt.StrongFocus)

        self.img_buffer_width: int = self.app_width
        self.img_buffer_height: int = self.app_height - self.control_panel_height
        """
        number_tiles_wide = self.img_buffer_width / self.tile_dimensions[0]
        number_tiles_high = self.img_buffer_height / self.tile_dimensions[1]
        print(self.app_width, self.app_height)
        print(number_tiles_wide, number_tiles_high)
        """
        
        if not self.storage_path:
            root_path = Path(__file__).resolve().parents[1]
            self.storage_path = root_path / "resources" / "images"

        self.map_view = MapView(self.img_buffer_width, self.img_buffer_height, self.tile_dimensions[0], self.tile_dimensions[1],
                                thread_count= 4, update_interval= self.update_interval)
        central_layout = self.create_central_layout()
        self.configure_map_view(central_layout)
        self.configure_control_panel(central_layout)
        self.map_view.set_active_state(True)
                
    def create_central_layout(self) -> QVBoxLayout:
        central_widget = QWidget()    
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        return layout
    
    def configure_map_view(self, layout: QVBoxLayout) -> None:
        widget = MouseEventWidget()
        widget.clickedZoomIn.connect(lambda: self.map_view.click_zoom(widget.clickPos, True))
        widget.clickedZoomOut.connect(lambda: self.map_view.click_zoom(widget.clickPos, False))
        map_layout = QVBoxLayout()
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.addWidget(self.map_view.map_view_frame)
        widget.setLayout(map_layout)
        layout.addWidget(widget)

    def configure_control_panel(self, layout: QVBoxLayout) -> None:
        """
        Method for configuring and rendering the bottom control panel of the interface window.
        """
        controlPanel = QHBoxLayout()
        controlPanel.setContentsMargins(0, 0, 0, 0)
        
        self._create_button_section(controlPanel, width = 150, height = self.control_panel_height)
        self._create_category_section(controlPanel, width = 70, height = self.control_panel_height, x_offset = 150)
        self._create_other_section(controlPanel, width = 150, height = self.control_panel_height)

        container = QWidget()
        container.setLayout(controlPanel)
        layout.addWidget(container)

    def _create_button_section(self, panel_layout: QHBoxLayout, width: int = 0, height: int = 0, x_offset: int = 0, y_offset: int = 0) -> None:
        """
        Helper method for creating button elements on the interface control panel.
        """
        reloadButton = QPushButton('Reload View')
        reloadButton.clicked.connect(self.map_view.handle_button)
        reloadButton.setFixedSize(QSize(width, height))
        reloadButton.setGeometry(self.app_width - width, self.img_buffer_height, width, height)
        panel_layout.addWidget(reloadButton)

    def _create_category_section(self, panel_layout: QHBoxLayout, width: int = 0, height: int = 0, x_offset: int = 0, y_offset: int = 0) -> None:
        """
        Helper method for creating category elements on the interface control panel.
        """
        # panel_layout.addWidget(...)
        pass

    def _create_other_section(self, panel_layout: QHBoxLayout, width: int = 0, height: int = 0, x_offset: int = 0, y_offset: int = 0) -> None:
        """
        Helper method for creating all other elements on the interface control panel.
        """
        # panel_layout.addWidget(...)
        pass
    
    def compute_interface_size(self, window_width_px: int = None, window_height_px: int = None) -> Tuple[int, int]:
        """
        Method for determining and setting optimal window dimensions and interface display scale.
        """
        if self.tile_dimensions[0] != self.tile_dimensions[1]:
            raise Exception("Imagery with unequal dimensions is not supported.")
        
        primary_monitor = MonitorFromPoint((0,0))
        monitor_info = GetMonitorInfo(primary_monitor)
        monitor_area = monitor_info.get("Monitor")
        work_area = monitor_info.get("Work")
        taskbar_y_offset = monitor_area[3] - work_area[3]

        screen_width = window_width_px
        if not screen_width:
            screen_width = QApplication.primaryScreen().size().width()

        screen_height = window_height_px
        if not screen_height:
            screen_height = QApplication.primaryScreen().size().height() - taskbar_y_offset - self.control_panel_height

        tile_width = int(screen_width / self.tile_dimensions[0])
        tile_width = min(tile_width, self.max_tile_width)
        tile_height = int(screen_height / self.tile_dimensions[1])
        tile_height = min(tile_height, self.max_tile_height)

        if tile_width < 3 or tile_height < 3:
            raise Exception("Minimum tile resolution was exceeded.")
        
        return int(tile_width * self.tile_dimensions[0]), int((tile_height * self.tile_dimensions[1]) + self.control_panel_height)
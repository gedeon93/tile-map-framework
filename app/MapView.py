from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtGui import QPixmap, QPainter # , QBrush, QPen, QColor
from PyQt5.QtCore import QTimer, QPoint, QRect, QEvent
from typing import Tuple

from app.ImageDownloader import ImageDownloader

# TODO: Util usage of geodetic, tile-layer and pixel conversions and operations for drawn elements
# from util import *

class MapView(QWidget):
    def __init__(self, map_width_px: int, map_height_px: int, img_res_width: int, img_res_height: int, 
                 storage_path: str = None, thread_count: int = 4, update_interval: int = 1000, max_zoom_level: int = 10):
        super().__init__()
        self.update_interval: int = update_interval
        self.storage_path: str = storage_path
        self.is_active: bool = False
        
        self.min_zoom_level: int = 3 # Hard Requirement
        self.max_zoom_level: int = max_zoom_level
        self.zoom_level: int = self.min_zoom_level
                
        self.img_res_x: int = img_res_width
        self.img_res_y: int = img_res_height
        self.max_tile_width: int = int(map_width_px / self.img_res_x)
        self.max_tile_height: int = int(map_height_px / self.img_res_y)

        zoom_res = 2 ** self.zoom_level
        self.x_tile_start = int((zoom_res / 2) - round((self.max_tile_width / 2) + 0.49))
        self.x_tile_end = int((zoom_res / 2) + round((self.max_tile_width / 2) - 0.49)) - 1
        self.y_tile_start = int((zoom_res / 2) - round((self.max_tile_height / 2) + 0.49))
        self.y_tile_end = int((zoom_res / 2) + round((self.max_tile_height / 2) - 0.49)) - 1

        self.img_fetch_threads: int = thread_count
        self.mouse_timer_stop_request: bool = False
        self.map_view_frame: QLabel = QLabel()
        self.map_image: QPixmap = QPixmap()

        self.thread_timer: QTimer = QTimer()
        self.thread_timer_scroll: QTimer = QTimer()
        self.thread_timer_scroll_done: bool = True
        self.thread_queue_timer: QTimer = QTimer()
        self.thread_queue: list = []
        self.thread_queue_timer_request_stop: bool = False
        self.thread_queue_timer_done: bool = True

        self.wheel_timer: QTimer = QTimer()
        self.can_change_tile_layer: bool = True
        # self.zoom_center_point: QPoint = QPoint(0, 0)
        self.zoom_dist: int = 0
        self.last_zoom_dist: int = 0

        self.widgets: dict = None

        self.jobs: list = []
        self.img_cache: dict = dict()
        self.img_cache_indexer: list = []
        self.paint_queue: list = []
        memory_limit = 100 * (1024 ** 2) # 100 Mb
        image_cache_limit: int = int(memory_limit / (self.img_res_x * self.img_res_y * 3))
        self.image_cache_limit: int = min(1000, image_cache_limit)
        
        self.installEventFilter(self)

        self._fetch_imagery()
        self.set_map_window(map_width_px, map_height_px)
        
        # Threading for ImageDownloader object
        self.thread_timer: QTimer = QTimer()
        self.thread_timer.setInterval(self.update_interval)
        self.thread_timer.timeout.connect(self.thread_timer_func)
        self.thread_timer.start()

    def set_active_state(self, state: bool) -> None:
        self.is_active = state

    def set_map_window(self, width: int, height: int, x_offset: int = 0, y_offset: int = 0) -> None:
        """
        Configures the image window frame that holds the primary Pixmap image buffer.
        Also defines the Pixmap image buffer size.

        Args:
            width (int): width of the image buffer.
            height (int): height of the image buffer.
            x_offset (int): X-dimension pixel offset of the frame within the main UI window.
            y_offset (int): Y-dimension pixel offset of the frame within the main UI window.

        Returns:
            None.
        """
        self.map_view_frame.setFixedSize(width, height)
        self.map_view_frame.setGeometry(x_offset, y_offset, width, height)
        self.map_view_frame.setVisible(True)
        self.map_image = QPixmap(width, height)
        # self.verify_frame()

    def verify_frame(self) -> None:
        """
        Forces the height and width of the image buffer to be within the specified range limits and ensures
        the image buffer fits within the UI window.
        """
        img = self.img_downloader.get_image_for_key('-'.join([str(x) for x in [self.zoom_level, self.y_tile_start, self.x_tile_start]]))
        if img:
            self.img_res_x = img.size().width()
            self.img_res_y = img.size().height()
        buffer_width = self.img_res_x * self.max_tile_width
        buffer_height = self.img_res_y * self.max_tile_height

        if buffer_width != self.map_image.size().width() or buffer_height != self.map_image.size().height():
            raise Exception(f"Map buffer size is invalid: size [{buffer_width}, {buffer_height}] does not match the preset.")

    ##### INTERFACE CONTROL FUNCTIONS #####
    def hook_widgets(self, **widgets) -> None:
        """
        Method for referencing UI widget objects that are defined within GeospatialUI.
        """
        self.widgets = widgets
        
    def handle_button(self) -> None:
        """
        Reload button callback. (Deprecated)
        """
        if not self.is_active:
            return
        
        self._fetch_imagery()
        self.thread_timer = QTimer()
        self.thread_timer.setInterval(self.update_interval)
        self.thread_timer.timeout.connect(self.thread_timer_func)
        self.thread_timer.start()

    def wheel_event(self, event: QEvent) -> None:
        """
        Mouse scroll wheel event trigger.
        """
        angle_delta: QPoint = event.angleDelta()
        self.wheel_event_func(angle_delta, event.pos())

    def wheel_event_func(self, angle_delta: QPoint, mouse_pos: QPoint) -> None:
        """
        Mouse scroll wheel event callback. Handles both in/out zooming and evokes image fetching.
        TODO: angle_delta feature not implemented: Zoom multiple levels per the changed amount.
        
        Args:
            angle_delta (QPoint): the amount of change that the mouse wheel scrolled. (UNUSED)
            mouse_pos (QPoint): the position of the mouse cursor when the mouse wheel scrolled.

        Returns:
            None.
        """
        self.thread_queue_timer_request_stop = True
        if self.can_change_tile_layer:
            self.can_change_tile_layer = False

            next_zoom = self.zoom_level
            if a.y() > 0:
                next_zoom += 1
            else:
                next_zoom -= 1

            if next_zoom > self.max_zoom_level:
                next_zoom = self.max_zoom_level
            if next_zoom < self.min_zoom_level:
                next_zoom = self.min_zoom_level

            self.wheel_timer = QTimer()
            self.wheel_timer.setInterval(self.update_interval)
            self.wheel_timer.timeout.connect(self.reset_wheel_func)
            self.wheel_timer.start()
            if next_zoom != self.zoom_level:
                self.get_imagery(next_zoom, p)
                
    def reset_wheel_func(self) -> None:
        """
        Method for resetting the thread queue timer. Triggered on detection of mouse wheel scrolling stopped.
        """
        if self.thread_queue_timer_done:
            self.thread_queue_timer.stop()
            self.can_change_tile_layer = True
            '''
            self.currPanJobs = []
            self.triggeredXPos = False
            self.triggeredXNeg = False
            self.triggeredYPos = False
            self.triggeredYNeg = False
            self.panOffset = QPoint(0, 0)
            self.mouse_timer_stop_request = False
            self.translateMapQPoint = QPoint(0, 0)
            '''

            self.thread_queue = []
            self.thread_queue_timer = QTimer()
            self.thread_queue_timer.setInterval(100)
            self.thread_queue_timer.timeout.connect(self.process_thread_queue)
            self.thread_queue_timer.start()
            self.thread_queue_timer_done = False
            self.thread_queue_timer_request_stop = False

            self.wheel_timer.stop()

    def click_zoom(self, click_pos: QPoint, zoom_direction: bool) -> None:
        """
        Handles zooming (image fetch) on mouse click.

        Args:
            click_pos (QPoint): the position of the mouse cursor when the click occured.
            zoom_direction (bool): the direction of the zoom (in or out). A value of 'True' signals a zoom in action.

        Returns:
            None.
        """
        self.get_imagery(self.zoom_level + (2*int(zoom_direction)-1), click_pos) 

    ##### GEOGRAPHIC IMAGERY FUNCTIONS #####
    def _fetch_imagery(self, job_list: list = None) -> bool:
        """
        Internal method for initializing and firing thread workers for image retreival from the ArcGIS server.
        
        Args:
            job_list (list, optional): specified list of image jobs for retreival. Useful for area-based reloading.

        Returns:
            None.
        """
        jobs = []
        if job_list:
            jobs = job_list
        else:
            for i in range(self.x_tile_start, self.x_tile_end+1):
                for j in range(self.y_tile_start, self.y_tile_end+1):
                    tileStr = str(self.zoom_level) + "-" + str(j) + "-" + str(i)
                    jobs.append(tileStr)

        self.jobs = jobs
        if len(self.jobs) > 0:
            self.img_downloader = ImageDownloader(self.jobs, self.img_fetch_threads, list(self.img_cache.keys()), file_dir=self.storage_path)
            self.img_downloader.start()
            return True
        return False

    def _cache_image(self, pixmap: QPixmap, key: str) -> QPixmap:
        """
        Internal method for caching an image (pixmap) for a supplied key.
        
        Args:
            pixmap (QPixmap): pixmap image to be stored in cache.
            key (str): unique key for accessing the pixmap image.

        Returns:
            QPixmap: the pixmap stored in cache, if exists. Otherwise returns the pixmap supplied.
        """
        in_cache_test = "was "
        if key in self.img_cache:
            # Recently accessed, put at front of list.
            i = self.img_cache_indexer.index(key)
            del self.img_cache_indexer[i]
            self.img_cache_indexer.insert(0, key)
            pixmap = self.img_cache[key]
        else:
            in_cache_test += "not"
            self.img_cache[key] = pixmap
            self.img_cache_indexer.insert(0, key)

            '''
            DO NOT EXCEED 100Mb storage during runtime
            Estimate: image_cache_limit of about 400 images (~262Kb per) results in 100Mb
            '''
            if len(self.img_cache_indexer) + 2 > self.image_cache_limit:
                delete_key = self.img_cache_indexer[-1]
                del self.img_cache[delete_key]
                del self.img_cache_indexer[-1]
        
        return pixmap

    def get_imagery(self, zoom_to: int, position: QPoint) -> bool:
        """
        Computes the set of image keys ("tiles") about a mouse position and zoom level to fetch.
        
        Args:
            zoom_to (int): level to zoom to (in or out).
            position (position): the position of the mouse cursor; serves as the center point for zooming.

        Returns:
            bool: the status of retreival.
        """
        if not self.is_active:
            return False
        
        curr_zoom = self.zoom_level
        x_start_tile = self.x_tile_start
        y_start_tile = self.y_tile_start
        x_end_tile = self.x_tile_end
        y_end_tile = self.y_tile_end
        if zoom_to < self.min_zoom_level or zoom_to > self.max_zoom_level or zoom_to == curr_zoom:
            return False

        zoom_diff = zoom_to - curr_zoom
        curr_zoom_resolution = 2 ** curr_zoom
        next_zoom_resolution = 2 ** zoom_to
        
        x_pos = position.x() / self.map_image.size().width()
        y_pos = position.y() / self.map_image.size().height()

        # x_tile_at_pos = (x_start_tile * 2) + int(x_pos * (next_zoom_resolution * self.max_tile_width / curr_zoom_resolution))
        # y_tile_at_pos = (y_start_tile * 2) + int(y_pos * (next_zoom_resolution * self.max_tile_height / curr_zoom_resolution))
        x_tile_at_pos = int(x_start_tile * (2 ** zoom_diff) + (x_pos * self.max_tile_width * next_zoom_resolution / curr_zoom_resolution))
        y_tile_at_pos = int(y_start_tile * (2 ** zoom_diff) + (y_pos * self.max_tile_height * next_zoom_resolution / curr_zoom_resolution))
        
        if zoom_diff < 0:
            x_tile_at_pos = int((x_start_tile + 1) / (2 ** (-1 * zoom_diff)) + (x_pos * self.max_tile_width * next_zoom_resolution / curr_zoom_resolution))
            y_tile_at_pos = int((y_start_tile + 1) / (2 ** (-1 * zoom_diff)) + (y_pos * self.max_tile_height * next_zoom_resolution / curr_zoom_resolution))

        """
        if x_tile_at_pos < 1:
            x_tile_at_pos = 1
        if x_tile_at_pos > (next_zoom_resolution - 1):
            x_tile_at_pos = next_zoom_resolution - 1
            
        if y_tile_at_pos < 1:
            y_tile_at_pos = 1
        if y_tile_at_pos > (next_zoom_resolution - 1):
            y_tile_at_pos = next_zoom_resolution - 1
        """

        x_tiles_lower = int(self.max_tile_width / (2 ** abs(zoom_diff))) - int(bool(x_pos >= 0.5))
        x_tiles_lower = max(x_tiles_lower, 0)
        x_tiles_upper = (self.max_tile_width - 1) - x_tiles_lower
        y_tiles_lower = int(self.max_tile_height / (2 ** abs(zoom_diff))) - int(bool(y_pos >= 0.5))
        y_tiles_lower = max(y_tiles_lower, 0)
        y_tiles_upper = (self.max_tile_height - 1) - y_tiles_lower 

        self.x_tile_start = x_tile_at_pos - x_tiles_lower
        self.x_tile_end = x_tile_at_pos + x_tiles_upper
        self.y_tile_start = y_tile_at_pos - y_tiles_lower
        self.y_tile_end = y_tile_at_pos + y_tiles_upper
        self.zoom_level = zoom_to
        
        if x_tile_at_pos - x_tiles_lower < 0:
            self.x_tile_start = 0
            self.x_tile_end = self.max_tile_width - 1
        if x_tile_at_pos + x_tiles_upper > (next_zoom_resolution - 1):
            self.x_tile_end = next_zoom_resolution - 1
            self.x_tile_start = self.x_tile_end - (self.max_tile_width - 1)

        if y_tile_at_pos - y_tiles_lower < 0:
            self.y_tile_start = 0
            self.y_tile_end = self.max_tile_height - 1
        if y_tile_at_pos + y_tiles_upper > (next_zoom_resolution - 1):
            self.y_tile_end = next_zoom_resolution - 1
            self.y_tile_start = self.y_tile_end - (self.max_tile_height - 1)
        
        """
        print('\n=== TEST === TEST === TEST ===')
        print(x_tiles_lower, x_tiles_upper, y_tiles_lower, y_tiles_upper)
        print(f"Img buffer = {self.map_image.size().width()} x {self.map_image.size().height()}")
        print(f"Zoom Mouse Pos. = {x_pos} x {y_pos}")
        print(f"Zoom-From Mouse Tile = {x_pos * self.max_tile_width} x {y_pos * self.max_tile_height}")
        print('curr zoom: ' + str(curr_zoom))
        print('curr start x: ' + str(x_start_tile))
        print('curr end x: ' + str(x_end_tile))
        print('curr start y: ' + str(y_start_tile))
        print('curr end y: ' + str(y_end_tile))        
        print('== ZOOM TESTING ==')
        print(f"Zoom-To (Center) Mouse Tile = {x_tile_at_pos} x {y_tile_at_pos}")
        print('next zoom: ' + str(self.zoom_level))
        print('next start x: ' + str(self.x_tile_start))
        print('next end x: ' + str(self.x_tile_end))
        print('next start y: ' + str(self.y_tile_start))
        print('next end y: ' + str(self.y_tile_end))
        print()
        """
        
        fetch_result = self._fetch_imagery()

        self.thread_timer = QTimer()
        self.thread_timer.setInterval(self.update_interval)
        self.thread_timer.timeout.connect(self.thread_timer_func)
        self.thread_timer.start()
        
        return fetch_result

    ##### THREAD HANDLER FUNCTIONS #####
    def thread_timer_func(self) -> bool:
        """
        Computes the set of image keys ("tiles") about a mouse position and zoom level to fetch.
        
        Args:
            zoom_to (int): level to zoom to (in or out).
            position (position): the position of the mouse cursor; serves as the center point for zooming.

        Returns:
            bool: the status of retreival.
        """
        if self.img_downloader.check_completed():
            self.thread_timer.stop()
            if self.img_downloader.no_data_assert():
                return False

            self.paint_frame()
            return True

        return False

    def process_thread_queue(self) -> None:
        if len(self.thread_queue) < 1:
            if self.thread_queue_timer_request_stop and self.thread_timer_scroll_done:
                self.thread_queue_timer_request_stop = False
                self.thread_queue_timer.stop()
                self.thread_queue_timer_done = True
            return

        if self.thread_timer_scroll_done:
            self.img_downloader = ImageDownloader(self.thread_queue[0], 2, list(self.img_cache.keys()))
            self.img_downloader.start()
        
            self.thread_timer_scroll = QTimer()
            self.thread_timer_scroll.setInterval(self.update_interval)
            self.thread_timer_scroll.timeout.connect(self.thread_timer_func)
            self.thread_timer_scroll_done = False
            self.thread_timer_scroll.start()
        
    def tile_to_pixel(self, xTile: float, yTile: float, ignoreFrame=False) -> Tuple[int, int]:
        if not ignoreFrame and (xTile * self.img_res_x > self.map_image.size().width() or yTile * self.img_res_y > self.map_image.size().height()):      
            return (0, 0)        
        return (int(xTile * self.img_res_x), int(yTile * self.img_res_y))

    ##### PAINT FUNCTIONS #####
    def paint_frame(self) -> None:
        """
        Paint all visualization elements.
        """
        # INITIALIZE PAINTER OBJECT
        self.painter = QPainter(self.map_image)
        self.painter.setRenderHint(QPainter.Antialiasing)

        # PAINT BACKGROUND (ARCGIS SATELLITE IMAGERY)        
        imgs = self.img_downloader.get_cache()
        for key in list(imgs.keys()):
            ci = int(key.split('-')[2])
            cj = int(key.split('-')[1])
            r = QRect(self.img_res_x * (ci - self.x_tile_start), self.img_res_y * (cj - self.y_tile_start), self.img_res_x, self.img_res_y)
            if key in imgs:
                img = self._cache_image(imgs[key][0], key)
                if isinstance(img, QPixmap):
                    self.painter.drawPixmap(r, img, QRect(img.rect()))
                else:
                    print(f"Error: Image not retrieved. Got {type(img)} type containing '{img}'.")

        # Paint Distinct Layer Elements
        # draw_circles(...)
        # draw_rectangles(...)

        # STOP PAINTING AND SET FRAME
        self.painter.end()
        self.map_view_frame.setPixmap(self.map_image)
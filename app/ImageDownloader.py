from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool, pyqtSlot, QEventLoop, QCoreApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QProgressBar

import urllib.request
import certifi
import ssl
import traceback, sys
from io import BytesIO
from PIL import Image
from typing import Callable, Tuple

# Define worker signals for runtime checks
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()


class Worker(QRunnable):
    def __init__(self, func: Callable[[str], Tuple], key: str):
        super().__init__()
        self.func = func
        self.key = key
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = tuple([self.key, self.func(self.key)])
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class ImageDownloader(QObject):
    def __init__(self, jobs: list = [], threads: int = None, cache_keys: list = [], file_dir: bool = None, is_batch=False):
        super().__init__()
        self.jobs: list = jobs
        self.threads: int = threads
        self.loop: QEventLoop = None
        
        self.imgCache: dict = {}
        self.keys: list = cache_keys
        self.is_batch = is_batch
        self.bar = QProgressBar()
        self.bar.setMinimum(0)
        self.bar.setMaximum(100)
        
        self.workers = []
        
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(4, self.threads))

        self.timer_check: int = 0
        self.completed: int = 0

        self.file_dir: bool = file_dir
        self.context: object = ssl.create_default_context(cafile=certifi.where())

    def print_result(self, r: list) -> None:
        self.imgCache[r[0]] = r[1]

    def worker_finished(self, worker) -> None:
        """
        Method for tracking worker completion.
        """
        self.completed += 1
        percent_complete = int((self.completed / len(self.jobs)) * 100)
        self.bar.setValue(percent_complete)

        if worker in self.workers:
            self.workers.remove(worker)

        if self.loop is not None:
            self.loop.quit()
        if self.completed >= len(self.jobs):
            if self.is_batch:
                QCoreApplication.quit()

    def start(self) -> None:
        """
        Method to kick off Worker processing for all requested jobs.
        """
        self.loop = QEventLoop()
        for job in self.jobs:
            worker = Worker(self.download_image, job)
            worker.signals.result.connect(self.print_result)
            worker.signals.finished.connect(lambda: self.worker_finished(worker))
            self.workers.append(worker)
            self.pool.start(worker)
        # self.pool.waitForDone()
        self.loop.exec_()
        
    def download_image(self, key: str) -> Tuple[any, any]:
        """
        Fetches image data from the arcgis server.

        Args:
            key (str): unique key for the image data (tile).

        Returns:
            pixmap (QPixmap): image data or returns 'cached' if already downloaded.
            cache (str): sampled cache key from every 16th byte.
        """
        if key not in self.keys:
            addr = key.replace('-', "/")

            url = "https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/" + addr + ".JPEG"
            data = urllib.request.urlopen(url, context=self.context).read()
            d = ' '
            if len(str(data)) > 16:
                d = data[::16]

            p = None
            if self.is_batch:
                image_file = Image.open(BytesIO(data))
                file_key = str(addr.split('/')[0]) + '/' + '-'.join(key.split('-')[1:])
                image_file.save('/'.join([self.file_dir, file_key + '.JPG']))
            else:
                p = QPixmap()
                p.loadFromData(data)
                if self.file_dir:
                    p.save(self.file_dir + key, ".JPG")

            return p, d

        return 'cached'

    def no_data_assert(self) -> bool:
        """
        Assert that no new image data is received from fetching."
        Two step check:
        1. Verify whether the fetched data is already cached.
        2. Check the subsampled cache keys for any data duplication.

        Args:
            None.

        Returns:
            bool: True if the image is already cached. False if new or dissimilar data exists.
        """
        if self.check_completed():
            data = self.imgCache[self.jobs[0]][1]
            count = 0
            uncached = []
            k = list(self.imgCache.keys())
            for c, j in zip(range(0, len(k)), self.imgCache.values()):
                if j != 'cached':
                    uncached.append(c)

            if len(uncached) < 2:
                return False
            else:
                data = self.imgCache[k[uncached[0]]][1]

            cap = 4
            if cap > len(uncached):
                cap = len(uncached)

            for i in range(1,cap):
                data2 = self.imgCache[k[uncached[i]]][1]
                count += int(data == data2)

            if count > 1:
                return True
        return False

    def get_cache(self) -> dict:
        return self.imgCache

    def get_jobs(self) -> list:
        return self.jobs

    def get_image_for_key(self, key: str) -> bool:
        if key in self.imgCache:
            return self.imgCache[key]
        return None
    
    def check_completed(self) -> bool:
        if self.completed >= len(self.jobs):
            return True
        return False


if __name__ == "__main__":
    # For batch download use
    import os
    import sys
    import argparse
    from itertools import product

    app = QCoreApplication(sys.argv)

    def download_query():
        parser = argparse.ArgumentParser(description="Direct usage of the ImageDownloader module is for batch downloads of ArcGIS image data.")
        parser.add_argument('-p', '--download_path', type=str, default=None, required=True,
                            help='Specify a path to the source directory where the application resides.')
        parser.add_argument('-min_zoom', '--min_zoom_level', type=int, default=0, required=True,
                            help='Lowest Level of Detail to download.')
        parser.add_argument('-max_zoom', '--max_zoom_level', type=int, default=0, required=True,
                            help='Highest Level of Detail to download.')
        parser.add_argument('-mem', '--memory_limit', type=int, default=101, required=False,
                    help='Maximum allowed megabytes of disk storage to use. Downloading will stop prematurely if breached.')

        args = parser.parse_args()

        download_directory = ""
        if args.download_path:
            download_directory = str(args.download_path)

        if not os.path.exists(download_directory):
            raise Exception(f"""The directory "{download_directory}" was not found.""")
            
        minimum_zoom_level = 0
        maximum_zoom_level = 0
        if args.min_zoom_level:
            try:
                minimum_zoom_level = int(args.min_zoom_level)
            except (TypeError, ValueError) as e:
                raise Exception(f"""Invalid input "{args.min_zoom_level}" for minimum zoom level.""")
        
        if args.max_zoom_level:
            try:
                maximum_zoom_level = int(args.max_zoom_level)
            except (TypeError, ValueError) as e:
                raise Exception(f"""Invalid input "{args.max_zoom_level}" for maximum zoom level.""")
            else:
                if minimum_zoom_level > maximum_zoom_level:
                    raise Exception("The zoom level of detail minimum must be lower than the maximum.")

        disk_memory_limit = 101
        if args.memory_limit:
            try:
                disk_memory_limit = int(args.memory_limit)
            except (TypeError, ValueError) as e:
                raise Exception(f"""Invalid input "{args.memory_limit}" for download disk memory limit.""")

        number_of_images = 2 ** ((maximum_zoom_level - minimum_zoom_level) + 1) - 1
        disk_memory_estimate = int(((256 ** 2) * 3 * number_of_images) / (1024 ** 2))

        if disk_memory_estimate > disk_memory_limit:
            user_input = input(f"Warning: The download size is estimated to be {disk_memory_estimate}. Continue? (y/n): ")
            if user_input.lower() != "y":
                sys.exit(-1)

        jobs = []
        for n in range(minimum_zoom_level, maximum_zoom_level + 1):
            if not os.path.exists('/'.join([download_directory, str(n)])):
                os.mkdir('/'.join([download_directory, str(n)]))

            grid_resolution = (2 ** n)
            tiles = list(product(range(0, grid_resolution), repeat=2))
            if n == 0:
                tiles = [(0, 0)]
            jobs += ['-'.join([str(n), str(tile[0]), str(tile[1])]) for tile in tiles]

        img_downloader = ImageDownloader(jobs, threads=max(4, os.cpu_count()), file_dir=download_directory, is_batch=True)
        img_downloader.start()            

    download_query()
    sys.exit(app.exec_())

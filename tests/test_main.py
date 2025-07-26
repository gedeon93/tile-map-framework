import os
import sys
import pandas as pd
import unittest

from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.MapInterface import MapInterface

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

class TestMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def test_interface_init(self):
        window = MapInterface(2048, 1200)
        self.assertEqual(window.map_view.max_tile_width, 8)
        self.assertEqual(window.map_view.max_tile_height, 4)
                          
if __name__ == "__main__":
    unittest.main()

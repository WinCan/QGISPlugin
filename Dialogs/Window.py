import os

from PyQt5 import uic
from PyQt5 import QtWidgets


class Window(QtWidgets.QDialog):
    def __init__(self, filename):
        super(Window, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), filename), self)

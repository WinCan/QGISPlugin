import os

from PyQt5 import uic
from PyQt5 import QtWidgets


class Second_window(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Second_window, self).__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'Second_window.ui'), self)
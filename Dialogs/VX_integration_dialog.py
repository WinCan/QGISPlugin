import os

from PyQt5 import uic
from PyQt5 import QtWidgets


class VXDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(VXDialog, self).__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'VX_integration_dialog_base.ui'), self)

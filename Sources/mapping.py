from PyQt5.QtWidgets import QTableWidgetItem, QDialogButtonBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QVariant

from qgis.core import QgsFields, QgsField

from ..Dialogs.Second_window_dialog import Second_window

class Mapping(Second_window):
    def __init__(self, _parent, _VX):
        self.VX_connection = _VX.connection
        self.parent = _parent
        super(Mapping, self).__init__()
        self.mapped_fields = dict()
        self.comboBox.addItem(self.parent.tr("Section"))
        self.comboBox.addItem(self.parent.tr("Manhole"))            
        self.source = self.VX_connection.LayerFieldsPovider.SectionShapeFields
        self.button_box.button(QDialogButtonBox.Ok).setIcon((QIcon(self.parent.plugin_dir + "\\Icons\\OK.png")))
        self.button_box.button(QDialogButtonBox.Ok).setIconSize(QSize(16, 16))
        self.button_box.button(QDialogButtonBox.Cancel).setIcon((QIcon(self.parent.plugin_dir + "\\Icons\\cancel.png")))
        self.button_box.button(QDialogButtonBox.Ok).setIconSize(QSize(16, 16))
        self.comboBox.currentTextChanged.connect(self.get_mapping_fields)
        self.addBtn.clicked.connect(self.add_row)
        self.removeBtn.clicked.connect(self.remove_row)

    def add_row(self):
        if (self.listWidget.currentItem() is not None) and (self.listWidget_2.currentItem() is not None):
            self.tableWidget.insertRow(0)
            self.tableWidget.setItem(0, 0, QTableWidgetItem(self.listWidget.currentItem().text()))
            self.tableWidget.setItem(0, 1, QTableWidgetItem(self.listWidget_2.currentItem().text()))
            self.listWidget.takeItem(self.listWidget.currentRow())
            self.listWidget_2.takeItem(self.listWidget_2.currentRow())
            
    def remove_row(self):
        if self.tableWidget.currentRow() != -1 and self.tableWidget.rowCount() > 0:
            self.listWidget.addItem(self.tableWidget.item(self.tableWidget.currentRow(), 0).text())
            self.listWidget_2.addItem(self.tableWidget.item(self.tableWidget.currentRow(), 1).text())
            self.tableWidget.removeRow(self.tableWidget.currentRow())
            
    def open(self, fields):
        for field in self.get_qgis_fields(self.source):
            self.listWidget.addItem(field.name())
        self.listWidget_2.clear()
        for field in fields:
            self.listWidget_2.addItem(field.name())
            
        if self.exec_():
            self.save_mapping_info()
            return True
            
    def get_mapping_fields(self):
        if self.comboBox.currentText() == self.parent.tr("Section"):
            self.source = self.VX_connection.LayerFieldsPovider.SectionShapeFields
        elif self.comboBox.currentText() == self.parent.tr("Manhole"):
            self.source = self.VX_connection.LayerFieldsPovider.NodeShapeFields
        self.listWidget.clear()
        for field in self.get_qgis_fields(self.source):
            self.listWidget.addItem(field.name())
            
    def save_mapping_info(self):
        for row in range(self.tableWidget.rowCount()):
            self.mapped_fields[self.tableWidget.item(row, 0).text()] = self.tableWidget.item(row, 1).text()

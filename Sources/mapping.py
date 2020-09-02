from PyQt5.QtWidgets import QTableWidgetItem, QDialogButtonBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QVariant

from qgis.core import QgsFields, QgsField

from ..Dialogs.Second_window_dialog import Second_window

class Mapping(Second_window):
    def __init__(self, _parent, _VX):
        super(Mapping, self).__init__()
        self.VX_connection = _VX
        self.parent = _parent
        self.main = self.parent.parent
        self.mapped_fields = dict()
        self.type_selector.addItem(self.main.tr("Section"))
        self.type_selector.addItem(self.main.tr("Manhole"))            
        self.source = self.VX_connection.LayerFieldsPovider.SectionShapeFields
        self.button_box.button(QDialogButtonBox.Ok).setIcon((QIcon(self.main.plugin_dir + "\\Icons\\OK.png")))
        self.button_box.button(QDialogButtonBox.Ok).setIconSize(QSize(16, 16))
        self.button_box.button(QDialogButtonBox.Cancel).setIcon((QIcon(self.main.plugin_dir + "\\Icons\\cancel.png")))
        self.button_box.button(QDialogButtonBox.Ok).setIconSize(QSize(16, 16))
        self.type_selector.currentTextChanged.connect(self.get_mapping_fields)
        self.addBtn.clicked.connect(self.add_row)
        self.removeBtn.clicked.connect(self.remove_row)

    def add_row(self):
        if (self.wincan_fields_list.currentItem() is not None) and (self.layer_fields_list.currentItem() is not None):
            self.mapping_table.insertRow(0)
            self.mapping_table.setItem(0, 0, QTableWidgetItem(self.wincan_fields_list.currentItem().text()))
            self.mapping_table.setItem(0, 1, QTableWidgetItem(self.layer_fields_list.currentItem().text()))
            self.wincan_fields_list.takeItem(self.wincan_fields_list.currentRow())
            self.layer_fields_list.takeItem(self.layer_fields_list.currentRow())
            
    def remove_row(self):
        if self.mapping_table.currentRow() != -1 and self.mapping_table.rowCount() > 0:
            self.wincan_fields_list.addItem(self.mapping_table.item(self.mapping_table.currentRow(), 0).text())
            self.layer_fields_list.addItem(self.mapping_table.item(self.mapping_table.currentRow(), 1).text())
            self.mapping_table.removeRow(self.mapping_table.currentRow())
            
    def open(self, fields):
        self.mapped_fields = dict()
        self.fill_lists_with_field_names(fields)
        if self.exec_():
            self.save_mapping_info()
            return True
            
    def fill_lists_with_field_names(self, fields):
        self.wincan_fields_list.clear()
        self.layer_fields_list.clear()
        for field in self.parent.drawing.get_qgis_fields(self.source):
            self.wincan_fields_list.addItem(field.name())
        self.mapping_table.clearContents()
        self.mapping_table.setRowCount(0)
        for field in fields:
            self.layer_fields_list.addItem(field.name())
            
    def get_mapping_fields(self):
        if self.type_selector.currentText() == self.main.tr("Section"):
            self.source = self.VX_connection.LayerFieldsPovider.SectionShapeFields
        elif self.type_selector.currentText() == self.main.tr("Manhole"):
            self.source = self.VX_connection.LayerFieldsPovider.NodeShapeFields
        self.wincan_fields_list.clear()
        for field in self.parent.drawing.get_qgis_fields(self.source):
            self.wincan_fields_list.addItem(field.name())
            
    def save_mapping_info(self):
        for row in range(self.mapping_table.rowCount()):
            self.mapped_fields[self.mapping_table.item(row, 0).text()] = self.mapping_table.item(row, 1).text()

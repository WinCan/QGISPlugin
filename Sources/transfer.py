import clr
import uuid

from PyQt5.QtCore import QCoreApplication

clr.AddReference("ZeroMQ")
clr.AddReference("CDLAB.WinCan.MQ")
clr.AddReference("CDLAB.WinCan.SDK.GIS")
clr.AddReference("CDLAB.WinCan.SDK.GIS.UI")
clr.AddReference("CDLAB.WinCan.Template")

import ZeroMQ
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType, EntityType, Infrastructure
from System.Collections.Generic import Dictionary
from System import String
from System import Object

from .drawing import Drawing
from .mapping import Mapping

class Transfer:    
    def __init__(self, _parent, _VX, _qgis):
        self.VX = _VX
        self.qgis = _qgis
        self.parent = _parent
        self.drawing = Drawing(self.parent, self.VX, self.qgis)
        self.mapping_window = Mapping(self, self.VX)
        
        
        self.vx_fields = Infrastructure.VxFields
        self.batch_update = CDLAB.WinCan.SDK.GIS.Model.UpdateBatch()
    
    def tr(self, message):
        return QCoreApplication.translate('TransferToWinCan', message)

    def is_wincan_layer(self):
        return self.layer.name() in self.drawing.wincan_layers

    def check_conditions(self):
        self.count, self.selected_shapes, self.layer = self.drawing.get_selected()
        if (self.layer is None):
            self.parent.show_warning(self.tr(
                "Please select layer to transfer"))
            return False

        if self.is_wincan_layer():
            self.parent.show_warning(self.tr(
                "Transfer feature is not available for WinCan layers"))
            return False

        if not self.VX.IsConnected:
            self.parent.show_warning(self.tr(
                "Missing connection to WinCan VX"))
            return False

        if (self.count == 0):
            self.parent.show_warning(self.tr(
                "Please select shapes to transfer"))
            return False
        return True

    def transfer_sections(self):
        for Section in self.selected_shapes:
            if Section is None:
                return
            fields = Dictionary[String, Object]()
            for key, field in self.mapping_window.mapped_fields.items():
                value = str(Section.attribute(str(field)))
                if key == "OBJ_PK":
                    fields[self.vx_fields.OBJ_PK] = str(uuid.uuid4())
                    continue
                fields[key] = value
            shape = str(Section.geometry().asWkt(8))
            shape = shape.replace("LineString", "LINESTRING")
            shape = shape.replace("Z", " Z")
            fields[self.vx_fields.OBJ_Shape_WKT] = shape

            if not fields.ContainsKey(self.vx_fields.OBJ_Type):
                fields[self.vx_fields.OBJ_Type] = "SEC"

            self.batch_update.AddItem(EntityType.Section, fields)
        self.VX.SendBatchToWinCanVX(self.batch_update)

    def transfer_nodes(self):
        for node in self.selected_shapes:
            if node is None:
                return
            fields = Dictionary[String, Object]()
            shape = str(node.geometry().asWkt())
            shape = shape.replace("Point", "POINT")
            shape = shape.replace("ZM", " ZM")
            fields[self.vx_fields.OBJ_Shape_WKT] = shape
            for key, field in self.mapping_window.mapped_fields.items():
                value = str(node.attribute(str(field)))
                if key == "OBJ_PK":
                    fields[self.vx_fields.OBJ_PK] = str(uuid.uuid4())
                    continue

            if not fields.ContainsKey(self.vx_fields.OBJ_Type):
                fields[self.vx_fields.OBJ_Type] = "NOD"
                fields[key] = value

            self.batch_update.AddItem(EntityType.Node, fields)
        self.VX.SendBatchToWinCanVX(self.batch_update)

    def transfer(self):
        if self.check_conditions():
            result = self.mapping_window.open(self.layer.fields())
            if result:
                self.transfer_form()

    def transfer_form(self):
        if self.layer.geometryType() == 0:
            self.transfer_nodes()
        else:
            self.transfer_sections()

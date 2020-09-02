import os.path
import clr
import uuid
import traceback
import subprocess
from datetime import datetime
from System.Threading import SynchronizationContext
from System.Collections.Generic import Dictionary
from System import String
from System import Object
from System import EventHandler

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QTimer, QVariant, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QWidget, QTableWidgetItem, QDialogButtonBox, QToolBar
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsFields, QgsField, QgsVectorFileWriter, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsFeature, QgsPointXY, QgsGeometry, QgsPalLayerSettings, QgsFeatureRequest


import ZeroMQ
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType, EntityType, Infrastructure
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template


class Transfer:
    def __init__(self):
        self.winCan_layers = ["WinCan Inspections",
                              "WinCan Sections",
                              "WinCan Manholes",
                              "WinCan Manhole Inspections",
                              "WinCan Manhole Observations",
                              "WinCan Observations"]

    def tr(self, message):

        return QCoreApplication.translate('TransferToWinCan', message)

    def IsWinCanLayer(self, VX, active_layer):

        if active_layer.name() in self.winCan_layers:
            return True

    def SaveVxShape(self, currentshape):

        VxFields = Infrastructure.VxFields
        type = EntityType.Section
        fields = dict()

        if (currentshape.TagPointer is Null):
            VX.show_error(TransferToWinCan.tr(
                "Shape is missing Reference to WinCan VX"))

        if (currentshape.TagPointer is section):
            type = EntityType.Section
            fields[VxFields.OBJ_PK] = section.Id

        elif (currentshape.TagPointer is inspection):
            type = EntityType.SectionInspection
            fields[VxFields.INS_PK] = inspection.Id

        elif (m_currentshape.TagPointer is observation):
            type = EntityType.SectionObservation
            fields[VxFields.OBS_PK] = observation.Id

        elif (m_currentshape.TagPointer is nodeInspection):
            type = EntityType.NodeInspection
            fields[VxFields.INS_PK] = nodeInspection.Id

        elif (m_currentshape.TagPointer is nodeObservation):
            type = EntityType.NodeObservation
            fields[VxFields.OBS_PK] = nodeObservation.Id

        elif (m_currentshape.TagPointer is node):
            type = EntityType.Node
            fields[VxFields.OBS_PK] = node.Id

        elif (m_currentshape.TagPointer is area):
            type = EntityType.GeoArea
            fields[VxFields.GEA_PK] = area.Id

        VxConnector.SendToWinCanVX(type, fields)

    def CheckConditions(self, VX):

        select = selection(VX)
        layer = select.layer

        if (layer is None):
            VX.show_warning(TransferToWinCan.tr(
                "Please select layer to transfer"))
            return False

        if IsWinCanLayer(VX, layer):
            VX.show_warning(TransferToWinCan.tr(
                "Transfer feature is not available for WinCan layers"))
            return False

        if not VX.vxConnector.IsConnected:
            VX.show_warning(TransferToWinCan.tr(
                "Missing connection to WinCan VX"))
            return False

        if (select.Count == 0):
            VX.show_warning(TransferToWinCan.tr(
                "Please select shapes to transfer"))
            return False

    def TransferSections(VX):

        VxFields = Infrastructure.VxFields
        updateBatch = CDLAB.WinCan.SDK.GIS.Model.UpdateBatch()

        for Section in selection(VX).SelectedShapes:
            if Section is None:
                return

            fields = Dictionary[String, Object]()

            for key, field in VX.MappedFields.items():

                value = str(Section.attribute(str(field)))

                if key == "OBJ_PK":
                    fields[VxFields.OBJ_PK] = str(uuid.uuid4())
                    continue

                fields[key] = value

            shape = str(Section.geometry().asWkt(8))
            shape = shape.replace("LineString", "LINESTRING")
            shape = shape.replace("Z", " Z")
            fields[VxFields.OBJ_Shape_WKT] = shape

            if not fields.ContainsKey(VxFields.OBJ_Type):
                fields[VxFields.OBJ_Type] = "SEC"

            updateBatch.AddItem(EntityType.Section, fields)
        VX.vxConnector.SendBatchToWinCanVX(updateBatch)

    def TransferNodes(self, VX):

        VxFields = Infrastructure.VxFields
        updateBatch = CDLAB.WinCan.SDK.GIS.Model.UpdateBatch()

        for node in selection(VX).SelectedShapes:
            if node is None:
                return
            fields = Dictionary[String, Object]()
            shape = str(node.geometry().asWkt())
            shape = shape.replace("Point", "POINT")
            shape = shape.replace("ZM", " ZM")
            fields[VxFields.OBJ_Shape_WKT] = shape
            for key, field in VX.MappedFields.items():

                value = str(node.attribute(str(field)))

                if key == "OBJ_PK":
                    fields[VxFields.OBJ_PK] = str(uuid.uuid4())
                    continue

            if not fields.ContainsKey(VxFields.OBJ_Type):
                fields[VxFields.OBJ_Type] = "NOD"
                fields[key] = value

            updateBatch.AddItem(EntityType.Node, fields)
        VX.vxConnector.SendBatchToWinCanVX(updateBatch)

    def Transfer(self):

        if self.CheckConditions(self.VX) is False:
            return
        layer_fields = select(self.VX).layer.fields()
        if self.mapping_window.open(layer_fields):
            self.transfer_form()

    def transfer_form(self):
        if select(VX).layer.geometryType() == 0:
            self.TransferNodes(VX)
        else:
            self.TransferSections(VX)

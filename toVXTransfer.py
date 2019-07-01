# -*- coding: utf-8 -*-
"""
/***************************************************************************
 VX
                                 A QGIS plugin
 Download data from WinCan VX
                              -------------------
        begin                : 2019-05-17
        copyright            : (C) 2019 by WinCan Poland
        email                : p.paziewski@wincan.com
 ***************************************************************************/
"""

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication,QTimer, QVariant
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsFields, QgsField,QgsVectorFileWriter, QgsWkbTypes, QgsCoordinateReferenceSystem,QgsFeature,QgsPointXY,QgsGeometry,QgsPalLayerSettings, QgsFeatureRequest
from .resources import *
from .VX_integration_dialog import VXDialog
import sys
import os.path
import time
import uuid
import array
import numpy
from datetime import datetime
from ctypes import cdll, windll
sys.path.append((os.path.dirname(__file__)+ "\DLL").rstrip())
windll.LoadLibrary(os.path.dirname(__file__)+ "\DLL\libsodium.dll")

import clr
clr.AddReference("ZeroMQ")
clr.AddReference("CDLAB.WinCan.MQ")
clr.AddReference("CDLAB.WinCan.SDK.GIS")
clr.AddReference("CDLAB.WinCan.SDK.GIS.UI")
clr.AddReference("CDLAB.WinCan.Template")
import ZeroMQ
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType, EntityType, Infrastructure
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template
from System.Collections.Generic import Dictionary
from System.Threading import SynchronizationContext
from System.Threading.Tasks import TaskScheduler, Task
from System.IO import FileInfo
from System import Environment, EventHandler, String, Object, Runtime, Guid

class selection:
    
    def __init__(self,VX):
        
        self.Count = 0
        self.SelectedShapes = []
        self.layer = VX.iface.activeLayer()
        if type(self.layer) is not type(None):
            for feature in self.layer.selectedFeatures():
                self.Count += 1
                self.SelectedShapes.append(feature)
            
class TransferToWinCan:
    
    def tr(message):

        return QCoreApplication.translate('TransferToWinCan', message)
  
    def IsWinCanLayer(VX,active_layer):
        
        for layer in VX.created_layers:
            if layer == active_layer:
                return True
            else:
                return False
    
    def SaveVxShape(currentshape):
        
        VxFields = Infrastructure.VxFields
        type = EntityType.Section
        fields = dict()
        
        if (currentshape.TagPointer is Null):
            VX.show_error(TransferToWinCan.tr("Shape is missing Reference to WinCan VX"))
              
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

    def CheckConditions(VX):
        
        select = selection(VX)
        layer = select.layer
        
        
        if (layer is None):
            VX.show_warning(TransferToWinCan.tr("Please select layer to transfer"))
            return False

        if (TransferToWinCan.IsWinCanLayer(VX, layer)):
            VX.show_warning(TransferToWinCan.tr("Transfer feature is not available for WinCan layers"))
            return False
 
        if not VX.vxConnector.IsConnected:
            VX.show_warning(TransferToWinCan.tr("Missing connection to WinCan VX"))
            return False
 
        if (select.Count == 0):
            VX.show_warning(TransferToWinCan.tr("Please select shapes to transfer"))
            return False
        
  
    def TransferSections(VX):
            
        VxFields = Infrastructure.VxFields
        updateBatch = CDLAB.WinCan.SDK.GIS.Model.UpdateBatch()
        
        for Section in selection(VX).SelectedShapes:
            if Section is None:
                return 
        
            fields = Dictionary[String, Object]()

            for key,field in VX.MappedFields.items():
   
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


    def TransferNodes(VX):
        
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
            
            for key,field in VX.MappedFields.items():

                value = str(node.attribute(str(field)))
                
                if key == "OBJ_PK":
                    fields[VxFields.OBJ_PK] = str(uuid.uuid4())
                    continue
                
            if not fields.ContainsKey(VxFields.OBJ_Type):                   
                fields[VxFields.OBJ_Type] = "NOD"
                
                fields[key] = value
                
            updateBatch.AddItem(EntityType.Node, fields)
            
        VX.vxConnector.SendBatchToWinCanVX(updateBatch)
        
    def Transfer(VX):

        if TransferToWinCan.CheckConditions(VX) is False:
            return 
        
        LayerFields = selection(VX).layer.fields()
        
        VX.open_mapping_dialog(LayerFields)
        
    def TransferForm(VX):
        if selection(VX).layer.geometryType() == 0:
            TransferToWinCan.TransferNodes(VX)
        else:
            TransferToWinCan.TransferSections(VX)

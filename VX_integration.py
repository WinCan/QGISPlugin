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
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QAction, QWidget, QTableWidgetItem, QDialogButtonBox
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsFields, QgsField,QgsVectorFileWriter, QgsWkbTypes, QgsCoordinateReferenceSystem,QgsFeature,QgsPointXY,QgsGeometry,QgsPalLayerSettings, QgsFeatureRequest
from .resources import *
from .VX_integration_dialog import VXDialog
from .Second_window_dialog import Second_window
import sys
import os.path
import time
import uuid
import array
import numpy
import shutil
from .toVXTransfer import TransferToWinCan
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
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType, EntityType
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template
from System.Threading import SynchronizationContext
from System.Threading.Tasks import TaskScheduler
from System.IO import FileInfo
from System import Environment, EventHandler


    
class VX:



    def __init__(self, iface):
        self.i = 0
        SynchronizationContext.SetSynchronizationContext(SynchronizationContext())

        self.iface = iface

        self.plugin_dir = os.path.dirname(__file__)

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'VX_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WinCan VX integration')
        
        self.first_start = None
        self.timer = QTimer()
        
        self.vxConnector =  CDLAB.WinCan.SDK.GIS.VxConnector("QGIS " + str(uuid.uuid4()), CDLAB.WinCan.SDK.GIS.ConnectedApplicationType.WinCanMap)
        
        self.MappedFields = dict()
                
        self.layers_created = False
        
        self.first_start_mapping = True

    def tr(self, message):
        """Get the translation for a string using Qt translation API. """

        return QCoreApplication.translate('VX', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:

            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = self.plugin_dir + "\\Icons\\icon.png"
        self.add_action(
            icon_path,
            text=self.tr(u'Open dialog'),
            callback=self.run,
            parent=self.iface.mainWindow())
    

        self.first_start = True
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&WinCan VX integration'),
                action)
            self.iface.removeToolBarIcon(action)

        self.timer.stop()
        if self.first_start != True: 
            pass
        
    def add_mapping_row(self):
        if (self.mapping.listWidget.currentItem() is not None) and (self.mapping.listWidget_2.currentItem() is not None):
            self.mapping.tableWidget.insertRow(0)
            self.mapping.tableWidget.setItem(0, 0, QTableWidgetItem(self.mapping.listWidget.currentItem().text()))
            self.mapping.tableWidget.setItem(0, 1, QTableWidgetItem(self.mapping.listWidget_2.currentItem().text()))
            self.mapping.listWidget.takeItem (self.mapping.listWidget.currentRow())
            self.mapping.listWidget_2.takeItem (self.mapping.listWidget_2.currentRow())
        
    def remove_row(self):
        if self.mapping.tableWidget.currentRow() != -1 and self.mapping.tableWidget.rowCount() > 0:
            self.mapping.listWidget.addItem(self.mapping.tableWidget.item(self.mapping.tableWidget.currentRow(),0).text())
            self.mapping.listWidget_2.addItem(self.mapping.tableWidget.item(self.mapping.tableWidget.currentRow(),1).text())
            self.mapping.tableWidget.removeRow(self.mapping.tableWidget.currentRow())
            
    def save_mapping_info(self):
        row = 0
        while row < self.mapping.tableWidget.rowCount():
            self.MappedFields[self.mapping.tableWidget.item(row,0).text()] = self.mapping.tableWidget.item(row,1).text()
            row += 1
        
    def MapingComboBox(self):
        if self.mapping.comboBox.currentText() == self.tr("Section"):
            source = self.vxConnector.LayerFieldsPovider.SectionShapeFields
        if self.mapping.comboBox.currentText() == self.tr("Manhole"):
            source = self.vxConnector.LayerFieldsPovider.NodeShapeFields
        self.mapping.listWidget.clear()
        for field in self.Fields(source):
            self.mapping.listWidget.addItem(field.name())
        
    def open_mapping_dialog(self, LayerFields):
        
        if self.first_start_mapping is True:
            self.mapping.comboBox.addItem(self.tr("Section"))
            self.mapping.comboBox.addItem(self.tr("Manhole"))
        
            source = self.vxConnector.LayerFieldsPovider.SectionShapeFields
            self.mapping.button_box.button(QDialogButtonBox.Ok).setIcon((QIcon(self.plugin_dir + "\\Icons\\OK.png")))
            self.mapping.button_box.button(QDialogButtonBox.Ok).setIconSize(QtCore.QSize(16, 16))
            self.mapping.button_box.button(QDialogButtonBox.Cancel).setIcon((QIcon(self.plugin_dir + "\\Icons\\cancel.png")))
            self.mapping.button_box.button(QDialogButtonBox.Ok).setIconSize(QtCore.QSize(16, 16))
        
            for field in self.Fields(source):
                self.mapping.listWidget.addItem(field.name())
            
            self.mapping.comboBox.currentTextChanged.connect(self.MapingComboBox)
            
            self.mapping.Dodaj.clicked.connect(self.add_mapping_row)
            self.mapping.Usun.clicked.connect(self.remove_row)
            self.first_start_mapping = False
            
        self.mapping.listWidget_2.clear()
        for field in LayerFields:
            self.mapping.listWidget_2.addItem(field.name())
        
        self.dlg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) 
        self.mapping.show()

        if self.mapping.exec_():
            self.save_mapping_info()
            TransferToWinCan.TransferForm(self)
    
    def ToQGISType(self, VXType):
        
        if VXType == 0:
            return QVariant.Int
        elif VXType == 1:
            return QVariant.Double
        elif VXType == 2:
            return QVariant.String
        elif VXType == 3:
            return QVariant.String
        elif VXType == 4:
            return QVariant.String
        elif VXType == 5:
            return QVariant.Bool
        else:
            return QVariant.String

    def Fields(self, fields):
        
        names = QgsFields()
        for field in fields:
            type = self.ToQGISType(field.Type)
            names.append(QgsField(field.Key, type))
        return names
    
    def UpdateProject(self, project):
        if type(project) != type(None):
            self.dlg.textBrowser.setText(str(self.vxConnector.Project.Key))
        else:
            self.dlg.textBrowser.setText(self.tr("None"))
             
    def UpdateVxData(self, source, args):
        package = source.GetUpdated()
        if (package.IsEmpty == 1):
            return
        else:
            if package.Nodes.Count > 0:
                self.draw_Nodes(package.Nodes)
            if package.Sections.Count > 0:
                self.draw_Sections(package.Sections)
            if package.Observations.Count > 0:
                self.draw_Observations(package.Observations)
            if package.NodeInspections.Count > 0:
                self.draw_NodeInspections(package.NodeInspections)
            if package.NodeObservations.Count > 0:
                self.draw_NodeObservations(package.NodeObservations)
            if package.Inspections.Count > 0:
                self.draw_Inspections(package.Inspections)       
#             self.UpdateProject(package.Project)   
            
    def DeleteFeatures(self, toDelete, FeatureClass):
         
        if FeatureClass is None:
            return
        else:
            FeatureClass.startEditing()
            for entity in toDelete:
                request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], FeatureClass.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % entity.Id)
                for f in FeatureClass.getFeatures(request):
                    FeatureClass.deleteFeature(f.id())
            FeatureClass.updateExtents()
            FeatureClass.commitChanges()
                 
    def OnDeletedEntites(self, source, args):
        
        sections = [entity for entity in args.DeletedEntities if entity.EntityType == 0]
        nodes = [entity for entity in args.DeletedEntities if entity.EntityType == 3]
        inspections = [entity for entity in args.DeletedEntities if entity.EntityType == 1]
        observations = [entity for entity in args.DeletedEntities if entity.EntityType == 2]
        nodeInspections = [entity for entity in args.DeletedEntities if entity.EntityType == 5]
        nodeObservations = [entity for entity in args.DeletedEntities if entity.EntityType == 6]
         
        self.DeleteFeatures(sections, self.created_layers[1])
        self.DeleteFeatures(nodes, self.created_layers[2])
        self.DeleteFeatures(inspections, self.created_layers[0])
        self.DeleteFeatures(observations, self.created_layers[5])
        self.DeleteFeatures(nodeInspections, self.created_layers[3])
        self.DeleteFeatures(nodeObservations, self.created_layers[4])
        self.iface.mapCanvas().refresh()
           
    def create_layers(self, WKT):
        
        InspectionLayerName = "WinCan Inspections"
        SectionLayerName = "WinCan Sections"
        NodeLayerName = "WinCan Manholes"
        NodeInspectionLayerName = "WinCan Manhole Inspections"
        NodeObservationLayerName = "WinCan Manhole Observations"
        ObservationLayerName = "WinCan Observations"
        date = datetime.now()
        layers_path = self.vxConnector.Project.Path + "\\Misc\\Exchange\\QGIS\\Layers" + date.strftime("%d_%m_%Y")
        try:
            os.makedirs(layers_path)
        except FileExistsError:
            pass
        
        if WKT == "WKT:UNKNOWN":
            EPSG = QgsCoordinateReferenceSystem()
        else:
            EPSG = QgsCoordinateReferenceSystem.fromEpsgId(int(WKT.split("\"")[-2]))
        Layers = [InspectionLayerName,SectionLayerName,NodeLayerName,NodeInspectionLayerName,NodeObservationLayerName,ObservationLayerName]
        LFP = self.vxConnector.LayerFieldsPovider
        ShapeFields = [LFP.InspectionShapeFields,LFP.SectionShapeFields,LFP.NodeShapeFields,LFP.NodeInspectionShapeFields,LFP.NodeObservationShapeFields,LFP.ObservationShapeFields]
        self.created_layers = []
        self.fields = []
        nr = 0

        
        for layer in Layers:
            layer_full_path = layers_path + "\\" + layer + ".shp"
            self.fields.append(self.Fields(ShapeFields[nr]))
            if (layer == NodeLayerName or layer == NodeObservationLayerName or layer == ObservationLayerName):
                QgsVectorFileWriter(layer_full_path,
                             "UTF-8",
                             self.Fields(ShapeFields[nr]),
                             QgsWkbTypes.Point,
                             EPSG,
                             "ESRI Shapefile")
            if (layer == InspectionLayerName or layer == NodeInspectionLayerName or layer == SectionLayerName):
                QgsVectorFileWriter(layer_full_path,
                             "UTF-8",
                             self.Fields(ShapeFields[nr]),
                             QgsWkbTypes.LineString,
                             EPSG,
                             "ESRI Shapefile")
            temp = QgsVectorLayer(layer_full_path , layer, 'ogr')
            self.created_layers.append(temp)
            nr +=1
            
        QgsProject.instance().addMapLayers(self.created_layers)
        self.layers_created = True
    
    def Add_values(self, feature, entity, shapefields):
            for attribute in feature.fields():
                for value in shapefields:
                    attr = feature.fieldNameIndex(value.Key)
                    feature.setAttribute(attr, str(entity.GetValue(value)))

    def draw_Inspections(self,Inspections):
        inspections = []
        InspectionLayer = self.created_layers[0]
        InspectionLayer.startEditing()
        prov = InspectionLayer.dataProvider()
        for ins in Inspections:
            points = []
            feature = QgsFeature()
            feature.setFields(self.fields[0])
            for point in ins.Vertices:
                points.append(QgsPointXY(point.X, point.Y))
            feature.setGeometry(QgsGeometry.fromPolylineXY(points))
            self.Add_values(feature, ins, self.vxConnector.LayerFieldsPovider.InspectionShapeFields)
            inspections.append(feature)
                
        prov.addFeatures(inspections)
        InspectionLayer.updateExtents()
        InspectionLayer.commitChanges()   
 
    def draw_Sections(self,Sections):
        sections = []
        SectionLayer = self.created_layers[1]
        SectionLayer.startEditing()
        prov = SectionLayer.dataProvider()
        for section in Sections:
            points = []
            feature = QgsFeature()
            feature.setFields(self.fields[1])
            for point in section.Vertices:
                points.append(QgsPointXY(point.X, point.Y))
            feature.setGeometry(QgsGeometry.fromPolylineXY(points))
            self.Add_values(feature, section, self.vxConnector.LayerFieldsPovider.SectionShapeFields)
            sections.append(feature)
                
        prov.addFeatures(sections)
        
        SectionLayer.loadNamedStyle(self.plugin_dir + '\\Styles\\style_section.qml')
        SectionLayer.updateExtents()
        SectionLayer.commitChanges()   

    def draw_Nodes(self,Nodes):
        nr = 1
        points = []
        NodeLayer = self.created_layers[2]
        NodeLayer.startEditing()
        prov = NodeLayer.dataProvider()
        
        if NodeLayer == None:
            return 
        
        for node in Nodes:
            
            if node.ExternalItemId != 0:
                request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], NodeLayer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % node.Id)
                features = NodeLayer.getFeatures(request)
                for f in features:
                        for value in self.vxConnector.LayerFieldsPovider.NodeShapeFields:
                            attr = NodeLayer.fields().indexFromName(str(value.Key))
                            NodeLayer.changeAttributeValue(f.id(), attr, str(node.GetValue(value)))
            else:                
                point = node.Centroid
                feature = QgsFeature()
                feature.setFields(self.fields[2])
                if (type(point) != type(None)):
                    layerPoint = QgsPointXY(point.X, point.Y)
                feature.setGeometry(QgsGeometry.fromPointXY(layerPoint))
                self.Add_values(feature, node, self.vxConnector.LayerFieldsPovider.NodeShapeFields)
                points.append(feature)
                node.ExternalItemId = nr
                nr += 1 
                
        if points != []:     
            prov.addFeatures(points)
            NodeLayer.loadNamedStyle(self.plugin_dir + '\\Styles\\style_node.qml')
            
        NodeLayer.updateExtents()
        NodeLayer.commitChanges()
        
    def test(self):
        
        pk = "4f8d6329-df8b-493d-a29d-6d45f5d23480"
        layer = self.created_layers[2]
        layer.startEditing()
        request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], layer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % pk)
        features = layer.getFeatures(request)
        for f in features:
            layer.changeAttributeValue(f.id(), layer.fields().indexFromName("OBJ_Key"), "dziala")
        layer.commitChanges()
        

    def draw_NodeInspections(self,NodeInspections):
        nodeinspection = []
        NodeInspectionLayer = self.created_layers[3]
        NodeInspectionLayer.startEditing()
        prov = NodeInspectionLayer.dataProvider()
        for Nodeins in NodeInspections:
            points = []
            feature = QgsFeature()
            feature.setFields(self.fields[3])
            for point in Nodeins.Vertices:
                points.append(QgsPointXY(point.X, point.Y))
            feature.setGeometry(QgsGeometry.fromPolylineXY(points))
            self.Add_values(feature, Nodeins, self.vxConnector.LayerFieldsPovider.NodeInspectionShapeFields)
            nodeinspection.append(feature)
                
        prov.addFeatures(nodeinspection)
        NodeInspectionLayer.updateExtents()
        NodeInspectionLayer.commitChanges()   
        
    def draw_NodeObservations(self,NodeObservation):
        points = []
        NodeObservationLayer = self.created_layers[4]
        NodeObservationLayer.startEditing()
        prov = NodeObservationLayer.dataProvider()
        for Nodeobs in NodeObservation:
            for point in Nodeobs.Vertices:
                feature = QgsFeature()
                feature.setFields(self.fields[4])
                layerPoint = QgsPointXY(point.X, point.Y)
                feature.setGeometry(QgsGeometry.fromPointXY(layerPoint))
                self.Add_values(feature, Nodeobs, self.vxConnector.LayerFieldsPovider.NodeObservationShapeFields)
                points.append(feature)
            
        prov.addFeatures(points)
        
        NodeObservationLayer.loadNamedStyle(self.plugin_dir + '\\Styles\\style_NodeObs.qml')
        NodeObservationLayer.updateExtents()
        NodeObservationLayer.commitChanges()
        
    def draw_Observations(self,Observations):
        points = []
        ObservationLayer = self.created_layers[5]
        ObservationLayer.startEditing()
        prov = ObservationLayer.dataProvider()
        for obs in Observations:
            for point in obs.Vertices:
                feature = QgsFeature()
                feature.setFields(self.fields[5])
                layerPoint = QgsPointXY(point.X, point.Y)
                feature.setGeometry(QgsGeometry.fromPointXY(layerPoint))
                self.Add_values(feature, obs, self.vxConnector.LayerFieldsPovider.ObservationShapeFields)
                points.append(feature)
            
        prov.addFeatures(points)
        
        ObservationLayer.loadNamedStyle(self.plugin_dir + '\\Styles\\style_obs.qml')
        ObservationLayer.updateExtents()
        ObservationLayer.commitChanges()
        
    def show_error(self, message):
        self.iface.messageBar().pushMessage("ERROR: " + message, level=Qgis.Critical)

    def show_warning(self, message):
        self.iface.messageBar().pushMessage(message, level=Qgis.Warning)

    def show_info(self, message):
        self.iface.messageBar().pushMessage(message, level=Qgis.Info)
        
    def check_if_connected(self):
        if self.vxConnector.IsConnected == 1:
            self.show_info(self.tr("Connected!"))
        else :
        	self.show_error(self.tr("The connection has not been established"))
        	
    def DownloadVxData(self):
        
        Nodes = self.vxConnector.GetGisObjects(EntityType.Node)
        Sections = self.vxConnector.GetGisObjects(EntityType.Section)
        Observations = self.vxConnector.GetGisObjects(EntityType.SectionObservation)
        NodeObservations = self.vxConnector.GetGisObjects(EntityType.NodeObservation)
        Inspections = self.vxConnector.GetGisObjects(EntityType.SectionInspection)
        NodeInspections = self.vxConnector.GetGisObjects(EntityType.NodeInspection)

        self.draw_Nodes(Nodes)
        self.draw_Sections(Sections)
        self.draw_Observations(Observations)
        self.draw_NodeObservations(NodeObservations)
        self.draw_Inspections(Inspections)
        self.draw_NodeInspections(NodeInspections)
            
        
        canvas = self.iface.mapCanvas()
        canvas.zoomToFullExtent()
        
        self.UpdateProject(self.vxConnector.Project)
        
    def connect_pushed(self):

        self.check_if_connected()
        if self.vxConnector.IsConnected and self.i==0:  
                if not self.layers_created:
                    self.create_layers(self.vxConnector.Project.CoordinateSystem)
                self.DownloadVxData()
                self.dlg.pushButton_2.setEnabled(True)
                self.dlg.reinitialize.setEnabled(True)
                self.i += 1
            
    def ToVX(self):
        TransferToWinCan.Transfer(self)
         
    def ClearVXData(self):
        for layer in self.iface.mapCanvas().layers():
            listOfIds = [feat.id() for feat in layer.getFeatures()]
            layer.dataProvider().deleteFeatures( listOfIds )

    def ReinitializeConnection(self):
        
        self.ClearVXData()
        self.vxConnector.StopCommunication()
        self.vxConnector.StartCommunication()
        

    def SelectFeature(self,feature, layer):
        
        mc = self.iface.mapCanvas()
        for l in mc.layers():
            if l.type() == l.VectorLayer:
                    l.removeSelection()
        request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], layer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % feature.Id)
        features = layer.getFeatures(request)
        for f in features:
            layer.select(f.id())
        box = layer.boundingBoxOfSelected()
        mc.setExtent(box)
        mc.refresh()
        
    def EntitySelectedInVx(self, source, args):
        
        gisObj = self.vxConnector.GetGisObject(args.EntityId, args.EntityType)
        
        if args.EntityType == 0:
            self.SelectFeature(gisObj, self.created_layers[1])
        elif args.EntityType == 3:                          
            self.SelectFeature(gisObj, self.created_layers[2])

    def run(self):
          
        if self.first_start == True:
            vxConnector = self.vxConnector
            vxConnector.UpdateReady += EventHandler(self.UpdateVxData)
            vxConnector.DeletedEntites += EventHandler(self.OnDeletedEntites)
            vxConnector.EntitySelectedInVx += EventHandler(self.EntitySelectedInVx)
            self.vxConnector.StartCommunication()
            self.first_start = False
            self.dlg = VXDialog()
            self.dlg.button_box.button(QDialogButtonBox.Ok).setIcon((QIcon(self.plugin_dir + "\\Icons\\OK.png")))
            self.dlg.button_box.button(QDialogButtonBox.Ok).setIconSize(QtCore.QSize(16, 16))
            self.dlg.button_box.button(QDialogButtonBox.Cancel).setIcon((QIcon(self.plugin_dir + "\\Icons\\cancel.png")))
            self.dlg.button_box.button(QDialogButtonBox.Cancel).setIconSize(QtCore.QSize(16, 16))
            self.mapping = Second_window()
            self.dlg.pushButton.clicked.connect(self.connect_pushed)
            self.dlg.pushButton_2.clicked.connect(self.ToVX)
#             self.dlg.reinitialize.clicked.connect(self.ReinitializeConnection)
            self.dlg.reinitialize.clicked.connect(self.test)

        
        self.dlg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) 
        self.dlg.show()

        result = self.dlg.exec_()
             
        
        if result:
            pass
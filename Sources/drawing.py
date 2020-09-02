import clr
import os
from datetime import datetime

clr.AddReference("CDLAB.WinCan.MQ")

from PyQt5.QtCore import QCoreApplication, QVariant, pyqtSignal, pyqtSlot, QObject

from qgis.core import QgsCoordinateReferenceSystem,\
                      QgsVectorFileWriter,\
                      QgsFeatureRequest,\
                      QgsVectorLayer,\
                      QgsGeometry, \
                      QgsWkbTypes,\
                      QgsPointXY, \
                      QgsFeature, \
                      QgsProject, \
                      QgsFields, \
                      QgsField    

from CDLAB.WinCan.SDK.GIS import EntityType, Model

class Drawing(QObject):
    wincan_layers = ["WinCan Inspections",
                     "WinCan Sections",
                     "WinCan Manholes",
                     "WinCan Manhole Inspections",
                     "WinCan Manhole Observations",
                     "WinCan Observations"]
    layers_created = False
    created_layers = []
    VX_data_cleared = pyqtSignal()
    VX_data_updated = pyqtSignal(Model.DataPackage)
    feature_selected = pyqtSignal(int, str)
    entities_deleted = pyqtSignal(list)
    
    def __init__(self, _parent, _VX, _qgis):
        super(Drawing, self).__init__()
        self.parent = _parent
        self.plugin_dir = self.parent.plugin_dir
        self.VX = _VX
        self.qgis = _qgis
        self.VX_data_cleared.connect(self.clear_data)
        self.VX_data_updated.connect(self.redraw)
        self.feature_selected.connect(self.select_feature)
        self.entities_deleted.connect(self.delete_entities)
        
    def clear_VX_data(self, source, args):
        self.VX_data_cleared.emit()
        
    def update_VX_data(self, source, args):
        package = source.GetUpdated()
        self.VX_data_updated.emit(package)
        
    def entity_selected_in_vx(self, source, args):
        self.feature_selected.emit(int(args.EntityType), str(args.EntityId))
          
    def on_deleted_entities(self, source, args):
        self.entities_deleted.emit(args.DeletedEntities)
    
    @pyqtSlot()
    def clear_data(self):
        for layer in self.qgis.mapCanvas().layers():
            if layer.name() in self.wincan_layers:
                listOfIds = [feat.id() for feat in layer.getFeatures()]
                layer.dataProvider().deleteFeatures(listOfIds)
        self.qgis.mapCanvas().refresh()
    
    @pyqtSlot(Model.DataPackage)
    def redraw(self, data):
        if not self.layers_created:
            self.create_layers()
            
        if data.IsEmpty:
            return
        else:
            if data.Nodes.Count > 0:
                self.draw_Nodes(data.Nodes)
            if data.Sections.Count > 0:
                self.draw_Sections(data.Sections)
            if data.Observations.Count > 0:
                self.draw_Observations(data.Observations)
            if data.NodeInspections.Count > 0:
                self.draw_NodeInspections(data.NodeInspections)
            if data.NodeObservations.Count > 0:
                self.draw_NodeObservations(data.NodeObservations)
            if data.Inspections.Count > 0:
                self.draw_Inspections(data.Inspections)
                
        canvas = self.qgis.mapCanvas()
        canvas.zoomToFullExtent()
                
    @pyqtSlot(int, str)       
    def select_feature(self, entity_type, feature_id):
        if self.VX.IsConnected and self.layers_created:
            layer = None
            if entity_type == 0:
                layer = self.created_layers[1]
            elif entity_type == 3:
                layer = self.created_layers[2]
            if layer != None:
                mc = self.qgis.mapCanvas()
                for l in mc.layers():
                    if l.type() == l.VectorLayer:
                        l.removeSelection()
                request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], layer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % feature_id)
                features = layer.getFeatures(request)

                for f in features:
                    layer.select(f.id())

                box = layer.boundingBoxOfSelected()
                mc.setExtent(box)
                mc.refresh()
                
    @pyqtSlot(list)
    def delete_entities(self, entities):
        sections = [entity for entity in entities if entity.EntityType == 0]
        nodes = [entity for entity in entities if entity.EntityType == 3]
        inspections = [entity for entity in entities if entity.EntityType == 1]
        observations = [entity for entity in entities if entity.EntityType == 2]
        nodeInspections = [entity for entity in entities if entity.EntityType == 5]
        nodeObservations = [entity for entity in entities if entity.EntityType == 6]

        self.delete_features(sections, self.created_layers[1])
        self.delete_features(nodes, self.created_layers[2])
        self.delete_features(inspections, self.created_layers[0])
        self.delete_features(observations, self.created_layers[5])
        self.delete_features(nodeInspections, self.created_layers[3])
        self.delete_features(nodeObservations, self.created_layers[4])
        self.qgis.mapCanvas().refresh()
                                       
    def get_selected(self):
        count = 0
        selected_shapes = []
        layer = self.qgis.activeLayer()
        if type(layer) is not type(None):
            for feature in layer.selectedFeatures():
                count += 1
                selected_shapes.append(feature)
        return count, selected_shapes, layer
    
    def draw_Inspections(self, Inspections):
        QCoreApplication.processEvents()
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
            self.add_values(
                feature, ins, self.VX.LayerFieldsPovider.InspectionShapeFields)
            inspections.append(feature)

        prov.addFeatures(inspections)
        InspectionLayer.updateExtents()
        InspectionLayer.commitChanges()
        QCoreApplication.processEvents()

    def draw_Sections(self, Sections):
        QCoreApplication.processEvents()
        nr = 1
        sections = []
        SectionLayer = self.created_layers[1]
        SectionLayer.startEditing()
        prov = SectionLayer.dataProvider()
        points = []

        if SectionLayer == None:
            return

        for section in Sections:

            if section.ExternalItemId != 0:
                request = QgsFeatureRequest().setSubsetOfAttributes(
                    ["OBJ_PK"], SectionLayer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % section.Id)
                features = SectionLayer.getFeatures(request)
                for f in features:
                    for value in self.VX.LayerFieldsPovider.SectionShapeFields:
                        attr = SectionLayer.fields().indexFromName(str(value.Key))
                        SectionLayer.changeAttributeValue(
                            f.id(), attr, str(section.GetValue(value)))
            else:
                points = []
                feature = QgsFeature()
                feature.setFields(self.fields[1])
                for point in section.Vertices:
                    points.append(QgsPointXY(point.X, point.Y))
                feature.setGeometry(QgsGeometry.fromPolylineXY(points))
                self.add_values(
                    feature, section, self.VX.LayerFieldsPovider.SectionShapeFields)
                sections.append(feature)
                section.ExternalItemId = nr
                nr += 1

        if points != []:
            prov.addFeatures(sections)
            SectionLayer.loadNamedStyle(
                self.plugin_dir + '\\Styles\\style_section.qml')

        SectionLayer.updateExtents()
        SectionLayer.commitChanges()
        QCoreApplication.processEvents()

    def draw_Nodes(self, Nodes):
        QCoreApplication.processEvents()
        nr = 1
        points = []
        NodeLayer = self.created_layers[2]
        NodeLayer.startEditing()
        prov = NodeLayer.dataProvider()

        if NodeLayer == None:
            return

        for node in Nodes:

            if node.ExternalItemId != 0:
                request = QgsFeatureRequest().setSubsetOfAttributes(
                    ["OBJ_PK"], NodeLayer.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % node.Id)
                features = NodeLayer.getFeatures(request)
                for f in features:
                    for value in self.VX.LayerFieldsPovider.NodeShapeFields:
                        attr = NodeLayer.fields().indexFromName(str(value.Key))
                        NodeLayer.changeAttributeValue(
                            f.id(), attr, str(node.GetValue(value)))
            else:
                point = node.Centroid
                feature = QgsFeature()
                feature.setFields(self.fields[2])
                if (type(point) != type(None)):
                    layerPoint = QgsPointXY(point.X, point.Y)
                    feature.setGeometry(QgsGeometry.fromPointXY(layerPoint))
                self.add_values(
                    feature, node, self.VX.LayerFieldsPovider.NodeShapeFields)
                points.append(feature)
                node.ExternalItemId = nr
                nr += 1

        if points != []:
            prov.addFeatures(points)
            NodeLayer.loadNamedStyle(
                self.plugin_dir + '\\Styles\\style_node.qml')

        NodeLayer.updateExtents()
        NodeLayer.commitChanges()
        QCoreApplication.processEvents()

    def draw_NodeInspections(self, NodeInspections):
        QCoreApplication.processEvents()
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
            self.add_values(
                feature, Nodeins, self.VX.LayerFieldsPovider.NodeInspectionShapeFields)
            nodeinspection.append(feature)

        prov.addFeatures(nodeinspection)
        NodeInspectionLayer.updateExtents()
        NodeInspectionLayer.commitChanges()
        QCoreApplication.processEvents()

    def draw_NodeObservations(self, NodeObservation):
        QCoreApplication.processEvents()
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
                self.add_values(
                    feature, Nodeobs, self.VX.LayerFieldsPovider.NodeObservationShapeFields)
                points.append(feature)

        prov.addFeatures(points)

        NodeObservationLayer.loadNamedStyle(
            self.plugin_dir + '\\Styles\\style_NodeObs.qml')
        NodeObservationLayer.updateExtents()
        NodeObservationLayer.commitChanges()
        QCoreApplication.processEvents()

    def draw_Observations(self, Observations):
        QCoreApplication.processEvents()
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
                self.add_values(
                    feature, obs, self.VX.LayerFieldsPovider.ObservationShapeFields)
                points.append(feature)

        prov.addFeatures(points)

        ObservationLayer.loadNamedStyle(
            self.plugin_dir + '\\Styles\\style_obs.qml')
        ObservationLayer.updateExtents()
        ObservationLayer.commitChanges()
        QCoreApplication.processEvents()

    def add_values(self, feature, entity, shapefields):
        for attribute in feature.fields():
            for value in shapefields:
                attr = feature.fieldNameIndex(value.Key)
                feature.setAttribute(attr, str(entity.GetValue(value)))
                
    def create_layers(self):
        inspection_layer_name = self.wincan_layers[0]
        section_layer_name = self.wincan_layers[1]
        node_layer_name = self.wincan_layers[2]
        node_nspection_layer_name = self.wincan_layers[3]
        node_observation_layer_name = self.wincan_layers[4]
        observation_layer_name = self.wincan_layers[5]
        
        date = datetime.now()
        layers_path = self.VX.Project.Path + \
            "\\Misc\\Exchange\\QGIS\\Layers" + date.strftime("%d_%m_%Y")
        try:
            os.makedirs(layers_path)
        except FileExistsError:
            pass

        WKT = self.get_coordinate_system()
        if WKT == "WKT:UNKNOWN":
            EPSG = QgsCoordinateReferenceSystem()
        else:
            EPSG = QgsCoordinateReferenceSystem.fromEpsgId(int(WKT.split("\"")[-2]))
        LFP = self.VX.LayerFieldsPovider
        ShapeFields = [LFP.InspectionShapeFields, LFP.SectionShapeFields, LFP.NodeShapeFields,
                       LFP.NodeInspectionShapeFields, LFP.NodeObservationShapeFields, LFP.ObservationShapeFields]
        self.fields = []
        nr = 0

        for layer in self.wincan_layers:
            layer_full_path = layers_path + "\\" + layer + ".shp"
            self.fields.append(self.get_qgis_fields(ShapeFields[nr]))
            if (layer == node_layer_name or layer == node_observation_layer_name or layer == observation_layer_name):
                QgsVectorFileWriter(layer_full_path,
                                    "UTF-8",
                                    self.get_qgis_fields(ShapeFields[nr]),
                                    QgsWkbTypes.Point,
                                    EPSG,
                                    "ESRI Shapefile")
            if (layer == inspection_layer_name or layer == node_nspection_layer_name or layer == section_layer_name):
                QgsVectorFileWriter(layer_full_path,
                                    "UTF-8",
                                    self.get_qgis_fields(ShapeFields[nr]),
                                    QgsWkbTypes.LineString,
                                    EPSG,
                                    "ESRI Shapefile")
            temp = QgsVectorLayer(layer_full_path, layer, 'ogr')
            self.created_layers.append(temp)
            nr += 1

        QCoreApplication.processEvents()
        QgsProject.instance().addMapLayers(self.created_layers)
        self.layers_created = True

    def delete_features(self, to_delete, feature_class):
        if feature_class is None:
            return
        else:
            feature_class.startEditing()
            for entity in to_delete:
                request = QgsFeatureRequest().setSubsetOfAttributes(["OBJ_PK"], feature_class.fields()).setFilterExpression('"OBJ_PK"=\'%s\'' % entity.Id)
                for f in feature_class.getFeatures(request):
                    feature_class.deleteFeature(f.id())
            feature_class.updateExtents()
            feature_class.commitChanges()
        
    def get_coordinate_system(self):
        return self.VX.Project.CoordinateSystem
                          
    def get_qgis_fields(self, fields):
        names = QgsFields()
        for field in fields:
            type = self.to_QGIS_type(field.Type)
            names.append(QgsField(field.Key, type))
        return names

    def to_QGIS_type(self, VXType):
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
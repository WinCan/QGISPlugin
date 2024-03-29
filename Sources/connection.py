import clr
import sys
import os
import uuid
import time
import subprocess
from ctypes import windll
from System import EventHandler

vx_assembly_path = os.environ["ProgramFiles(x86)"] + "\\CDLAB\\Assemblies"
vx_assembly_path3 = os.environ["ProgramFiles(x86)"] + "\\CDLAB\\WinCanVX"
sys.path.append(vx_assembly_path.rstrip())
windll.LoadLibrary(vx_assembly_path + "\\libsodium.dll")
windll.LoadLibrary(vx_assembly_path3 + "\\libzmq.dll")

clr.AddReference(vx_assembly_path3 + "\\ZeroMQ")
clr.AddReference(vx_assembly_path + "\\CDLAB.WinCan.MQ.dll")
clr.AddReference(vx_assembly_path + "\\CDLAB.WinCan.SDK.GIS.dll")
clr.AddReference(vx_assembly_path + "\\CDLAB.WinCan.SDK.GIS.UI.dll")
clr.AddReference(vx_assembly_path + "\\CDLAB.WinCan.Template.dll")

import ZeroMQ
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType, EntityType

from .drawing import Drawing

class Connection():
    Project = None
    def __init__(self, _parent, _qgis):
        self.parent = _parent
        self.connection = CDLAB.WinCan.SDK.GIS.VxConnector("QGIS " + str(uuid.uuid4()), CDLAB.WinCan.SDK.GIS.ConnectedApplicationType.WinCanMap)
        self.drawing = Drawing(self.parent, self.connection, _qgis)
        self.connection.UpdateReady += EventHandler(self.drawing.update_VX_data)
        self.connection.DeletedEntites += EventHandler(self.drawing.on_deleted_entities)
        self.connection.EntitySelectedInVx += EventHandler(self.drawing.entity_selected_in_vx)
        self.connection.VxDataCleared += EventHandler(self.drawing.clear_VX_data)
        self.connection.ReinitializeRequired += EventHandler(self.restart_connection)

    def is_VX_enabled(self):
        processes = subprocess.Popen('tasklist', stdout=subprocess.PIPE).communicate()[0]
        return b'WinCanVX.exe' in processes

    def stop_connection(self):
        if self.connection.IsConnected:
            self.connection.StopCommunication()
            self.parent.update_project_label()

    def start_connection(self):
        self.connection.StartCommunication()

    def restart_connection(self):
        self.stop_connection()
        self.start_comunication()

    def connect_with_VX(self):
        connection_retry_cnt = 0
        while not self.connection.IsConnected and connection_retry_cnt < 10:
            self.start_connection()
            time.sleep(1)
            connection_retry_cnt += 1
        if connection_retry_cnt == 10 and not self.connection.IsConnected:
            self.parent.show_error(self.parent.tr("Timeout - Connection error after 10 attempts. Please make sure that WinCan VX is started."))

    def look_for_project(self):
        project_receive_cnt = 0
        while not self.is_project() and project_receive_cnt < 10:
            self.start_connection()
            time.sleep(1)
            project_receive_cnt += 1
        if project_receive_cnt == 10 and not self.is_project():
            self.parent.show_warning(self.parent.tr("Project is not available! Load project in VX and try again."))

    def start_comunication(self):
        self.connected = False
        self.connect_with_VX()
        self.look_for_project()        
        if self.is_project() and self.connection.IsConnected:
            self.connected = True
        return self.connected

    def is_project(self):
        result = type(self.connection.Project) != type(None)
        if result:
            self.Project = self.connection.Project
        return result
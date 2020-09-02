import time
import os.path
import traceback
import subprocess
from datetime import datetime
from System.Threading import SynchronizationContext

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QTimer, QVariant, QThread
from PyQt5.QtWidgets import QAction, QWidget, QTableWidgetItem, QDialogButtonBox, QToolBar
from PyQt5.QtGui import QIcon
from qgis.core import Qgis, QgsVectorLayer, QgsProject, QgsFields, QgsField, QgsVectorFileWriter, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsFeature, QgsPointXY, QgsGeometry, QgsPalLayerSettings, QgsFeatureRequest

from .resources import *
from .Sources.connection import Connection
from .Sources.transfer import Transfer
from .Dialogs.VX_integration_dialog import VXDialog
from .Dialogs.Second_window_dialog import Second_window

import ZeroMQ
from CDLAB.WinCan.SDK.GIS import ConnectedApplicationType
import CDLAB.WinCan.MQ
import CDLAB.WinCan.SDK.GIS.UI
import CDLAB.WinCan.Template

class Plugin_main:
    def __init__(self, _qgis):
        SynchronizationContext.SetSynchronizationContext(SynchronizationContext())

        self.qgis = _qgis
        self.plugin_dir = os.path.dirname(__file__)   
        self.menu = self.tr(u'&WinCan VX integration')
        self.set_translator()        
        self.VX = Connection(self, self.qgis)
        self.main_window = VXDialog()
        self.transfer = Transfer(self, self.VX.connection, self.qgis)
        
        self.main_window.connect_button.clicked.connect(self.connect_pushed)
        self.main_window.to_VX_button.clicked.connect(self.transfer.Transfer)
        self.main_window.reinitialize_button.clicked.connect(self.VX.restart_connection)
        self.main_window.button_box.button(QDialogButtonBox.Close).setIcon((QIcon(self.plugin_dir + "\\Icons\\OK.png")))
        self.main_window.button_box.button(QDialogButtonBox.Close).setIconSize(QtCore.QSize(16, 16))

    def set_translator(self):
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
     
    def tr(self, message):
        """Get the translation for a string using Qt translation API. """

        return QCoreApplication.translate('VX', message)

    def add_action(
            self,
            icon_path,
            text,
            callback=False,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None,
            checkable=False):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        if callback:
            action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if checkable is True:
            action.setCheckable(True)
            action.toggled.connect(self.connect_pushed)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:

            self.toolbar.addAction(action)

        if add_to_menu:
            self.qgis.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        self.toolbar = self.qgis.addToolBar("VX integration")
        self.actions = []
        if self.VX.is_VX_enabled():
            icon_path = self.plugin_dir + "\\Icons\\icon.png"
            self.add_action(
                icon_path,
                text=self.tr(u'Open dialog'),
                callback=self.run,
                parent=self.qgis.mainWindow())

            icon_path = self.plugin_dir + "\\Icons\\connect.png"
            self.add_action(
                icon_path,
                text=self.tr(u'Connect!'),
                callback=self.connect_pushed,
                parent=self.qgis.mainWindow(),
                checkable=True)

            icon_path = self.plugin_dir + "\\Icons\\transfer.png"
            self.add_action(
                icon_path,
                text=self.tr(u'Transfer to WinCan VX'),
                callback=self.transfer.Transfer,
                enabled_flag=False,
                parent=self.qgis.mainWindow())

            icon_path = self.plugin_dir + "\\Icons\\reinitialize.png"
            self.add_action(
                icon_path,
                text=self.tr(u'Reinitialize connection'),
                callback=self.VX.restart_connection,
                enabled_flag=False,
                parent=self.qgis.mainWindow())

        else:
            icon_path = self.plugin_dir + "\\Icons\\restart.png"
            self.add_action(
                icon_path,
                text=self.tr(
                    u'ERROR: VX not started - Start VX and restart QGIS'),
                enabled_flag=False,
                parent=self.qgis.mainWindow())

        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.qgis.removePluginMenu(
                self.tr(u'&WinCan VX integration'),
                action)
        del self.toolbar

        if self.first_start != True:
            pass

    def update_project_label(self, project=None):
        if type(project) != type(None):
            self.main_window.textBrowser.setText(str(project.Key))
        else:
            self.main_window.textBrowser.setText(self.tr("Disconnected"))

    def show_error(self, message):
        self.qgis.messageBar().pushMessage("ERROR: " + message, level=Qgis.Critical)

    def show_warning(self, message):
        self.qgis.messageBar().pushMessage(message, level=Qgis.Warning)

    def show_info(self, message):
        self.qgis.messageBar().pushMessage(message, level=Qgis.Info)
            
    def turn_buttons_on(self):
        self.main_window.to_VX_button.setEnabled(True)
        self.main_window.reinitialize_button.setEnabled(True)
        self.actions[2].setEnabled(True)
        self.actions[3].setEnabled(True)
        self.actions[1].setChecked(True)

    def turn_buttons_off(self):
        self.main_window.to_VX_button.setEnabled(False)
        self.main_window.reinitialize_button.setEnabled(False)
        self.actions[2].setEnabled(False)
        self.actions[3].setEnabled(False)
        self.actions[1].setChecked(False)

    def connect_pushed(self, checked):
        if checked:
            self.show_info(self.tr("Connecting... Please wait!"))
            if self.VX.start_comunication():
                self.show_info(self.tr("Connected!"))
                self.update_project_label(self.VX.Project)
                self.turn_buttons_on()
        else:
            self.turn_buttons_off()
            self.VX.stop_connection()
            
    def run(self):
        self.main_window.show()
        self.main_window.exec_()

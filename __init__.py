import sys
import os.path
try:
    import clr
except ImportError:
    raise ImportError('Please install pythonnet!')
from ctypes import windll
from .main import Plugin_main
try:
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
except OSError:
    raise OSError('Please install WinCan VX!')

def classFactory(_qgis):
    return Plugin_main(_qgis)
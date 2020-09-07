import sys
import os.path
try:
    import clr
except ImportError:
    raise ImportError('Please install pythonnet!')
from ctypes import windll
from .main import Plugin_main
try:
    vx_assembly_path = os.environ["ProgramFiles(x86)"] + "\CDLAB\Assemblies"
    sys.path.append(vx_assembly_path.rstrip())
    windll.LoadLibrary(vx_assembly_path + "\libsodium.dll")
    clr.AddReference("ZeroMQ")
    clr.AddReference("CDLAB.WinCan.MQ")
    clr.AddReference("CDLAB.WinCan.SDK.GIS")
    clr.AddReference("CDLAB.WinCan.SDK.GIS.UI")
    clr.AddReference("CDLAB.WinCan.Template")
except OSError:
    raise OSError('Please install WinCan VX!')

def classFactory(_qgis):
    return Plugin_main(_qgis)
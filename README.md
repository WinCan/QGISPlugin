Plugin depends on a following stuff:
- pythonnet
- WinCan VX used to be installed on system

___
***Install pythonnet on QGIS***
1. Run QGIS as Administator
2. Run QGIS PythonConsole
3. Install pythonnet
```
from pip._internal import main as pipmain; pipmain(['install', 'pythonnet'])
```
___
***Download WinCan_QGISPlugin***

We use Git Large File Storage for storing some icons, libraries etc. 
```
git clone git@github.com:WinCan/QGISPlugin.git
git lfs install
git lfs pull
```

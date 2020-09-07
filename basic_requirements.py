

def show_progress(count, block_size, total_size):
    print("Downloaded: {:.2f} %".format(100*count*block_size/total_size))

import time
import os
import subprocess
import urllib.request
try:
    import ssl
except ImportError:
    url = "https://slproweb.com/download/Win32OpenSSL-1_1_1g.msi"
    path = os.getcwd() + "\Win32OpenSSL-1_1_1g.msi"
    urllib.request.urlretrieve(url, path, show_progress)
    os.system('msiexec /i %s /qn' % path)
try:
    import clr
except ImportError:
    subprocess.check_call(['python', '-m', 'pip', 'install', 'pythonnet'])
    
    
    
try:
    import ssl
    import clr
    print("Ready to use plugin!")
except ImportError:
    print("An error occured!")

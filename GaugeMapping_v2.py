import arcpy, os, sys, requests, logging, errno, datetime

cwd = os.getcwd()
clone_env = os.path.join(cwd,'Packages')
sys.path.append(clone_env)

import pandas as pd
import fiona
import geopandas as gpd
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension('3D')

arcpy.env.overwriteOutput = True

from utils_v2 import (
    paths, 
    createFolder, 
    log_message,
    dir_file, 
    log_setup,
    bld_FLDs,
    xsRAS,
    depthRAS,
    fpPOLY)

root = arcpy.GetParameterAsText(0)
XS = arcpy.GetParameterAsText(1)
profile_string= arcpy.GetParameterAsText(2)
profile_list = profile_string.split(';')

try:
    Folders = bld_FLDs(root)
except (Exception, OSError) as e:
    arcpy.AddError('Encountered the following while mapping folder paths: {}'.format(e))

# Close and reinitialize logging handlers to release file handles
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

#Logging level specified in script configuration
log_folder = paths(Folders[5],'GeoProcess_Logs')
createFolder(log_folder)
log_file_name = 'GaugeMapping_Logs_'+str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
log_file_path = paths(log_folder,log_file_name)
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log_message('Folder paths built{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))

for profile in profile_list:
    xs_raster = xsRAS(Folders[9],XS,profile,Folders[2])
    log_message('XS TIN to raster module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.ResetEnvironments()
    if xs_raster[1] == '':
        log_message('Script encountered process error - input raster for depth grid module does not exist\nTool terminating prematurely'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
        arcpy.AddWarning(('Script encountered process error - input raster for depth grid module does not exist\nTool terminating prematurely'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")))))
        sys.exit()
    depth_grid = depthRAS(xs_raster[1],Folders[9],profile,Folders[2])
    log_message('Depth grid module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.ResetEnvironments()
    if depth_grid[1] == '':
        log_message('Script encountered process error - input raster for floodplain polygon module does not exist\nTool terminating prematurely'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
        arcpy.AddWarning(('Script encountered process error - input raster for floodplain polygon module does not exist\nTool terminating prematurely'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")))))
        sys.exit()
    fpPOLY(depth_grid[1],Folders[9],profile,Folders[2])
    log_message('Floodplain polygon module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))






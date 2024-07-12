import arcpy, os, sys, requests, logging, errno, datetime

cwd = os.getcwd()
clone_env = os.path.join(cwd,'Packages')
sys.path.append(clone_env)

import fiona
import geopandas as gpd
import pandas as pd
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
    final_flood,
    DG_ras,
    EG_ras)

root = arcpy.GetParameterAsText(0)
Clipping_Area = arcpy.GetParameterAsText(1)
Site_Name = arcpy.GetParameterAsText(2)

#### ------------- SQL Filters ------------- ####

fp = 'Shape_Area >= 5000'

#### --------------------------------------- ####

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
log_file_name = 'Deliverable_Logs_'+str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
log_file_path = paths(log_folder,log_file_name)
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log_message('Folder paths built{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))

final_flood(Folders[9],Folders[8],Clipping_Area,Site_Name,fp)
log_message('Deliverable floodplain module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
arcpy.ResetEnvironments()

DG_ras(Folders[9],Folders[8],Folders[2],Site_Name)
log_message('Deliverable Depth Grid module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
arcpy.ResetEnvironments()

EG_ras(Folders[9],Folders[8],Folders[2],Site_Name)
log_message('Deliverable Elevation Grid module is complete{0}\n------------------------------------------------'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
arcpy.ResetEnvironments()
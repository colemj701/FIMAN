import arcpy, os, sys, requests, logging, errno, datetime, time, argparse, pathlib

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

env_settings_list = [
    "compression",
    "resamplingMethod",
    "nodata",
    "cellSize",
    "cellSizeProjectionMethod",
    "cellAlignment",
    "pyramid",
    "snapRaster"
]

def env(x):
    arcpy.env.workspace = x
    return arcpy.env.workspace

def paths(x,y):
    path = os.path.join(x,y)
    return path

def log_message(mes):
    arcpy.AddMessage(mes)
    logging.info(mes)

def createFolder(folderPath):
    if not os.path.exists(folderPath):
        try:
            os.makedirs(folderPath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

#Logging level specified in script configuration
def dir_file(out_ras):
    directory, filename = os.path.split(out_ras)

    if directory.endswith('.gdb'):
        gp_dir = os.path.abspath(os.path.dirname(directory))
    else:
        gp_dir = directory

    return directory, filename, gp_dir

def bld_FLDs(root_fld):
    folder_dict = {
        0:'01_Effective Data',
        1:'02_Working Model',
        2:'DEM01',
        3:'03_Supporting Data',
        4:'04_Final',
        5:'05_GIS',
        6:'WSEL',
        7:'Working_DEM',
        8:'Final.gdb',
        9:'Temp.gdb'
    }

    for root, dirs, files in os.walk(root_fld):
        for directory in dirs:
            dir_path = paths(root,directory)
            base = os.path.join(directory)
            for key, value in folder_dict.items():
                if value == base:
                    folder_dict[key] = dir_path
    return folder_dict

def log_setup(dir):
    # Close and reinitialize logging handlers to release file handles
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    log_folder = paths(dir,'GeoProcess_Logs')
    createFolder(log_folder)
    log_file_name = 'Mosaic_Logs_'+str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    log_file_path = paths(log_folder,log_file_name)
    log_set = logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    return log_set

def gp_env(snap):
    arcpy.env.compression = 'LZW'
    arcpy.env.resamplingMethod = 'BILINEAR'
    arcpy.env.snapRaster = snap
    arcpy.env.nodata = 'NONE'
    arcpy.env.cellAlignment = 'DEFAULT'
    arcpy.env.cellSize = 'MAXOF'
    arcpy.env.pyramid = 'PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP'
    arcpy.env.cellSizeProjectionMethod = 'CONVERT_UNITS'

def xsRAS(FLD,in_feat,Profile,pDEM):
    log_message('Initiating XS TIN to Raster module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Creating {0} WSEL raster...'.format(Profile))

    desc = arcpy.Describe(in_feat)
    spa = desc.SpatialReference
    log_message(f'Input XS spatial reference used for TIN generation  :: {spa.name}')

    try:
        TIN = arcpy.ddd.CreateTin(
            out_tin=paths(FLD,'TIN_'+Profile),
            spatial_reference=spa,
            in_features=[[in_feat,Profile,'Mass_Points','<None>']],
            constrained_delaunay='DELAUNAY'
            )
        log_message('{0} TIN successfully created\nCreating {0} WSEL raster...'.format(Profile))

    except (Exception, OSError) as e:
        log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
        arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    env(pDEM)
    snap = arcpy.ListRasters()
    snap_ras = snap[0]

    gp_env(snap_ras)
    log_message('---------------\nTIN to Raster GeoProcessing Environments  ::\n---------------')
    for setting in env_settings_list:
        value = getattr(arcpy.env,setting)  # Get the value of the setting
        log_message(f"::   {setting}: {value}")
    try:
        out_ras = arcpy.ddd.TinRaster(
            in_tin=TIN, 
            out_raster=paths(FLD,'ras1_'+Profile),
            data_type='FLOAT', 
            method='LINEAR', 
            sample_distance='CELLSIZE 10', 
            z_factor=1, 
            sample_value=10)
        ras_path = paths(FLD,'ras1_'+Profile)

        log_message('{0} WSEL raster successfully created...'.format(Profile))

    except (Exception, OSError) as e:
        log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
        arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    arcpy.SetProgressorPosition()

    return out_ras, ras_path

def depthRAS(inRAS,outGDB,Profile,pDEM):
    log_message('Initiating depth grid module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Producing {0} depth grid...'.format(Profile))
    out_mRas = None

    env(pDEM)
    snap = arcpy.ListRasters()
    snap_ras = snap[0]

    with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

        log_message('---------------\nRaster Minus GeoProcessing Environments  ::\n---------------')
        for setting in env_settings_list:
            value = getattr(arcpy.env,setting)  # Get the value of the setting
            log_message(f"::   {setting}: {value}")

        try:
            out_minusRas = arcpy.sa.Minus(inRAS, snap_ras)
            out_minusRas.save(paths(outGDB,'Minus_'+Profile))
            out_mRas = (paths(outGDB,'Minus_'+Profile))

            log_message('{0} Minus raster successfully created\nCreating {0} Extraction raster...'.format(Profile))

        except (Exception, OSError) as e:
            log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
            arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    arcpy.ResetEnvironments()
    env(pDEM)
    snap = arcpy.ListRasters()
    snap_ras = snap[0]

    with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

        log_message('---------------\nRaster Extract GeoProcessing Environments  ::\n---------------')
        for setting in env_settings_list:
            value = getattr(arcpy.env,setting)  # Get the value of the setting
            log_message(f"::   {setting}: {value}")

        try:
            extractRas = arcpy.sa.ExtractByAttributes(out_mRas, 'Value >= 0')
            extractRas.save(paths(outGDB,'Extract_Minus1_'+Profile))
            out_eRas = paths(outGDB,'Extract_Minus1_'+Profile)

            log_message('{0} Extraction raster successfully created\nCreating {0} Integer raster...'.format(Profile))


        except (Exception, OSError) as e:
            log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
            arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    arcpy.ResetEnvironments()
    env(pDEM)
    snap = arcpy.ListRasters()
    snap_ras = snap[0]

    with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

        log_message('---------------\nRaster Int GeoProcessing Environments  ::\n---------------')
        for setting in env_settings_list:
            value = getattr(arcpy.env,setting)  # Get the value of the setting
            log_message(f"::   {setting}: {value}")

        try:
            extractRas = arcpy.sa.Int(out_eRas)
            extractRas.save(paths(outGDB,'Int_Extract_1_'+Profile))
            out_eRas = paths(outGDB,'Int_Extract_1_'+Profile)

            log_message('{0} Integer raster successfully created...'.format(Profile))


        except (Exception, OSError) as e:
            log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
            arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    arcpy.SetProgressorPosition()

    return extractRas, out_eRas

def fpPOLY(inRAS,outGDB,Profile,pDEM):
    log_message('Initiating floodplain polygon module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Producing {0} floodplain polygon...'.format(Profile))
    fp_path = None
    out_fp = None

    env(pDEM)
    snap = arcpy.ListRasters()
    snap_ras = snap[0]

        # Process: Raster to Polygon (Raster to Polygon) (conversion)
    with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):
        try:
            arcpy.conversion.RasterToPolygon(
            in_raster=inRAS,
            out_polygon_features=paths(outGDB,'Raw_Poly1_'+Profile), 
            simplify="NO_SIMPLIFY",
            raster_field='Value')

            ras_fp = paths(outGDB,'Raw_Poly1_'+Profile)
            out_fp = arcpy.analysis.PairwiseDissolve(
                in_features=ras_fp,
                out_feature_class=paths(outGDB,'Raw_Floodplain_'+Profile),
                dissolve_field=None,
                statistics_fields=None,
                multi_part="MULTI_PART",
                concatenation_separator=""
                )
            fp_path = paths(outGDB,'Raw_Floodplain_'+Profile)

        except (Exception, OSError) as e:
            log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
            arcpy.AddWarning("An unexpected error occurred: {}".format(e))
        
    arcpy.ResetEnvironments()

    return out_fp, fp_path

def final_flood(inGDB,outGDB,Clip,SiteName,WhereClause):
    log_message('Initiating deliverable floodplain module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Preparing final floodplain ploygons...')

    outPOLY = None

    # Get all the layers from the FGDB
    layers = fiona.listlayers(inGDB)
    output_fld = os.path.dirname(inGDB)

    # Read each layer into a GeoDataFrame
    for layer in layers:
        arcpy.SetProgressor('default','Exploding {0} multipart feature...'.format(layer))
        if layer.startswith('Raw_Floodplain_') and layer.endswith('_exploded'):
            arcpy.Delete_management(paths(inGDB,layer))

        elif layer.startswith('Raw_Floodplain_'):
            try:
                gdf = gpd.read_file(inGDB, layer=layer)

                # Explode multi-part geometries
                exploded_gdf = gdf.explode()

                # Save the exploded features to a File Geodatabase feature class
                output_file = f'{layer}_exploded'
                output_shp = f'{layer}_exploded.shp'
                output_explode_shp = paths(output_fld,output_shp)

                exploded_gdf.to_file(f'{output_fld}/{output_file}.shp')

                arcpy.FeatureClassToGeodatabase_conversion(Input_Features=output_explode_shp, Output_Geodatabase=inGDB)
                arcpy.Delete_management(output_explode_shp)

                log_message('{0} floodplain polygon successfully created...'.format(output_file))

            except (Exception, OSError) as e:
                log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
                arcpy.AddWarning("An unexpected error occurred: {}".format(e))

        else:
            pass

    log_message('Multipart floodplain polygon features successfully exploded...{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
        # Now you can work with the GeoDataFrame (e.g., explore attributes, plot, analyze)

    env(inGDB)

    explode_list = arcpy.ListFeatureClasses('*_exploded')

    for fc in explode_list:
        desc = arcpy.Describe(fc)
        desc_name = desc.name
        prefix = 'FP_'+SiteName+'_'
        desc_name = desc_name.replace('_exploded','')
        newName = desc_name.replace('Raw_Floodplain_',prefix)
        arcpy.SetProgressor('default','Processing {0} to final deliverable gdb...'.format(newName))

        try:

            FL = arcpy.MakeFeatureLayer_management(
                in_features=fc, 
                out_layer='FL_FP', 
                where_clause=WhereClause)

            outPOLY = arcpy.analysis.Clip(
            in_features=FL,
            clip_features=Clip,
            out_feature_class=paths(outGDB,newName),
            cluster_tolerance=None
        )
            
            log_message('{0} Floodplain polygon successfully created...'.format(newName))
            print('{0} Floodplain polygon successfully created...'.format(newName))
            
        except (Exception, OSError) as e:
            log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
            arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    return outPOLY


def DG_ras(inGDB,outGDB,pDEM,SiteName):
    log_message('Initiating Deliverable Depth Grid module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Preparing depth grid rasters...')
    outRAS = None

    arcpy.env.workspace = env(inGDB)
    minus_list = arcpy.ListRasters('Minus_*')

    for ras in minus_list:
        rpath = paths(inGDB,ras)
        desc = arcpy.Describe(rpath)
        desc_name = desc.name
        profile = desc_name[6:]
        wildcard = '*'+profile
        DGnewName = 'DG_'+profile+'_Draft'
        DGfinalName = 'DG_'+SiteName+'_'+profile
        arcpy.SetProgressor('default','Processing {0} to final deliverable gdb...'.format(desc.name))

        env(outGDB)
        pfc = arcpy.ListFeatureClasses(wildcard)
        pfc_path = paths(outGDB,pfc[0])

        env(pDEM)
        snap = arcpy.ListRasters()
        snap_ras = snap[0]

        with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

            log_message('---------------\nRaster Minus Clip GeoProcessing Environments  ::\n---------------')
            for setting in env_settings_list:
                value = getattr(arcpy.env,setting)  # Get the value of the setting
                log_message(f"::   {setting}: {value}")

            try:
                arcpy.management.Clip(
                    in_raster=rpath,
                    rectangle=None,
                    out_raster=paths(inGDB,DGnewName),
                    in_template_dataset=pfc_path,
                    nodata_value="NoData",
                    clipping_geometry="ClippingGeometry",
                    maintain_clipping_extent="MAINTAIN_EXTENT"
                )
                clip1 = paths(inGDB,'DG_'+profile+'_Draft')

                log_message('{0} Draft DG Raster sucessfully created...'.format(DGnewName))
                print('{0} Draft DG Raster sucessfully created...'.format(DGnewName))

                arcpy.ResetEnvironments()

                env(pDEM)
                snap = arcpy.ListRasters()
                snap_ras = snap[0]

                with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

                    log_message('---------------\nConditional Raster GeoProcessing Environments  ::\n---------------')
                    for setting in env_settings_list:
                        value = getattr(arcpy.env,setting)  # Get the value of the setting
                        log_message(f"::   {setting}: {value}")

                    conRAS = arcpy.sa.Con(
                        in_conditional_raster=clip1,
                        in_true_raster_or_constant=0.1,
                        in_false_raster_or_constant=clip1,
                        where_clause='VALUE < 0.1'
                    )
                    outRAS = conRAS.save(paths(outGDB,DGfinalName))

                    log_message('{0} Final DG Raster sucessfully created...'.format(DGfinalName))
        
            except (Exception, OSError) as e:
                print(e)
                log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
                arcpy.AddWarning("An unexpected error occurred: {}".format(e))

    return outRAS

def EG_ras(inGDB,outGDB,pDEM,SiteName):
    log_message('Initiating Deliverable Elevation Grid module{0}'.format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S"))))
    arcpy.SetProgressor('default','Preparing elevation grid rasters...')
    outRAS = None

    arcpy.env.workspace = env(inGDB)
    minus_list = arcpy.ListRasters('ras1_*')

    for ras in minus_list:
        rpath = paths(inGDB,ras)
        desc = arcpy.Describe(rpath)
        desc_name = desc.name
        profile = desc_name[5:]
        wildcard = '*'+profile
        EGfinalName = 'EG_'+SiteName+'_'+profile
        arcpy.SetProgressor('default','Processing {0} to final deliverable gdb...'.format(desc.name))

        env(outGDB)
        pfc = arcpy.ListFeatureClasses(wildcard)
        pfc_path = paths(outGDB,pfc[0])
        log_message('Cliiping floodplain : {}'.format(pfc_path))

        env(pDEM)
        snap = arcpy.ListRasters()
        snap_ras = snap[0]

        with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

            log_message('---------------\nRas1 Clip GeoProcessing Environments  ::\n---------------')
            for setting in env_settings_list:
                value = getattr(arcpy.env,setting)  # Get the value of the setting
                log_message(f"::   {setting}: {value}")

            try:
                arcpy.management.Clip(
                    in_raster=rpath,
                    rectangle=None,
                    out_raster=paths(outGDB,'Clip_' + profile),
                    in_template_dataset=pfc_path,
                    nodata_value="NoData",
                    clipping_geometry="ClippingGeometry",
                    maintain_clipping_extent="MAINTAIN_EXTENT"
                )

                log_message('{0} Elevation Clip Raster sucessfully created...'.format(EGfinalName))
                print('{0} Elevation Clip Raster sucessfully created...'.format(EGfinalName))
        
            except (Exception, OSError) as e:
                print(e)
                log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
                arcpy.AddWarning("An unexpected error occurred: {}".format(e))

        with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled", snapRaster = snap_ras, cellSize=10):

            log_message('---------------\nResampling GeoProcessing Environments  ::\n---------------')
            for setting in env_settings_list:
                value = getattr(arcpy.env,setting)  # Get the value of the setting
                log_message(f"::   {setting}: {value}")

            try:
                fras_path = paths(outGDB,'Clip_' + profile)

                outRAS = arcpy.management.Resample(
                    in_raster=fras_path, 
                    out_raster = paths(outGDB,EGfinalName), 
                    cell_size = 10, 
                    resampling_type = 'BILINEAR')
                
                log_message('{0} Final Elevation EG Raster sucessfully created...'.format(EGfinalName))
                print('{0} Final Elevation EG Raster sucessfully created...'.format(EGfinalName))
        
            except (Exception, OSError) as e:
                print(e)
                log_message("A process error occurred{0} \n{1}".format('  ::  '+str(datetime.now().strftime("%Y-%m-%d @ %H:%M:%S")),e))
                arcpy.AddWarning("An unexpected error occurred: {}".format(e))

        arcpy.Delete_management(fras_path)

    return outRAS
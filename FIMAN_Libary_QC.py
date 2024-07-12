import arcpy
import re

File_GDB_Location = arcpy.GetParameterAsText(0)
MappingGDB = arcpy.GetParameterAsText(1)

#Create FIMAN_Comment.gdb
arcpy.CreateFileGDB_management(File_GDB_Location, "FIMAN_Comment.gdb", "CURRENT")
commentDB = File_GDB_Location + "\\FIMAN_Comment.gdb"

# Process: Create FIMAN_Comments
arcpy.CreateFeatureclass_management(commentDB, "FIMAN_Comments", "POLYGON", "", "DISABLED", "DISABLED", "{B286C06B-0879-11D2-AACA-00C04FA33C20};IsHighPrecision", "", "0", "0", "0")

FIMAN_Comments1 = commentDB + "\\FIMAN_Comments"

arcpy.AddField_management(FIMAN_Comments1, "SOURCE", "TEXT", "", "", "50", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(FIMAN_Comments1, "COMMENT", "TEXT", "", "", "255", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(FIMAN_Comments1, "RESPONSE", "TEXT", "", "", "255", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(FIMAN_Comments1, "DRAFT", "TEXT", "", "", "5", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.DefineProjection_management(FIMAN_Comments1, "PROJCS['NAD_1983_StatePlane_North_Carolina_FIPS_3200_Feet',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Lambert_Conformal_Conic'],PARAMETER['False_Easting',2000000.002616666],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-79.0],PARAMETER['Standard_Parallel_1',34.33333333333334],PARAMETER['Standard_Parallel_2',36.16666666666666],PARAMETER['Latitude_Of_Origin',33.75],UNIT['Foot_US',0.3048006096012192]],VERTCS['NAVD_1988',VDATUM['North_American_Vertical_Datum_1988'],PARAMETER['Vertical_Shift',0.0],PARAMETER['Direction',1.0],UNIT['Foot_US',0.3048006096012192]]")

arcpy.env.workspace = MappingGDB

#read list of inundation polygons
InundationList = arcpy.ListFeatureClasses(feature_type= 'Polygon')

#extract elevation by keeping letters after the second occurence of '_', replacing '_' with '.'

ele = [float(e.split('_',3)[3].replace('_','.')) for e in InundationList]
arcpy.AddMessage('Elevation list items: {}'.format(ele))

#sort InundationList based on sorted elevation
ele,InundationList = zip(*sorted(zip(ele,InundationList)))


for i in range(len(InundationList)-1):
#    print(InundationList[i], InundationList[i+1])
    arcpy.analysis.Erase(InundationList[i],InundationList[i+1],commentDB+"\\ER_"+InundationList[i])

    arcpy.management.AddFields(commentDB+"\\ER_"+InundationList[i],[["SOURCE", "TEXT", "", "50", ""],
                                                                    ["COMMENT", "TEXT", "", "255", ""],
                                                                    ["RESPONSE", "TEXT", "", "255", ""],
                                                                    ["DRAFT", "TEXT", "", "5", ""]])

    arcpy.management.CalculateField(commentDB+"\\ER_"+InundationList[i],'SOURCE','"{}"'.format(InundationList[i]))
    arcpy.management.CalculateField(commentDB+"\\ER_"+InundationList[i],'COMMENT','"{} library polygon extents are greater than {}"'.format(InundationList[i],InundationList[i+1]))
    arcpy.management.Append(commentDB+"\\ER_"+InundationList[i],commentDB+"\\FIMAN_Comments",'NO_TEST')
    arcpy.AddMessage("{0} has been reviewed.".format(InundationList[i]))
    arcpy.Delete_management(commentDB+"\\ER_"+InundationList[i])

#print('finished')
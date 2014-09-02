""" This script contains the Arc modules required to running the GUI """
import os
import os.path
import arcpy
import csv
from arcpy import env
from arcpy.sa import *

class ArcFunctions:

    def init_lists(self,ws):
        """Init raster list"""
    ################################################################################
        # Sets the arc workspace to get the raster list
        env.workspace = ws
        raster_list = arcpy.ListRasters()  # glob.glob  or listdir() -- .img / GRID /  Header file search?  restrict to certain file types
        # File types:  .IMG, .BIL, .TIFF,
        return(raster_list)
    ################################################################################


    def overlay(self,raster_list,env_workspace,shape):
        """Performing overlays with ArcGIS, Extract Multi Value to Points tool"""
        print("Performing overlays")

        Fields = ""
        for raster in raster_list:
            in_raster = os.path.join(env_workspace, raster)
            fieldname = str(raster)
            item = str(in_raster+" "+fieldname+";")
            Fields += item

        Fields = Fields[:-1]


        """
    from osgeo import gdal,ogr
    import struct

    src_filename = '/tmp/test.tif'
    shp_filename = '/tmp/test.shp'

    src_ds=gdal.Open(src_filename)
    gt=src_ds.GetGeoTransform()
    rb=src_ds.GetRasterBand(1)

    ds=ogr.Open(shp_filename)
    lyr=ds.GetLayer()
    for feat in lyr:
        geom = feat.GetGeometryRef()
        mx,my=geom.GetX(), geom.GetY()  #coord in map units

        #Convert from map to pixel coordinates.
        #Only works for geotransforms with no rotation.
        #If raster is rotated, see http://code.google.com/p/metageta/source/browse/trunk/metageta/geometry.py#493
        px = int((mx - gt[0]) / gt[1]) #x pixel
        py = int((my - gt[3]) / gt[5]) #y pixel

        structval=rb.ReadRaster(px,py,1,1,buf_type=gdal.GDT_UInt16) #Assumes 16 bit int aka 'short'
        intval = struct.unpack('h' , structval) #use the 'short' format code (2 bytes) not int (4 bytes)

        print intval[0] #intval is a tuple, length=1 as we only asked for 1 pixel value
        """

    ################################################################################
        arcpy.CheckOutExtension("Spatial")
        ExtractMultiValuesToPoints(shape,Fields,"NONE")    #
        arcpy.CheckInExtension("Spatial")
    ################################################################################

        print("Overlays finished")
        print("---------------------------------------------------------------")



    def background(self,Output_path,resolution,raster_list,env_workspace):
        """This uses the defined resolution and creates the background grid"""


        OutGrid = os.path.join(Output_path,"background.shp")

        res = str(resolution)

        for raster in raster_list:
            raster = raster
            r = os.path.join(env_workspace,raster)
            break
    ################################################################################
        YMAX = arcpy.GetRasterProperties_management(r,"TOP")
        YMIN = arcpy.GetRasterProperties_management(r,"BOTTOM")
        XMIN = arcpy.GetRasterProperties_management(r,"LEFT")
        XMAX = arcpy.GetRasterProperties_management(r,"RIGHT")

        YOrient = float(str(YMIN)) + 10

        OriginCoord = str(XMIN)+" "+str(YMIN)
        OrientCoord = str(XMIN)+" "+str(YOrient)
        OppositeCoord = str(XMAX)+" "+str(YMAX)
        try:

            arcpy.CreateFishnet_management(OutGrid,OriginCoord,OrientCoord,res,
                                            res,"0","0",OppositeCoord,"LABELS",
                                            raster,"POLYGON")
        except:
            print arcpy.GetMessages()
        arcpy.Delete_management(OutGrid)
    ################################################################################

        self.background_points = os.path.join(Output_path,
                                            "background_label.shp")

        Fields = ""
        for raster in raster_list:
            in_raster = os.path.join(env_workspace, raster)
            fieldname = str(raster)
            item = str(in_raster+" "+fieldname+";")
            Fields += item

        Fields = Fields[:-1]
    ################################################################################
        arcpy.CheckOutExtension("Spatial")
        ExtractMultiValuesToPoints(self.background_points,Fields,"NONE")
        arcpy.AddXY_management(self.background_points)
        arcpy.CheckInExtension("Spatial")
    ################################################################################
        return(self.background_points)



    ################################################################################
    def csvwriter(self,shape,background_points,data,grid_data):
        """Export csv from ArcGIS"""
        print("Writing csv files for analysis")
        FL = []

        field_list = arcpy.ListFields(shape)
        for field in field_list:
            f = field.name
            FL.append(f)

        fields = ';'.join(FL[2:])

        FLbkgrd = []

        field_list_bkgrd = arcpy.ListFields(background_points)
        for field_bkgrd in field_list_bkgrd:
            f_bkgrd = field_bkgrd.name
            FLbkgrd.append(f_bkgrd)
        fields_bkgrd = ';'.join(FLbkgrd[2:])


        try:
            arcpy.ExportXYv_stats(shape, fields, "COMMA", data,
                                                        "ADD_FIELD_NAMES")
            arcpy.ExportXYv_stats(background_points, fields_bkgrd, "COMMA",
                                            grid_data, "ADD_FIELD_NAMES")
        except:
            print arcpy.GetMessages(2)

        print("CSV files written")
        print("---------------------------------------------------------------")


    def grid_create(self,out_Layer,gridshape,rastername,newfile,Mapdir,shape):
        """This function creates the maps for output. First it creates a new
        shapefile from the scored grids the user creates in SPM. Then the scored
        grids are interpolated using the IDW command. Next, rasters are applied
        to the Blank.mxd file provided in order to output JPEGS that are opened
        using the matplotlib."""


        env.workspace = Mapdir

        self.SpRf = arcpy.Describe(shape).spatialReference

        arcpy.CreateFeatureclass_management(Mapdir,gridshape,"POINT",
                                                            "","","",self.SpRf)
        arcpy.AddField_management(gridshape,"PROB","FLOAT")

        cursor = arcpy.InsertCursor(gridshape)

        df = DataFrame.from_csv(newfile)
        Xlocation = df.columns.get_loc("POINT_X")
        Ylocation = df.columns.get_loc("POINT_Y")
        probLoc = df.columns.get_loc("PROB_2")


        with open(newfile, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            row = reader.next()
            for row in reader:
                Row = cursor.newRow()
                point = arcpy.CreateObject("Point")
                point.X, point.Y = float(row[Xlocation+1]), float(row[Ylocation+1])
                Row.PROB = float(row[probLoc+1])
                Row.shape = point
                cursor.insertRow(Row)
        del cursor
    ################################################################################



    def map_maker(self,resolution,gridshape,SpRf,outIDWname,out_Layer,Mapdir,mxdpath,rastername):

        radius = float(resolution) * 2.5
    ################################################################################
        arcpy.CheckOutExtension("Spatial")
        print ("Creating interpolated raster file")
        #self.outIDWname = os.path.join(self.Mapdir, self.rastername)
        try:
            arcpy.DefineProjection_management(gridshape,SpRf)
            outIDW = Idw(gridshape, "PROB", resolution, 2,
                                                    RadiusFixed(radius))
            outIDW.save(outIDWname)
        except:
            print arcpy.GetMessages(2)

        print ("Interpolation complete")
        print ("------------------------------------------------------")
        arcpy.CheckInExtension("Spatial")
    ################################################################################

        print ("Creating JPEG")

        templyr = out_Layer+"_temp"
        outLYR = out_Layer+".lyr"
        ADDLYR = os.path.join(Mapdir,outLYR)
        Jname = out_Layer+".jpg"
        outJPEG = os.path.join(Mapdir,Jname)
    ################################################################################
        try:
            """To create JPEGS, all rasters must be saved as .lyr files with a
                symbology <- creates a temp layer first"""
            arcpy.MakeRasterLayer_management(rastername, templyr)
            #Saves the layer from the raster
            arcpy.SaveToLayerFile_management(templyr,outLYR,"ABSOLUTE")
            #Opens the .mxd file that was created with the layout desired
            mxd = arcpy.mapping.MapDocument(mxdpath)
            #Lists all dataframes in the mxd file.. the [0] takes the first one
            #listed
            dataf = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]
            #Adds the .lyr file to the dataframe
            addLayer = arcpy.mapping.Layer(ADDLYR)
            #Adds and arranges the .lyr file to the layout
            arcpy.mapping.AddLayer(dataf,addLayer,"AUTO_ARRANGE")
            #Exports the mxd layout with the new layer to a JPEG
            arcpy.mapping.ExportToJPEG(mxd, outJPEG)

            del mxd
        except:
            print arcpy.GetMessages()

        return outJPEG

    def getsprf(self,shape):
        sprf = arcpy.Describe(shape).spatialReference
        UnitName = sprf.angularUnitName
        return UnitName

################################################################################



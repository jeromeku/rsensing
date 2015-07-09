#!/usr/bin/env python
#Name:  ndvi.py
import auxil.auxil as auxil
from numpy import *
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly,GDT_Float32

def main(): 
    gdal.AllRegister()
    infile = auxil.select_infile() 
    if infile:                  
        inDataset = gdal.Open(infile,GA_ReadOnly)     
        cols = inDataset.RasterXSize
        rows = inDataset.RasterYSize    
        bands = inDataset.RasterCount
    else:
        return
    
    band = inDataset.GetRasterBand(3)
    band3 = band.ReadAsArray(0,0,cols,rows)
    
    
    band = inDataset.GetRasterBand(4)
    band4 = band.ReadAsArray(0,0,cols,rows)
    band4 = array(band4,dtype=float32)
    
    NDVI = (band4-band3)/(band4+band3)
    
#  write to disk       
    outfile,fmt = auxil.select_outfilefmt() 
    if outfile:
        driver = gdal.GetDriverByName(fmt)   
        outDataset = driver.Create(outfile,
                        cols,rows,1,GDT_Float32)
        projection = inDataset.GetProjection()
        geotransform = inDataset.GetGeoTransform()
        if geotransform is not None:
            outDataset.SetGeoTransform(geotransform)
        if projection is not None:
            outDataset.SetProjection(projection)              
        outBand = outDataset.GetRasterBand(1)
        outBand.WriteArray(NDVI,0,0) 
        outBand.FlushCache() 
        outDataset = None    
    inDataset = None        
 
if __name__ == '__main__':
    main()    
#!/usr/bin/env python
#******************************************************************************
#  Name:     c_corr.py
#  Purpose:  c-coorection algorithm for solar illunination in rough terrain
#  Usage:             
#    python c_corr.py [options] msfilename demfilename
#
#  Copyright (c) 2011, Mort Canty
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

import os, sys, getopt, time, subprocess
import numpy as np
from osgeo import gdal
import scipy.ndimage.interpolation as ndii
import scipy.stats as stats
from osgeo.gdalconst import GA_ReadOnly, GDT_Float32     

def write_band(bnd,fname,projection=None,geotransform=None): 
#  write an image band to disk   
    driver = gdal.GetDriverByName('ENVI')
    rows,cols = bnd.shape
    outDataset = driver.Create(fname,cols,rows,1,GDT_Float32)   
    if projection is not None:
        outDataset.SetProjection(projection)
    if geotransform is not None:
        outDataset.SetGeoTransform(geotransform)     
    band = outDataset.GetRasterBand(1)
    band.WriteArray(bnd,0,0) 
    band.FlushCache() 
    outDataset = None         

def main():
    usage = '''
Usage:
-----------------------------------------------------------------------
python %s [-d spatialDimensions] [-p bandPositions]  [-c classfilename]
           solarAzimuth(deg) solarElevation(deg) msfilename demfilename 

bandPositions and spatialDimensions are lists, 
e.g., -p [1,2,3] -d [0,0,400,400]

Outfile name is msfilename_corr with same format as msfilename      
-----------------------------------------------------''' %sys.argv[0]
    options, args = getopt.getopt(sys.argv[1:],'hd:p:c:')
    dims = None
    pos = None  
    classfile = None          
    for option, value in options:
        if option == '-h':
            print usage
            return 
        elif option == '-d':
            dims = eval(value) 
        elif option == '-p':
            pos = eval(value)    
        elif option == '-c':
            classfile = value
    if len(args) != 4:
        print 'Incorrect number of arguments'
        print usage
        sys.exit(1)     
    gdal.AllRegister()
    AZIMUTH = np.radians(eval(args[0]))     # solar azimuth in radians
    ZENITH = np.radians(90.0-eval(args[1])) # solar zenith in radians
    msfile = args[2]
    demfile = args[3]    
    print '-------------------------'
    print '   C-Correction'
    print '-------------------------'
    print time.asctime()     
    print 'MS  file: %s'%msfile
    print 'DEM file: %s'%demfile  
    start = time.time()  
             
    path = os.path.dirname(msfile)
    basename = os.path.basename(msfile)
    root, ext = os.path.splitext(basename)
    outfile = path+'/'+root+'_corr'+ext         
    try:                   
        msDataset = gdal.Open(msfile,GA_ReadOnly)     
        cols = msDataset.RasterXSize
        rows = msDataset.RasterYSize    
        bands = msDataset.RasterCount
    except Exception as e:
        print 'Error: %s  --MS image could not be read'%e           
    try:                   
        demDataset = gdal.Open(demfile,GA_ReadOnly)     
    except Exception as e:
        print 'Error: %s  --DEM raster could not be read'%e                
    if pos is not None:
        bands = len(pos)
    else:
        pos = range(1,bands+1)
    if dims:
        x0,y0,cols,rows = dims
    else:
        x0 = 0
        y0 = 0          
    geotransform_ms = msDataset.GetGeoTransform()
    projection_ms = msDataset.GetProjection() 
    geotransform_dem = demDataset.GetGeoTransform()   
    if (geotransform_ms is None) or (geotransform_dem is None):
        print 'Image not geo-referenced, aborting' 
        sys.exit(1)   
#  read multispectral image        
    MS = np.asarray(np.zeros((bands,rows,cols)),dtype=np.float32) 
    k = 0                                   
    for b in pos:
        band = msDataset.GetRasterBand(b)
        MS[k,:,:] = band.ReadAsArray(x0,y0,cols,rows)
        k += 1       
#  save MS NIR band to disk for co-registration with cos(gamma)
    if bands>3:
        k=3  # landsat, spot or rapideye band 4
    elif bands==3:
        k=2  # aster band 3
    else:
        k=0  # band 1    
    gt = list(geotransform_ms)
    gt[0] = gt[0] + x0*gt[1]
    gt[3] = gt[3] + y0*gt[5]       
    geotransform_ms_subset = tuple(gt)     
    write_band(MS[3,:,:],path+'/nir_band',projection_ms,geotransform_ms_subset)      
#  dem raster
    gt1 = list(geotransform_ms)               
    gt2 = list(geotransform_dem)
    ulx1 = gt1[0] + x0*gt1[1]
    uly1 = gt1[3] + y0*gt1[5]
    x20 = int(round(((ulx1 - gt2[0])/gt2[1])))
    y20 = int(round(((uly1 - gt2[3])/gt2[5])))
    ratiox = gt1[1]/gt2[1] 
    ratioy = gt1[5]/gt2[5]
    cols2 = int(round(cols*ratiox)) 
    rows2 = int(round(rows*ratioy)) 
    band = demDataset.GetRasterBand(1)
    DEM = band.ReadAsArray(x20,y20,cols2,rows2) 
    DEM = ndii.zoom(DEM, (1.0/ratiox,1/ratioy))
    demDataset = None
#  class raster
    if classfile is not None:
        print 'Class file: %s'%classfile
        classDataset =  gdal.Open(classfile,GA_ReadOnly)  
        try:     
            band = classDataset.GetRasterBand(1)
        except Exception as e:
            print 'Error: %s  --Class raster could not be read'%e
            sys.exit(1)        
        CLASS = band.ReadAsArray(0,0,cols,rows).ravel()
        classDataset = None
    else:
        CLASS = np.zeros((rows*cols), dtype=np.uint8) + 1     
    num_classes = np.max(CLASS)          
#  write dem subset to disk and calculate slope and aspect maps      
    demtmpfn = path+'/dem_temp'     
    gt2[0] += x0*ratiox  
    gt2[3] -= y0*ratioy
    gt2[1] = gt1[1]
    gt2[2] = gt1[2]
    gt2[4] = gt1[4]
    gt2[5] = gt1[5]         
    write_band(DEM,demtmpfn,projection_ms,tuple(gt2))   
    slopefn = path+'/dem_slope'
    aspectfn = path+'/dem_aspect'
    subprocess.call(['gdaldem','slope',demtmpfn,slopefn])
    subprocess.call(['gdaldem','aspect','-zero_for_flat',demtmpfn,aspectfn])
#  calculate cos(gamma)
    slopeDataset = gdal.Open(slopefn,GA_ReadOnly)
    band = slopeDataset.GetRasterBand(1)
    SLOPE = np.radians(band.ReadAsArray(0,0,cols,rows))  # terrain slope in radians
    slopeDataset = None
    aspectDataset = gdal.Open(aspectfn,GA_ReadOnly)
    band = aspectDataset.GetRasterBand(1)
    ASPECT = np.radians(band.ReadAsArray(0,0,cols,rows)) # terrain aspect in radians
    aspectDataset = None
    COSGAMMA = np.cos(SLOPE)*np.cos(ZENITH) + np.sin(SLOPE)*np.sin(ZENITH)*np.cos(AZIMUTH-ASPECT)
#  co-register cos(gamma) with NIR band to correct for geo-reference error    
    write_band(COSGAMMA,path+'/cosgamma',projection_ms,geotransform_ms_subset)    
    subprocess.call(['python','/python/zfl2015/src/register.py',path+'/nir_band',path+'/cosgamma'])
    cgDataset = gdal.Open(path+'/cosgamma_warp',GA_ReadOnly)
    band = cgDataset.GetRasterBand(1)
    COSGAMMA = band.ReadAsArray(0,0,cols,rows).ravel()  # co-registered cos(gamma) image
    cgDataset = None
#  loop over the MS image bands 
    driver = msDataset.GetDriver()    
    outDataset = driver.Create(outfile,cols,rows,len(pos),GDT_Float32)
    outDataset.SetGeoTransform(geotransform_ms_subset)
    outDataset.SetProjection(projection_ms)
    for k in range(bands):
#  loop over the classes
        for c in range(1,num_classes+1):
            idx = np.where(CLASS==c)[0]
            MSk = MS[k,:,:].ravel()
            m,b,r,_,_ = stats.linregress(COSGAMMA[idx], MSk[idx])
            print 'Band: %i Class: %i Pixels: %i Slope: %f Intercept: %f Correlation: %f'%(pos[k],c,len(idx),m,b,r)
            if r>0.2:
                print '---correcting band %i, class %i'%(pos[k],c)
                MSk[idx] = MSk[idx]*(np.cos(ZENITH) + b/m)/(COSGAMMA[idx] + b/m)
        outBand = outDataset.GetRasterBand(k+1)
        outBand.WriteArray(np.resize(MSk,(rows,cols)),0,0) 
        outBand.FlushCache()    
    outDataset = None
    msDataset = None
    demDataset = None
    print 'c-corrected image written to: '+outfile       
    print 'elapsed time: '+str(time.time()-start)                        
    
if __name__ == '__main__':
    main()      
                                           
#!/usr/bin/env python
#******************************************************************************
#  Name:     pca.py
#  Purpose:  Principal components analysis
#  Usage (from command line):             
#    python pca.py  [-d spatialDimensions] fileNmae
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
import numpy as np
import os, sys, getopt, time
from osgeo import gdal
import matplotlib.pyplot as plt
from osgeo.gdalconst import GA_ReadOnly,GDT_Float32

def main(): 
    usage = '''Usage: python %s  [-d dims] [-p pos] fileName\n
            spatial dimension is a list, e.g., -d [0,0,400,400] \n'''%sys.argv[0]
    options,args = getopt.getopt(sys.argv[1:],'hnd:p:')
    dims = None
    pos = None
    graphics = True
    for option, value in options: 
        if option == '-h':
            print usage
            return 
        elif option == '-n':
            graphics = False
        elif option == '-d':
            dims = eval(value)  
        elif option == '-p':
            pos = eval(value)
    gdal.AllRegister()
    infile = args[0] 
    path = os.path.dirname(infile)
    basename = os.path.basename(infile)
    root, ext = os.path.splitext(basename)
    outfile = path+'/'+root+'_pca'+ext    
    print '------------PCA ---------------'
    print time.asctime()     
    print 'Input %s'%infile
    start = time.time()    
    
    inDataset = gdal.Open(infile,GA_ReadOnly)
    try:                         
        cols = inDataset.RasterXSize
        rows = inDataset.RasterYSize    
        bands = inDataset.RasterCount
    except Exception as e:
        print 'Error: %s  -- Could not read in file'%e
        sys.exit(1)
    if dims:
        x0,y0,cols,rows = dims
    else:
        x0 = 0
        y0 = 0       
    if pos is not None:
        bands = len(pos)
    else:
        pos = range(1,bands+1)        
#  data matrix
    G = np.zeros((rows*cols,bands)) 
    k = 0                               
    for b in pos:
        band = inDataset.GetRasterBand(b)
        tmp = band.ReadAsArray(x0,y0,cols,rows)\
                              .astype(float).ravel()
        G[:,k] = tmp - np.mean(tmp)
        k += 1      
#  covariance matrix
    C = np.mat(G).T*np.mat(G)/(cols*rows-1)   
#  diagonalize    
    lams,U = np.linalg.eigh(C)     
#  sort
    idx = np.argsort(lams)[::-1]
    lams = lams[idx]
    U = U[:,idx] 
    print 'Eigenvalues: %s'%str(lams)
    if graphics: 
        plt.plot(range(1,bands+1),lams)
        plt.title(infile)
        plt.ylabel('Eigenvalue') 
        plt.xlabel('Spectral Band')
        plt.show()
        plt.close()                  
#  project
    PCs = np.reshape(np.array(G*U),(rows,cols,bands))       
#  write to disk       
    driver = inDataset.GetDriver() 
    outDataset = driver.Create(outfile,
                cols,rows,bands,GDT_Float32)
    projection = inDataset.GetProjection()
    geotransform = inDataset.GetGeoTransform()
    if geotransform is not None:
        gt = list(geotransform)
        gt[0] = gt[0] + x0*gt[1]
        gt[3] = gt[3] + y0*gt[5]
        outDataset.SetGeoTransform(tuple(gt))
    if projection is not None:
        outDataset.SetProjection(projection)        
    for k in range(bands):        
        outBand = outDataset.GetRasterBand(k+1)
        outBand.WriteArray(PCs[:,:,k],0,0) 
        outBand.FlushCache() 
    outDataset = None    
    inDataset = None        
    print 'result written to: %s'%outfile
    print 'elapsed time: %s'%str(time.time()-start) 
     
if __name__ == '__main__':
    main()    
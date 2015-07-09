#!/usr/bin/env python
#Name:  recon.py
import auxil.auxil as auxil
from numpy import *
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly, GDT_Float32

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
#  data matrix
    n = rows*cols
    Z = zeros((n,bands))                                  
    for b in range(bands):
        band = inDataset.GetRasterBand(b+1)
        tmp = band.ReadAsArray(0,0,cols,rows)\
                              .astype(float).ravel()
        Z[:,b] = tmp - mean(tmp) 
    Z = mat(Z)           
#  covariance matrix
    S = Z.T*Z/n 
#  diagonalize and sort eigenvectors  
    lamda,V = linalg.eigh(S)
    idx = argsort(lamda)[::-1]
    lamda = lamda[idx]
    V = V[:,idx]                    
#  get principal components and reconstruct
    r = 2
    X = Z*V    
    Z_r = X[:,:r]*V[:,:r].T
    recon = reshape(array(Z_r),(rows,cols,bands))

#  write to disk       
    outfile,fmt = auxil.select_outfilefmt() 
    if outfile:
        driver = gdal.GetDriverByName(fmt)   
        outDataset = driver.Create(outfile,
                        cols,rows,bands,GDT_Float32)
        projection = inDataset.GetProjection()
        geotransform = inDataset.GetGeoTransform()
        if geotransform is not None:
            gt = list(geotransform)  #geotransform is a tuple
            gt[0] = gt[0] + gt[1]
            gt[3] = gt[3] + gt[5]
            outDataset.SetGeoTransform(tuple(gt))
        if projection is not None:
            outDataset.SetProjection(projection)        
        for k in range(bands):        
            outBand = outDataset.GetRasterBand(k+1)
            outBand.WriteArray(recon[:,:,k],0,0) 
            outBand.FlushCache() 
        outDataset = None    
 
if __name__ == '__main__':
    main()    
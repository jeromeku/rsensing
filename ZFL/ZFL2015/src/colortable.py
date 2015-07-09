import sys, shapefile
import auxil.auxil as auxil 
import numpy as np
from dispms import make_image
import matplotlib.pyplot as plt

def colortable(trnfile):    
    r = shapefile.Reader(trnfile)
    records = r.records()  
    classids = []
    classnames = ['UNCLASSIFIED']
    K = -1
    for record in records:
        classid = int(record[1])
        classname = record[0]
        if classid > K:
            K = classid
            classids.append(classid+1)
            classnames.append(classname)
#  number of classes              
    K += 1        
    ctable = np.reshape(auxil.ctable,(18,3)) 
    redband = np.zeros(((K+1)*20,80),dtype=np.uint8) + 255
    greenband = redband*0 + 255
    blueband  = redband*0 + 255  
    redband[:20,:20] = ctable[0,0]
    greenband[:20,:20] = ctable[0,1]
    blueband[:20:,:20] = ctable[0,2]  
    for k in classids:
        redband[k*20:(k+1)*20,:20] = ctable[k,0]
        greenband[k*20:(k+1)*20,:20] = ctable[k,1]
        blueband[k*20:(k+1)*20,:20] = ctable[k,2]
    X = make_image(redband,greenband,blueband,(K+1)*20,80,'linear')    
    f, ax = plt.subplots(figsize=(6,8))
    ax.imshow(X)
    plt.title(trnfile)
    y = 0
    for classname in classnames:
        plt.text(30,y+10,classname)
        y+=20
    plt.show()
    
def main():
    usage = '''
Usage: 
python %s trainShapefile''' %sys.argv[0]
    try:
        trnfile = sys.argv[1]
    except:
        print usage
    ctable = colortable(trnfile)

if __name__ == '__main__':
    main()     
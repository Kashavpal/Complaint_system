import cv2, numpy as np
FACE=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
def face_similarity(original_path,candidate_path):
    a=cv2.imread(original_path); b=cv2.imread(candidate_path)
    if a is None or b is None: return False,0.0,'Image could not be read.'
    ga=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); gb=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    fa=FACE.detectMultiScale(ga,1.1,5); fb=FACE.detectMultiScale(gb,1.1,5)
    if len(fa)!=1 or len(fb)!=1: return False,0.0,'Exactly one detectable face is required in each image.'
    xa,ya,wa,ha=fa[0]; xb,yb,wb,hb=fb[0]
    ca=cv2.equalizeHist(cv2.resize(ga[ya:ya+ha,xa:xa+wa],(160,160))).astype(np.uint8)
    cb=cv2.equalizeHist(cv2.resize(gb[yb:yb+hb,xb:xb+wb],(160,160))).astype(np.uint8)
    ha1=cv2.calcHist([ca],[0],None,[64],[0,256]); hb1=cv2.calcHist([cb],[0],None,[64],[0,256])
    score=float(cv2.compareHist(ha1,hb1,cv2.HISTCMP_CORREL))
    return score>=0.72,score,'Verification completed.'

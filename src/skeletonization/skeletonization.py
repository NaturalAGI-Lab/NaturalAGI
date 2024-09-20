import numpy as np
from settings import Settings, gng_parameters
from ypstruct import structure
import gng
import json
import cv2

def image_to_contours(image_path: str, threshold = 0.0) -> np.array:
    
    image = cv2.imread(image_path, 0)
    
    h = image.shape[0]
    w = image.shape[1]

    points = []

    for y in range(0, h):
        for x in range(0, w):
            # threshold the pixel     
            
            if image[y, x] > threshold:            
                    points.append([x, y])

    return np.array(points)   
    
def gng_skeletonization(image_path: str, settings: Settings): 

    points_np = image_to_contours(image_path, settings.cnr_threshold)
    # Fit Neural Gas to Data
    print("Fitting Growing Neural Gas Network ...")
    net = gng.fit(points_np, gng_parameters(settings))    
    return net


def net_to_json(net):
    
    net_dict = dict(net)       
    return json.dumps(net_dict, indent = 4) 

def net_from_json(json_net):        
    net = structure(json.loads(json_net))      
    return net
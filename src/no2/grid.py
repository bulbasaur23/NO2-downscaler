import math
import pandas as pd

CELLS_PER_DEG=20
CELL_DEG=1/CELLS_PER_DEG

#derive cell_index --> [-180,180] to [0,360] for lon
#[-90,90] to [0,180] for lat
def cell_index(lon:float,lat:float)-> tuple[int,int]:
    ix=math.floor(round((lon+180)*CELLS_PER_DEG,6))  #longitudinal index
    iy=math.floor(round((lat+90)*CELLS_PER_DEG,6))  #latitudinal index
    #The +180 and +90 shift longitude and latitude into non-negative grid coordinates.
    return ix,iy 

#unique index
def make_cell_id(ix:int,iy:int) ->str:
    return f"{iy}_{ix}"

def cell_bounds(ix:int,iy:int)->tuple[float,float,float,float]:
    #returns west,south,east,north of a cell
    west=round(ix/CELLS_PER_DEG-180,6)
    south=round(iy/CELLS_PER_DEG-90,6)
    return west,south,round(west+CELL_DEG,6),round(south+CELL_DEG,6)

#create DataFrame
def cells_in_bbox(west:float,south:float,east:float,north:float)-> pd.DataFrame:
    ix0 = (west + 180) * CELLS_PER_DEG
    iy0 = (south + 90) * CELLS_PER_DEG
    ix1 = (east + 180) * CELLS_PER_DEG
    iy1 = (north + 90) * CELLS_PER_DEG

    # tolerating error
    for v in (ix0,iy0,ix1,iy1):
        if abs(v-round(v))>1e-6:
            raise ValueError("Bounding Box edges must lie on the 0.05 grid")

    rows=[]
    for iy  in range(round(iy0),round(iy1)): #from iy0 to iy1-1
        for ix in range(round(ix0),round(ix1)):  #from ix0 to ix1-1
            w,s,e,n=cell_bounds(ix,iy)
            rows.append({
                "cell_id":make_cell_id(ix,iy),
                "ix":ix,
                "iy":iy,
                "west":w,
                "south":s,
                "east":e,
                "north":n,
                "lon":round((w+e)/2,6),
                "lat":round((s+n)/2,6)
            })

    return pd.DataFrame(rows,columns=["cell_id","ix","iy","west","south","east","north","lon","lat"],)
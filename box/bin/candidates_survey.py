import numpy as np, zarr, tifffile, time
B="https://vesuvius-challenge-open-data.s3.amazonaws.com"
C=[("PHerc0125","20250821151825-9.362um-1.2m-113keV-masked.zarr",20840),("PHerc0211","20250821151803-9.362um-1.2m-113keV-masked.zarr",19416),("PHerc0813","20250821151723-9.362um-1.2m-113keV-masked.zarr",16993),("PHerc0826","20250821151701-9.362um-1.2m-113keV-masked.zarr",16920),("PHerc0257","20250821151750-9.362um-1.2m-113keV-masked.zarr",18872)]
tiles=[]
for sc,vol,nz in C:
    try:
        a=zarr.open(f"{B}/{sc}/volumes/{vol}", mode="r")["4"]
        for frac in (0.40,0.65):
            z=int(nz*frac); img=np.asarray(a[z//16]).astype(np.float32); v=img[img>0]; lo,hi=(np.percentile(v,[1,99.5]) if v.size else (0,1))
            t=np.clip((img-lo)/(hi-lo),0,1)*255; pad=np.zeros((560,560),np.float32); h,w=t.shape; pad[:min(h,560),:min(w,560)]=t[:560,:560]; tiles.append(pad); print(sc,z,img.shape,flush=True)
    except Exception as e: print(sc,"failed",str(e)[:80],flush=True)
cols=len(tiles)//2; grid=np.zeros((2*560,cols*560),np.uint8)
for i,t in enumerate(tiles): c,r=divmod(i,2); grid[r*560:(r+1)*560,c*560:(c+1)*560]=t.astype(np.uint8)
tifffile.imwrite("/tmp/candidates_survey.tif",grid); print("MONTAGE-EXIT: 0", grid.shape)

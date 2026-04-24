import csv
import numpy as np
import cv2

"""
Used to convert .csv files containing 2D bounding boxes into 3D coordinates.
Before running, be sure to calibrate the views of your cameras and generate
the below projection matrices.

Before running code, edit projection matrix and 2D data paths.
"""

K1 = np.load("stereo_K1.npy")
K2 = np.load("stereo_K2.npy")
d1 = np.load("stereo_d1.npy")
d2 = np.load("stereo_d2.npy")
R = np.load("stereo_R.npy")
T = np.load("stereo_T.npy")

def read_csv(file):
    data = []
    with open(file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = float(row["timestamp"])
            cx = float(row["cx"])
            cy = float(row["cy"])
            data.append((ts, cx, cy))
    return data

cam1_data = read_csv("cam1_0407.3.csv")
cam2_data = read_csv("cam2_0407.3.csv")

R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K1, d1, K2, d2, (4608,2592), R, T)

def merge_by_time(data1, data2, tol=0.02):  # 20 ms offset tolerance. Should not be an issue due to simultaneous Arduino trigger.
    merged = []
    j = 0
    for t1, x1, y1 in data1:
        while j < len(data2)-1 and abs(data2[j+1][0]-t1) < abs(data2[j][0]-t1):
            j += 1
        t2, x2, y2 = data2[j]
        if abs(t1 - t2) < tol:
            merged.append((t1, (x1, y1), (x2, y2)))
    return merged

merged = merge_by_time(cam1_data, cam2_data)

def triangulate(pts1, pts2):
    pts1 = np.array(pts1, dtype=np.float32).reshape(-1,1,2)
    pts2 = np.array(pts2, dtype=np.float32).reshape(-1,1,2)

    pts1_ud = cv2.undistortPoints(pts1, K1, d1, R=R1, P=P1)
    pts2_ud = cv2.undistortPoints(pts2, K2, d2, R=R2, P=P2)

    pts4d = cv2.triangulatePoints(P1, P2, pts1_ud, pts2_ud)
    pts3d = (pts4d[:3] / pts4d[3]).T
    return pts3d

with open("3d_0407.3.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp","X","Y","Z"])
    for ts, (x1,y1), (x2,y2) in merged:
        pts3d = triangulate([(x1,y1)], [(x2,y2)])
        X,Y,Z = pts3d[0] #Y,Z,X closest so far
        writer.writerow([f"{ts:.6f}", f"{X:.3f}", f"{Y:.3f}", f"{Z:.3f}"])

print("3D points saved.")
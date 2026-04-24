import cv2
import numpy as np
import glob
import os

"""
Generates the projection matrices needed to convert PICTUS 2D points
into 3D points.
"""

CHECKERBOARD = (8, 10)  # inner corners, (width, height)
SQUARE_SIZE = 10.0     # mm, but can be any consistent unit
DIR1 = "/media/rohara/AEAB-F3D82/calib_images_1"     # path to images from camera 1
DIR2 = "/media/rohara/AEAB-F3D82/calib_images_2"     # path to images from camera 2

ENABLE_RATIONAL_MODEL = False  # rational model is more complex, use when checkerboard is bad
CHECK_REPROJECTION_ERROR = True  # remove outlier frames
MAX_REPROJECTION_ERROR = 0.2  # pixels
MEASURE_BOARD_FLATNESS = True  # detect if checkerboard is warped
MAX_STEREO_PAIR_ERROR = 0.3  # max pair error before pair is removed
STEREO_OUTLIER_ITERATIONS = 5

def find_corners(img_path, pattern):
    """Determines locations of checkerboard corners."""
    img = cv2.imread(img_path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, pattern, None)
    if not ret:
        return None
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (5,5), (-1,-1), criteria)   # NOTE: adjust this parameter if your reprojection error is high
    return corners

def compute_reprojection_error(objpoints, imgpoints, rvec, tvec, K, d):
    """Calculate reprojection error for a single image."""
    projected, _ = cv2.projectPoints(objpoints, rvec, tvec, K, d)
    projected = projected.reshape(-1, 2)
    imgpoints_reshaped = imgpoints.reshape(-1, 2)

    diff = imgpoints_reshaped - projected
    error = np.sqrt(np.sum(diff**2)) / len(projected)

    return error

def estimate_board_planarity(objpoints, imgpoints, K, d, rvec, tvec):
    """Estimate how planar the detected board is by computing z-variance."""
    R, _ = cv2.Rodrigues(rvec)
    points_cam = (R @ objpoints.T).T + tvec.T
    centroid = points_cam.mean(axis=0)
    centered = points_cam - centroid
    _, _, vh = np.linalg.svd(centered)
    normal = vh[2, :]
    distances = np.abs(centered @ normal)
    max_deviation = distances.max()
    rms_deviation = np.sqrt(np.mean(distances**2))
    
    return max_deviation, rms_deviation

def check_corner_orientation(img_path1, img_path2, pattern, save_debug = True):
    """Determines if first corners on images are aligned (and flips images if needed)."""
    img1 = cv2.imread(img_path1)
    img2 = cv2.imread(img_path2)
    c1 = find_corners(img_path1, pattern)
    c2 = find_corners(img_path2, pattern)

    if c1 is None or c2 is None:
        print("Bad corners detected.")
        return False

    dbg1 = img1.copy()
    dbg2 = img2.copy()
    cv2.drawChessboardCorners(dbg1, pattern, c1, True)
    cv2.drawChessboardCorners(dbg2, pattern, c2, True)
    p1 = tuple(c1[0].ravel().astype(int))
    p2 = tuple(c2[0].ravel().astype(int))

    w1 = img1.shape[1]
    w2 = img2.shape[1]
    c1_side = "left" if p1[0] < w1 / 2 else "right"
    c2_side = "left" if p2[0] < w2 / 2 else "right"
    needs_flip = (c1_side != c2_side)
    if needs_flip:
        print("Mismatch, camera 2 corners will be flipped.")
    else:
        print("No flip needed.")

    return needs_flip

def flip_corners_if_needed(corners, needs_flip):
    """Flips calibration image if corners aren't aligned."""
    if needs_flip:
        return corners[::-1]
    return corners

def compute_stereo_pair_errors(objpoints, imgpoints1, imgpoints2, K1, d1, K2, d2, R, T):
    """Determines error between image pairs."""
    errors, errs1, errs2 = [], [], []
    for obj, ip1, ip2, in zip(objpoints, imgpoints1, imgpoints2):
        _, rvec1, tvec1 = cv2.solvePnP(obj, ip1, K1, d1)
        _, rvec2, tvec2 = cv2.solvePnP(obj, ip2, K2, d2)

        e1 = compute_reprojection_error(obj, ip1, rvec1, tvec1, K1, d1)
        e2 = compute_reprojection_error(obj, ip2, rvec2, tvec2, K2, d2)

        errs1.append(e1)
        errs2.append(e2)
        errors.append((e1 + e2) / 2.0)
    return errors, errs1, errs2

def single_camera_calibration(images, checkerboard, square_size):
    '''Calibrates a single camera with optional rational distortion model.'''
    objp = np.zeros((checkerboard[0]*checkerboard[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard[0], 0:checkerboard[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints = []
    imgpoints = []
    valid_images = []

    for f in images:
        corners = find_corners(f, checkerboard)
        if corners is not None:
            objpoints.append(objp)
            imgpoints.append(corners)
            valid_images.append(f)

    if len(objpoints) == 0:
        raise ValueError("No valid calibration images found!")

    gray = cv2.imread(valid_images[0], cv2.IMREAD_GRAYSCALE)
    flags = 0
    if ENABLE_RATIONAL_MODEL:
        flags = cv2.CALIB_RATIONAL_MODEL
    
    ret, K, d, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None, flags=flags
    )
    
    if CHECK_REPROJECTION_ERROR or MEASURE_BOARD_FLATNESS:
        filtered_objpoints = []
        filtered_imgpoints = []
        filtered_images = []
        
        for i, (obj, img, rvec, tvec, fname) in enumerate(zip(objpoints, imgpoints, rvecs, tvecs, valid_images)):
            reproj_err = compute_reprojection_error(obj, img, rvec, tvec, K, d)
            
            planarity_info = ""
            if MEASURE_BOARD_FLATNESS:
                max_dev, rms_dev = estimate_board_planarity(obj, img, K, d, rvec, tvec)
                planarity_info = f", planarity RMS: {rms_dev:.3f}mm, max: {max_dev:.3f}mm"
            
            keep = True
            if CHECK_REPROJECTION_ERROR and reproj_err > MAX_REPROJECTION_ERROR:
                keep = False
            
            if keep:
                filtered_objpoints.append(obj)
                filtered_imgpoints.append(img)
                filtered_images.append(fname)
        
        if len(filtered_objpoints) < len(objpoints):
            ret, K, d, rvecs, tvecs = cv2.calibrateCamera(
                filtered_objpoints, filtered_imgpoints, gray.shape[::-1], None, None, flags=flags
            )
    
    return K, d, ret, valid_images

def reshape_corners(c, rows, cols):
    return c.reshape(cols, rows, 1, 2)

def find_correct_flip(files1, files2, checkerboard, K1, d1, K2, d2):
    objp = np.zeros((checkerboard[0] * checkerboard[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard[0], 0:checkerboard[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE

    objpoints, imgpoints1, imgpoints2_raw = [], [], []
    for f1, f2 in zip(files1, files2):
        c1 = find_corners(f1, checkerboard)
        c2 = find_corners(f2, checkerboard)
        if c1 is not None and c2 is not None:
            objpoints.append(objp)
            imgpoints1.append(c1)
            imgpoints2_raw.append(c2)

    rows, cols = checkerboard
    n = rows * cols

    transforms = {
        "no_flip":        lambda c: c,
        "full_reverse":   lambda c: c[::-1],
        "flip_rows":      lambda c: reshape_corners(c, rows, cols)[::-1].reshape(n, 1, 2),
        "flip_cols":      lambda c: reshape_corners(c, rows, cols)[:, ::-1].reshape(n, 1, 2)
    }

    gray = cv2.imread(files1[0], cv2.IMREAD_GRAYSCALE)
    img_size = gray.shape[::-1]

    for name, transform in transforms.items():
        imgpoints2 = [transform(c) for c in imgpoints2_raw]
        try:
            ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(objpoints, imgpoints1, imgpoints2, K1, d1, K2, d2, img_size, flags=cv2.CALIB_FIX_INTRINSIC)
            rvec, _ = cv2.Rodrigues(R)
            angle = np.linalg.norm(rvec) * 180.0 / np.pi
            print(f"{name:<20} RMS: {ret:.4f} Rotation: {angle} degrees")
        except Exception as e:
            print(f"{name:<20} FAILED {e}")

def stereo_calibration(dir1, dir2, checkerboard, square_size):
    '''Calibrates both cameras and performs stereo calibration.'''
    files1 = sorted(glob.glob(os.path.join(dir1, "*.jpg")))
    files2 = sorted(glob.glob(os.path.join(dir2, "*.jpg")))
    
    if len(files1) == 0 or len(files2) == 0:
        raise ValueError("No images found.")
    
    K1, d1, err1, valid1 = single_camera_calibration(files1, checkerboard, square_size)
    print(f"Camera 1 final RMS: {err1:.4f}")
    print(f"Used {len(valid1)} images")
    K2, d2, err2, valid2 = single_camera_calibration(files2, checkerboard, square_size)
    print(f"\nCamera 2 final RMS: {err2:.4f}")
    print(f"Used {len(valid2)} images")

    #find_correct_flip(files1, files2, checkerboard, K1, d1, K2, d2)

    needs_flip = check_corner_orientation(files1[0], files2[0], checkerboard)

    objpoints = []
    imgpoints1 = []
    imgpoints2 = []

    objp = np.zeros((checkerboard[0]*checkerboard[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:checkerboard[0], 0:checkerboard[1]].T.reshape(-1, 2)
    objp *= square_size

    for f1, f2 in zip(files1, files2):
        c1 = find_corners(f1, checkerboard)
        c2 = find_corners(f2, checkerboard)
        if c1 is not None and c2 is not None:
            objpoints.append(objp)
            imgpoints1.append(c1)
            rows, cols = checkerboard
            n = rows * cols
            c2_fixed = reshape_corners(c2, rows, cols)[:, ::-1].reshape(n, 1, 2)

            imgpoints2.append(c2_fixed)
    
    gray = cv2.imread(files1[0], cv2.IMREAD_GRAYSCALE)
    
    stereo_flags = cv2.CALIB_FIX_INTRINSIC
    if ENABLE_RATIONAL_MODEL:
        stereo_flags |= cv2.CALIB_RATIONAL_MODEL

    pair_names = [f"{os.path.basename(f1)} / {os.path.basename(f2)}"
                  for f1, f2 in zip(files1, files2)
                  if find_corners(f1, checkerboard) is not None and find_corners(f2, checkerboard) is not None]

    ret = None
    R = T = E = F = None

    for iteration in range(STEREO_OUTLIER_ITERATIONS + 1):
        if len(objpoints) < 6:
            break

        ret, K1, d1, K2, d2, R, T, E, F = cv2.stereoCalibrate(
            objpoints, imgpoints1, imgpoints2,
            K1, d1, K2, d2, gray.shape[::-1],
            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5),
            flags=stereo_flags
        )

        pair_errors, errs1, errs2 = compute_stereo_pair_errors(objpoints, imgpoints1, imgpoints2, K1, d1, K2, d2, R, T)

        keep_mask = []
        for i, (name, e_mean, e1, e2) in enumerate(zip(pair_names, pair_errors, errs1, errs2)):
            keep = e_mean <= MAX_STEREO_PAIR_ERROR
            keep_mask.append(keep)

        n_rejected = keep_mask.count(False)
        if n_rejected == 0 or iteration == STEREO_OUTLIER_ITERATIONS:
            if n_rejected == 0:
                print("All pairs within threshold, stopping rejection.")
            else:
                print("Reached max iterations.")
            break

        objpoints = [o for o, k in zip(objpoints, keep_mask) if k]
        imgpoints1 = [p for p, k in zip(imgpoints1, keep_mask) if k]
        imgpoints2 = [p for p, k in zip(imgpoints2, keep_mask) if k]
        pair_names = [n for n, k in zip(pair_names, keep_mask) if k]

        print(f"\n Keeping {len(objpoints)} pairs and rerunning.")

    print(f"\nStereo RMS error: {ret:.4f}")

    rvec_stereo, _ = cv2.Rodrigues(R)
    angle_deg = np.linalg.norm(rvec_stereo) * 180.0 / np.pi
    print(f"Rotation angle is {angle_deg}.") # You want your angle to be as close to 180 degrees as possible.

    print("\nK1:")
    print(K1)
    print(f"\nd1: {d1.ravel()}")
    print("\nK2:")
    print(K2)
    print(f"\nd2: {d2.ravel()}")
    print("\nR:")
    print(R)
    print("\nT (mm):")
    print(T.ravel())
    print(f"\nBaseline distance: {np.linalg.norm(T):.2f} mm") # This should be the distance between cameras.

    np.save("stereo_K1.npy", K1)
    np.save("stereo_d1.npy", d1)
    np.save("stereo_K2.npy", K2)
    np.save("stereo_d2.npy", d2)
    np.save("stereo_R.npy", R)
    np.save("stereo_T.npy", T)

    print("Generated calibration files.")
    
    return K1, d1, K2, d2, R, T

if __name__ == "__main__":
    stereo_calibration(DIR1, DIR2, CHECKERBOARD, SQUARE_SIZE)

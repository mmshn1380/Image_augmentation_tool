import numpy as np
import cv2
import os
import json

def nplbl2dictlbl(image_path, category, lbl):
    label = {"image_path": image_path, "category": category, "points": lbl.tolist()}
    return label

def show_image(img, lbl):
    lbl_img = img.copy()
    lbl_img = cv2.polylines(lbl_img, [lbl], True, (0, 0, 255), 3)
    cv2.namedWindow('image', cv2.WINDOW_NORMAL)
    cv2.imshow("image", lbl_img)
    cv2.waitKey(0)

def save_image_with_lbl(img, lbl):
    lbl_img = img.copy()
    lbl_img = cv2.polylines(lbl_img, [lbl], True, (0, 0, 255), 3)
    cv2.imwrite("image.jpg", lbl_img)

def rotate_image(img, lbl, angle):
    """
    Rotates an image (angle in degrees) and expands image to avoid cropping
    """

    height, width = img.shape[:2] # image shape has 3 dimensions
    image_center = (width/2, height/2) # getRotationMatrix2D needs coordinates in reverse order (width, height) compared to shape

    rotation_mat = cv2.getRotationMatrix2D(image_center, angle, 1.)

    # rotation calculates the cos and sin, taking absolutes of those.
    abs_cos = abs(rotation_mat[0,0]) 
    abs_sin = abs(rotation_mat[0,1])

    # find the new width and height bounds
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)

    # subtract old image center (bringing image back to origo) and adding the new image center coordinates
    rotation_mat[0, 2] += bound_w/2 - image_center[0]
    rotation_mat[1, 2] += bound_h/2 - image_center[1]

    # rotate image with the new bounds and translated rotation matrix
    rot_img = cv2.warpAffine(img, rotation_mat, (bound_w, bound_h))

    # rotate label
    rot_lbl = lbl.copy()
    rot = rotation_mat[:, 0:2]
    move = rotation_mat[:, 2].reshape(2,1)
    def rotate_point(point):
        return (np.matmul(rot, point.reshape(2,1)) + move).T
    rot_lbl = np.array([rotate_point(point) for point in rot_lbl])
    rot_lbl = rot_lbl.reshape(2,2)
    rot_lbl = rot_lbl.astype(np.int32)

    return rot_img, rot_lbl

def mirror_image(img, lbl):
    mirror_img = img.copy()
    mirror_img = cv2.flip(mirror_img, 1)
    mirror_lbl = lbl.copy()
    mirror_lbl[:, 0] = img.shape[1] - lbl[:, 0] - 1
    mirror_lbl[:, 1] = lbl[:, 1]
    return mirror_img, mirror_lbl

def resize_image(img, lbl, scale):
    resize_img = cv2.resize(img, None, fx=scale, fy=scale)
    resize_lbl = lbl.copy()
    resize_lbl[:, 0] = lbl[:, 0] * scale
    resize_lbl[:, 1] = lbl[:, 1] * scale
    return resize_img, resize_lbl


def generate(src_path, dst_path, angle_start, angle_step, angle_stop, scale_start, scale_step, scale_stop, mirror, save_format, lbl_dict):
    supported_formats = ["jpg", "png", "bmp"]
    if not os.path.exists(dst_path):
        os.makedirs(dst_path)
    for img_path in os.listdir(src_path):
        img_format = img_path.split(".")[-1]
        if not img_format in supported_formats:
            continue
        img_path = os.path.join(src_path, img_path)
        orig_img = cv2.imread(img_path)
        img_name = img_path.split("/")[-1].replace("." + img_format, "")
        img_name_with_ext = img_name + "." + img_format
        if not img_name_with_ext in lbl_dict:
            continue
        lbl = lbl_dict[img_name_with_ext]
        for scale in np.arange(scale_start, scale_stop + scale_step, scale_step):
            for angle in np.arange(angle_start, angle_stop + angle_step, angle_step):
                img, lbl = resize_image(orig_img, lbl, scale)
                img, lbl = rotate_image(img, lbl, angle)
                
                img_save_name = img_name + "_" + str(angle) + "_" + str(scale) + "." + img_format
                save_path = os.path.join(dst_path, img_save_name)
                save_lbl(dst_path, lbl, img_save_name, save_format)
                cv2.imwrite(save_path, img)

                if mirror:
                    img, lbl = mirror_image(img, lbl)
                    img_save_name = img_name + "_" + str(angle) + "_" + str(scale) + "_flip" + "." + img_format
                    save_path = os.path.join(dst_path, img_save_name)
                    save_lbl(dst_path, lbl, img_save_name, save_format)
                    cv2.imwrite(save_path, img)

def save_lbl(dst, lbl, name, save_format):
    label_name = dst + "/tags." + save_format
    if save_format == "csv":
        with open(label_name, "a") as f:
            f.write(name + " " + str(lbl[0, 0]) + " " + str(lbl[0, 1]) + " " + str(lbl[1, 0]) + " " + str(lbl[1, 1]) + "\n")
    elif save_format == "json":
        data = {}
        if os.path.exists(label_name):
            with open(label_name, "r") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        data[name] = lbl.tolist()
        with open(label_name, "w") as f:
            json.dump(data, f)



if __name__ == "__main__":
    # img = cv2.imread("cat.png")
    # lbl = np.array([[281, 666], [554, 668], [549, 8], [283, 5]])

    # show_image(img, lbl)

    # rot_img, rot_lbl = rotate_image(img, lbl, 30)

    # mirr_img, mirr_lbl = mirror_image(img, lbl)

    # resized_img, resized_lbl = resize_image(img, lbl, 0.5)

    # label = nplbl2dictlbl("cat1.png", "cat", lbl)
    # print(label)

    lbl_dict = {}
    lbl_dict["cat.png"] = np.array([[281, 666], [554, 668]])
    generate("./", "./dst/", -30, 1, 30, 1, 1, 1, False, "json", lbl_dict)
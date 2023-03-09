import os
import numpy as np
import cv2
from onnxruntime import InferenceSession

import logging
import traceback

rmbg_model = None

logging.basicConfig(filename='abgr_error.log', level=logging.DEBUG)


# img returned [h,w,3]
def read_image(src):
    img_array = np.fromfile(src, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img


def write_image(dst, img, params=None):
    print(dst, "에 저장됨!")
    try:
        ext = os.path.splitext(dst)[1]
        result, n = cv2.imencode(ext, img, params)

        if result:
            with open(dst, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        logging.error(traceback.format_exc() + str(e))
        return False


def get_mask(img, s=1024):
    img = (img / 255).astype(np.float32)
    h, w = h0, w0 = img.shape[:-1]
    h, w = (s, int(s * w / h)) if h > w else (int(s * h / w), s)
    ph, pw = s - h, s - w
    img_input = np.zeros([s, s, 3], dtype=np.float32)
    img_input[ph // 2:ph // 2 + h, pw // 2:pw // 2 + w] = cv2.resize(img, (w, h))
    img_input = np.transpose(img_input, (2, 0, 1))
    img_input = img_input[np.newaxis, :]
    try:
        mask = rmbg_model.run(None, {'img': img_input})[0][0]
    except Exception as e:
        logging.error(traceback.format_exc() + str(e))
        assert False
        return None
    mask = np.transpose(mask, (1, 2, 0))
    mask = mask[ph // 2:ph // 2 + h, pw // 2:pw // 2 + w]
    mask = cv2.resize(mask, (w0, h0))[:, :, np.newaxis]
    return mask


def rmbg_fn(img):
    mask = get_mask(img)
    img = (mask * img + 255 * (1 - mask)).astype(np.uint8)
    mask = (mask * 255).astype(np.uint8)
    img = np.concatenate([img, mask], axis=2, dtype=np.uint8)
    mask = mask.repeat(3, axis=2)
    return mask, img


def apply_abgr(model_path, src, save_path=""):
    global rmbg_model

    if not rmbg_model:
        print("* 모델 로딩 중...")
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        rmbg_model = InferenceSession(model_path, providers=providers)
        print("* 로딩 완료!")

    print("ABGR 적용 중 - 대상 파일 :", src)

    img_tar = read_image(src)
    i1, i2 = rmbg_fn(img_tar)

    path_pair = os.path.split(src)
    path_dir = path_pair[0]
    path_filename = path_pair[1]

    path_pair = os.path.splitext(path_filename)
    path_filename = path_pair[0]
    path_ext = path_pair[1]

    if save_path and os.path.isdir(save_path):
        path_dir = save_path

    write_image(path_dir + "/" + path_filename + "_mask" + path_ext, i1)
    write_image(path_dir + "/" + path_filename + "_img" + path_ext, i2)


if __name__ == '__main__':
    from ABGRemoverGUI import SRC_MODEL
    import sys

    input_list = sys.argv

    print("시작!")

    if len(input_list) > 1:
        src_list = input_list[1:]
        for src in src_list:
            print("working on", src)
            apply_abgr(SRC_MODEL, src)

    input("끝!")

import os
import numpy as np
import cv2
from onnxruntime import InferenceSession

rmbg_model = None

# img returned [h,w,3]
def read_image(src):
    img_array = np.fromfile(src, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img


def write_image(dst, img, params=None):
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
        print(e)
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
    mask = rmbg_model.run(None, {'img': img_input})[0][0]
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


def apply_abgr(model_path, src):
    global rmbg_model

    if not rmbg_model:
        print("need to init model")
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        rmbg_model = InferenceSession(model_path, providers=providers)
        print("init done")

    print("abgr on ", src)

    img_tar = read_image(src)
    i1, i2 = rmbg_fn(img_tar)

    ns = src.split(".")

    filename = "".join(ns[:-1])
    ext = "".join(ns[-1:])
    write_image(filename + "_mask." + ext, i1)
    write_image(filename + "_img." + ext, i2)



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
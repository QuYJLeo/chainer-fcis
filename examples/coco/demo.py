#!/usr/bin/env python
import argparse
import datetime
import os
import os.path as osp

import matplotlib
if os.environ.get('DISPLAY') is None:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

import chainer
import easydict
import fcis
import yaml


filepath = osp.abspath(osp.dirname(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', default=0)
    parser.add_argument('-m', '--modelpath', default=None)
    parser.add_argument('--imgdir', default=None)
    args = parser.parse_args()

    # chainer config for demo
    gpu = args.gpu
    chainer.cuda.get_device_from_id(gpu).use()
    chainer.global_config.train = False
    chainer.global_config.enable_backprop = False

    # load config
    cfgpath = osp.join(filepath, 'cfg', 'demo.yaml')
    with open(cfgpath, 'r') as f:
        config = easydict.EasyDict(yaml.load(f))

    target_height = config.target_height
    max_width = config.max_width
    score_thresh = config.score_thresh
    nms_thresh = config.nms_thresh
    mask_merge_thresh = config.mask_merge_thresh
    binary_thresh = config.binary_thresh
    min_drop_size = config.min_drop_size
    iter2 = config.iter2

    # load label_names
    label_names = fcis.datasets.coco.coco_utils.coco_label_names
    n_class = len(label_names)

    # load model
    model = fcis.models.FCISResNet101(n_class)
    modelpath = args.modelpath
    if modelpath is None:
        modelpath = model.download('coco')
    chainer.serializers.load_npz(modelpath, model)
    model.to_gpu(gpu)

    # load input images
    if args.imgdir is None:
        imgdir = osp.join(filepath, 'images')
    else:
        imgdir = args.imgdir
    img_names = sorted(os.listdir(imgdir))
    imgpaths = []
    for name in img_names:
        if name.endswith(('.png', '.jpg', '.PNG', '.JPG')):
            imgpaths.append(osp.join(imgdir, name))
    orig_imgs = fcis.utils.read_images(imgpaths, channel_order='BGR')

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    savepath = osp.join(filepath, 'vis_demo', timestamp)
    if not osp.exists(savepath):
        os.makedirs(savepath)

    for i, orig_img in enumerate(orig_imgs):
        # prediction
        # H, W, C -> C, H, W
        bboxes, whole_masks, labels, cls_probs = model.predict(
            [orig_img.transpose((2, 0, 1))],
            target_height, max_width, score_thresh,
            nms_thresh, mask_merge_thresh, binary_thresh,
            min_drop_size, iter2=iter2)

        # batch size = 1
        bboxes = bboxes[0]
        whole_masks = whole_masks[0]
        labels = labels[0]
        cls_probs = cls_probs[0]

        # visualization
        fcis.utils.visualize_mask(
            orig_img[:, :, ::-1], whole_masks, bboxes, labels,
            cls_probs, label_names)
        plt.savefig(osp.join(savepath, '{}.png'.format(i)))
        plt.show()


if __name__ == '__main__':
    main()

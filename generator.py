import glob
import math
import pickle
import random
import tensorflow as tf
import keras as K
import os
import numpy as np
import cv2
from keras.utils import Sequence
import logging

random.seed(0)
np.random.seed(0)
tf.set_random_seed(0)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

file_path = os.path.dirname(__file__)
SEPARATOR = os.path.sep


class Generator:
    def __init__(self, ds_folder, batch_size=64, w=64, h=128, val_to_train=0.15, augmenter=None, preprocessor=None):
        cats_folders = list(sorted([name for name in os.listdir(ds_folder)
                                    if os.path.isdir(ds_folder + SEPARATOR + name)]))

        self.ds_imgs = []
        self.ds_labels = []
        logger.debug("start init of dataset")

        self.name_to_idx = {}
        self.idx_to_name = {}
        for i, cat in enumerate(cats_folders):
            for img_path in glob.glob(ds_folder + SEPARATOR + str(cat) + SEPARATOR + '*.jpg') + \
                            glob.glob(ds_folder + SEPARATOR + str(cat) + SEPARATOR + '*.png'):
                self.ds_imgs.append(img_path)
                self.ds_labels.append(i)
                self.name_to_idx[cat] = i
                self.idx_to_name[i] = cat

        self.ds_imgs = np.asarray(self.ds_imgs)
        self.ds_labels = np.asarray(self.ds_labels)
        self.all_indices = np.arange(self.ds_imgs.shape[0])
        self.all_length = self.ds_imgs.shape[0]
        self.batch_size = batch_size
        self.w = w
        self.h = h
        self.val_to_train = val_to_train
        self.cats_num = len(cats_folders)

        self.augmenter = augmenter
        self.preprocessor = preprocessor

        np.random.shuffle(self.all_indices)

        self.train_indices, self.val_indices = np.split(self.all_indices,
                                                        [int((1 - val_to_train) * self.all_length)])

        self.train_length = self.train_indices.shape[0]
        self.val_length = self.val_indices.shape[0]
        logger.debug("dataset inited")
        logger.debug("total %s img in train", self.train_length)
        logger.debug("total %s img in val", self.val_length)
        logger.debug("total %s categories", self.cats_num)

    class InnerGenerator(Sequence):

        def __init__(self, outer, indexes, is_train):
            self.indixes = indexes
            self.outer = outer
            self.length = self.indixes.shape[0]
            self.is_train = is_train

        def on_epoch_end(self):
            np.random.shuffle(self.indixes)

        def __getitem__(self, idx):
            try:
                inds = self.indixes[idx * self.outer.batch_size:(idx + 1) * self.outer.batch_size]
                images = self.outer.ds_imgs[inds]
                labels = self.outer.ds_labels[inds]

                labels_x = []
                labels_y = []

                for i in range(self.outer.batch_size):
                    img = cv2.imread(images[i])
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    if self.is_train and self.outer.augmenter is not None:
                        img = self.outer.augmenter(np.asarray([img]))[0]

                    img = cv2.resize(img, (self.outer.w, self.outer.h))
                    if self.outer.preprocessor is not None:
                        img = self.outer.preprocessor(img)

                    labels_x.append(img)
                    labels_y.append(K.utils.to_categorical([int(labels[i])], num_classes=self.outer.cats_num)[0])

                labels_x = np.asarray(labels_x)
                labels_y = np.asarray(labels_y)

                return labels_x, labels_y
            except Exception as e:
                logger.exception("error on generation")

        def __len__(self):
            return int(math.ceil(float(self.length) / self.outer.batch_size)) - 1

    def make_train_generator(self):
        return Generator.InnerGenerator(self, self.train_indices, True)

    def make_val_generator(self):
        return Generator.InnerGenerator(self, self.val_indices, False)

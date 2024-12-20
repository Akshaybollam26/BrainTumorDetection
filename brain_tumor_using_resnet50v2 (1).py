# -*- coding: utf-8 -*-
"""BRAIN_TUMOR_USING_RESNET50V2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1kc4wN5W3ncnUiXfw7C_mHTi-bufKXEKs
"""

from google.colab import drive
drive.mount('/content/drive')

import tensorflow as tf
print(tf.__version__)

#tf.config.list_physical_devices('GPU')
#tf.test.is_gpu_available()

import os
os.environ['CUDA_VISIBLE_DEVICES']='0'

gpu = tf.config.experimental.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(gpu[0], True)


#from tensorflow.python.client import device_lib
#device_lib.list_local_devices()

import os
import numpy as np
import cv2
from random import shuffle
from tqdm import tqdm
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.utils import plot_model
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ReduceLROnPlateau , ModelCheckpoint
from collections import Counter
# Importing the libraries
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from keras.applications.resnet import preprocess_input
from tensorflow.keras.regularizers import l2

from sklearn.metrics import roc_auc_score, confusion_matrix, roc_curve, auc
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
import numpy as np
import seaborn as sn

import matplotlib.pyplot as plt
from itertools import cycle

tf.test.is_gpu_available()

TrianImage="/content/drive/MyDrive/SRI/SRI_Dataset_Aug/Training_aug"
TestImage="/content/drive/MyDrive/SRI/SRI_Dataset_Aug/Testing_aug"
giloma_tumor = os.listdir(TrianImage + "/giloma_tumor")
meningioma_tumor = os.listdir(TrianImage + "/meningioma_tumor")
no_tumor = os.listdir(TrianImage + "/no_tumor")
pituitary_tumor = os.listdir(TrianImage + "/pituitary_tumor")

print(len(giloma_tumor))
print(len(meningioma_tumor))
print(len(no_tumor))
print(len(pituitary_tumor))

NUM_TRAINING_IMAGES = len(giloma_tumor)+len(meningioma_tumor)+len(no_tumor) +len(pituitary_tumor)
print(NUM_TRAINING_IMAGES)

plt.figure(figsize=(10,10))
for i in range(9):
    plt.subplot(3, 3, i + 1)
    plt.imshow(plt.imread(os.path.join(TrianImage + "/giloma_tumor",giloma_tumor[i])),cmap='gray')
    plt.title("giloma_tumor")
plt.show()

plt.figure(figsize=(10,10))
for i in range(9):
    plt.subplot(3, 3, i + 1)
    plt.imshow(plt.imread(os.path.join(TrianImage + "/meningioma_tumor",meningioma_tumor[i])),cmap='gray')
    plt.title("meningioma_tumor")
plt.show()

plt.figure(figsize=(10,10))
for i in range(9):
    plt.subplot(3, 3, i + 1)
    plt.imshow(plt.imread(os.path.join(TrianImage + "/no_tumor",no_tumor[i])),cmap='gray')
    plt.title("no_tumor")
plt.show()

plt.figure(figsize=(10,10))
for i in range(9):
    plt.subplot(3, 3, i + 1)
    plt.imshow(plt.imread(os.path.join(TrianImage + "/pituitary_tumor",pituitary_tumor[i])),cmap='gray')
    plt.title("pituitary_tumor")
plt.show()

image_size = 224
BATCH_SIZE = 64
STEPS_PER_EPOCH = NUM_TRAINING_IMAGES // BATCH_SIZE

data_path = '/content/drive/MyDrive/SRI/SRI_Dataset_Aug'

train_datagen = ImageDataGenerator(rescale = 1./255,
                                   zoom_range = 0.2,
                                   rotation_range=15,
                                   horizontal_flip = True)

test_datagen = ImageDataGenerator(rescale = 1./255)

training_set = train_datagen.flow_from_directory(data_path + '/Training_aug',
                                                 target_size = (image_size, image_size),
                                                 batch_size = BATCH_SIZE,
                                                 class_mode = 'categorical',
                                                 shuffle=True)

testing_set = test_datagen.flow_from_directory(data_path + '/Testing_aug',
                                            target_size = (image_size, image_size),
                                            batch_size = BATCH_SIZE,
                                            class_mode = 'categorical',
                                            shuffle = True)

# https://www.tensorflow.org/api_docs/python/tf/keras/utils/Sequence
print("train batch ", training_set.__getitem__(0)[0].shape)
print("test batch ", testing_set.__getitem__(0)[0].shape)
print("sample train label \n", training_set.__getitem__(0)[1][:5])

training_set.class_indices

testing_set.class_indices

labels = ['giloma tumor' , 'meningioma tumor' , 'no tumor' , 'pituitary tumor']
sample_data = testing_set.__getitem__(1)[0]
sample_label = testing_set.__getitem__(1)[1]

plt.figure(figsize=(20,20))
for i in range(16):
    plt.subplot(4, 4, i + 1)
    plt.axis('off')
    plt.imshow(sample_data[i])
    plt.title(labels[np.argmax(sample_label[i])])

def display_training_curves(training, validation, title, subplot):
    if subplot%10==1: # set up the subplots on the first call
        plt.subplots(figsize=(10,10), facecolor='#F0F0F0')
        plt.tight_layout()
    ax = plt.subplot(subplot)
    ax.set_facecolor('#F8F8F8')
    ax.plot(training)
    ax.plot(validation)
    ax.set_title('model '+ title)
    ax.set_ylabel(title)
    ax.set_xlabel('epoch')
    ax.legend(['train', 'valid.'])

def categorical_smooth_loss(y_true, y_pred, label_smoothing=0.1):
    loss = tf.keras.losses.categorical_crossentropy(y_true, y_pred, label_smoothing=label_smoothing)
    return loss

lr_reduce = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, epsilon=0.0001, patience=3, verbose=1)
es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, verbose=1)

counter = Counter(training_set.classes)
max_val = float(max(counter.values()))
class_weights = {class_id : max_val/num_images for class_id, num_images in counter.items()}
class_weights

"""**RESNET50V2**"""

print(tf.keras.applications.ResNet50V2(weights='imagenet').input_shape)

pretrained_resnet = tf.keras.applications.ResNet50V2(input_shape=(image_size, image_size, 3), weights='imagenet', include_top=False)

for layer in pretrained_resnet.layers:
  layer.trainable = False

x3 = pretrained_resnet.output
# Added pool_size argument. You can adjust the pool size as needed.
x3 = tf.keras.layers.AveragePooling2D(pool_size=(2, 2), name="averagepooling2d_head")(x3)
x3 = tf.keras.layers.Flatten(name="flatten_head")(x3)
x3 = tf.keras.layers.Dense(128, activation="relu", name="dense_head")(x3)
x3 = tf.keras.layers.Dropout(0.5, name="dropout_head")(x3)
x3 = tf.keras.layers.Dense(64, activation="relu", name="dense_head_2")(x3)
x3 = tf.keras.layers.Dropout(0.5, name="dropout_head_2")(x3)
model_out = tf.keras.layers.Dense(23, activation='softmax', name="predictions_head")(x3)

model_resnet = Model(inputs=pretrained_resnet.input, outputs=model_out)
model_resnet.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),loss=categorical_smooth_loss,metrics=['accuracy'])
# model_vgg.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),loss="categorical_crossentropy",metrics=['accuracy'])
model_resnet.summary()

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.utils import Sequence
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense
from tensorflow.keras.applications import ResNet50
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report, precision_score, recall_score, f1_score
import seaborn as sns
import matplotlib.pyplot as plt

class CustomDataGenerator(Sequence):
    def __init__(self, directory, batch_size=32, target_size=(224, 224), preprocessing_function=None, subset=None):
        self.directory = directory
        self.batch_size = batch_size
        self.target_size = target_size
        self.preprocessing_function = preprocessing_function
        self.image_data_generator = ImageDataGenerator(
            validation_split=0.2  # Use 20% of data for validation
        )
        self.data_generator = self.image_data_generator.flow_from_directory(
            directory,
            target_size=target_size,
            batch_size=batch_size,
            class_mode='categorical',
            subset=subset  # 'training' or 'validation'
        )

    def __len__(self):
        return len(self.data_generator)

    def __getitem__(self, index):
        batch_images, batch_labels = next(self.data_generator)
        if self.preprocessing_function:
            batch_images = self.preprocessing_function(batch_images)
        return batch_images, batch_labels

    def on_epoch_end(self):
        self.data_generator.on_epoch_end()

# Load and adjust ResNet model
base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
x = base_model.output
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
predictions = Dense(4, activation='softmax')(x)  # Number of classes is 4

model_resnet = Model(inputs=base_model.input, outputs=predictions)

# Compile the model
model_resnet.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Custom preprocessing function
def preprocess_data(images):
    # Implement your preprocessing function if needed
    return images

# Create data generators
train_datagen = CustomDataGenerator(
    directory='/content/drive/MyDrive/SRI/SRI_Dataset_Aug/Training_aug',
    target_size=(224, 224),
    preprocessing_function=preprocess_data,
    subset='training'  # Specify training subset
)

validation_datagen = CustomDataGenerator(
    directory='/content/drive/MyDrive/SRI/SRI_Dataset_Aug/Training_aug',
    target_size=(224, 224),
    preprocessing_function=preprocess_data,
    subset='validation'  # Specify validation subset
)

# Define callbacks
lr_reduce = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=3)
es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# Train the model
history_resnet = model_resnet.fit(
    train_datagen,
    validation_data=validation_datagen,
    callbacks=[lr_reduce, es_callback],
    epochs=10
)

def plot_confusion_matrix(cm, class_names):
    plt.figure(figsize=(10, 7))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()

from sklearn.metrics import confusion_matrix, classification_report

# Evaluate the model on the validation set
y_true = []
y_pred = []

for batch_images, batch_labels in validation_datagen:
    predictions = model_resnet.predict(batch_images)
    predicted_labels = np.argmax(predictions, axis=1)
    true_labels = np.argmax(batch_labels, axis=1)

    y_true.extend(true_labels)
    y_pred.extend(predicted_labels)

    if len(y_true) >= validation_datagen.__len__() * validation_datagen.batch_size:
        break

# Compute confusion matrix
cm = confusion_matrix(y_true, y_pred)
class_names = list(validation_datagen.data_generator.class_indices.keys())

# Plot confusion matrix
plot_confusion_matrix(cm, class_names)

# Generate classification report
report = classification_report(y_true, y_pred, target_names=class_names)
print("Classification Report:\n", report)

# Compute precision, recall, and F1 score
precision = precision_score(y_true, y_pred, average='weighted')
recall = recall_score(y_true, y_pred, average='weighted')
f1 = f1_score(y_true, y_pred, average='weighted')

print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1 Score: {f1:.4f}")

def plot_roc_curve(y_true, y_pred, class_names):
    # Binarize the output
    y_true_bin = label_binarize(y_true, classes=range(len(class_names)))
    n_classes = len(class_names)

    # Compute ROC curve and ROC AUC for each class
    fpr = {}
    tpr = {}
    roc_auc = {}

    for i in range(n_classes):
        fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], y_pred[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    # Compute micro-average ROC curve and ROC AUC
    fpr["micro"], tpr["micro"], _ = roc_curve(y_true_bin.ravel(), y_pred.ravel())
    roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

    plt.figure(figsize=(12, 8))

    # Plot ROC curve for each class
    for i in range(n_classes):
        plt.plot(fpr[i], tpr[i], lw=2, label=f'ROC curve of class {class_names[i]} (area = {roc_auc[i]:.2f})')

    # Plot micro-average ROC curve
    plt.plot(fpr["micro"], tpr["micro"], linestyle=':', color='deeppink', label=f'Micro-average ROC curve (area = {roc_auc["micro"]:.2f})')

    plt.plot([0, 1], [0, 1], linestyle='--', color='gray')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC)')
    plt.legend(loc='lower right')
    plt.grid(True)
    plt.show()

from sklearn.metrics import roc_auc_score

# Evaluate the model on the validation set
y_true = []
y_pred = []

for batch_images, batch_labels in validation_datagen:
    predictions = model_resnet.predict(batch_images)
    predicted_probs = predictions  # Probability scores
    true_labels = np.argmax(batch_labels, axis=1)

    y_true.extend(true_labels)
    y_pred.extend(predicted_probs)

    if len(y_true) >= validation_datagen.__len__() * validation_datagen.batch_size:
        break

# Binarize the output
y_true_bin = label_binarize(y_true, classes=range(len(validation_datagen.data_generator.class_indices)))
y_pred_bin = np.array(y_pred)

# Compute ROC-AUC score
roc_auc_scores = {}
for i in range(len(validation_datagen.data_generator.class_indices)):
    roc_auc_scores[i] = roc_auc_score(y_true_bin[:, i], y_pred_bin[:, i])
roc_auc_scores["micro"] = roc_auc_score(y_true_bin.ravel(), y_pred_bin.ravel())

# Print ROC-AUC scores
for i in range(len(validation_datagen.data_generator.class_indices)):
    print(f"ROC AUC score for class {i} ({list(validation_datagen.data_generator.class_indices.keys())[i]}): {roc_auc_scores[i]:.2f}")
print(f"Micro-average ROC AUC score: {roc_auc_scores['micro']:.2f}")

# Plot ROC-AUC curve
class_names = list(validation_datagen.data_generator.class_indices.keys())
plot_roc_curve(y_true_bin, y_pred_bin, class_names)


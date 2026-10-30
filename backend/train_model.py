
from pathlib import Path
import json
import random
import shutil

import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow import keras
from tensorflow.keras import layers

# ---------------- CONFIGURATION ----------------
BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
SPLIT_DIR = BASE_DIR / "dataset_split"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "farmflow_freshness.keras"

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS_HEAD = 5
EPOCHS_FINE_TUNE = 5
SEED = 42

CLASS_NAMES = ["fresh", "stale"]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


def prepare_dataset():
    """Combine the 12 source folders into fresh/stale train/val/test folders."""
    if not DATASET_DIR.is_dir():
        raise FileNotFoundError(
            f"Dataset folder not found: {DATASET_DIR}"
        )

    if SPLIT_DIR.exists():
        shutil.rmtree(SPLIT_DIR)

    files_by_class = {"fresh": [], "stale": []}

    for folder in sorted(DATASET_DIR.iterdir()):
        if not folder.is_dir():
            continue

        name = folder.name.lower()
        if name.startswith("fresh_"):
            label = "fresh"
        elif name.startswith("stale_"):
            label = "stale"
        else:
            print(f"Skipping unrecognized folder: {folder.name}")
            continue

        images = [
            path for path in folder.rglob("*")
            if path.is_file()
            and path.suffix.lower() in VALID_EXTENSIONS
        ]
        files_by_class[label].extend(images)
        print(f"{folder.name}: {len(images)} images")

    for label, files in files_by_class.items():
        if len(files) < 10:
            raise ValueError(
                f"Only {len(files)} images found for '{label}'. "
                "Check your dataset folders and image files."
            )

    # 70% train, 15% validation, 15% test.
    train_files, temp_files, train_y, temp_y = train_test_split(
        files_by_class["fresh"] + files_by_class["stale"],
        [0] * len(files_by_class["fresh"])
        + [1] * len(files_by_class["stale"]),
        test_size=0.30,
        random_state=SEED,
        stratify=(
            [0] * len(files_by_class["fresh"])
            + [1] * len(files_by_class["stale"])
        ),
    )

    val_files, test_files, val_y, test_y = train_test_split(
        temp_files,
        temp_y,
        test_size=0.50,
        random_state=SEED,
        stratify=temp_y,
    )

    splits = [
        ("train", train_files, train_y),
        ("val", val_files, val_y),
        ("test", test_files, test_y),
    ]

    for split_name, paths, labels in splits:
        for path, label_id in zip(paths, labels):
            label_name = CLASS_NAMES[label_id]
            destination_dir = SPLIT_DIR / split_name / label_name
            destination_dir.mkdir(parents=True, exist_ok=True)

            # Unique filenames avoid collisions across source folders.
            unique_name = f"{path.parent.name}_{path.name}"
            destination = destination_dir / unique_name

            # Copy rather than move, preserving the original dataset.
            shutil.copy2(path, destination)

    print("\nDataset split created:")
    for split_name, _, _ in splits:
        for class_name in CLASS_NAMES:
            count = len(
                list((SPLIT_DIR / split_name / class_name).glob("*"))
            )
            print(f"  {split_name}/{class_name}: {count}")


def load_datasets():
    train_ds = keras.utils.image_dataset_from_directory(
        SPLIT_DIR / "train",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="binary",
        shuffle=True,
        seed=SEED,
    )

    val_ds = keras.utils.image_dataset_from_directory(
        SPLIT_DIR / "val",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="binary",
        shuffle=False,
    )

    test_ds = keras.utils.image_dataset_from_directory(
        SPLIT_DIR / "test",
        class_names=CLASS_NAMES,
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="binary",
        shuffle=False,
    )

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)
    test_ds = test_ds.prefetch(autotune)

    return train_ds, val_ds, test_ds


def build_model():
    augmentation = keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.10),
    ], name="augmentation")

    base = keras.applications.MobileNetV2(
        input_shape=(*IMAGE_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = keras.Input(shape=(*IMAGE_SIZE, 3))
    x = augmentation(inputs)
    x = layers.Rescaling(
        scale=1.0 / 127.5,
        offset=-1,
    )(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.25)(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)

    model = keras.Model(inputs, outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model, base


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    prepare_dataset()
    train_ds, val_ds, test_ds = load_datasets()
    model, base = build_model()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=3,
            restore_best_weights=True,
        ),
        keras.callbacks.ModelCheckpoint(
            str(MODEL_PATH),
            monitor="val_loss",
            save_best_only=True,
        ),
    ]

    print("\nPhase 1: training the classification head")
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS_HEAD,
        callbacks=callbacks,
    )

    print("\nPhase 2: fine-tuning MobileNetV2")
    base.trainable = True

    # Fine-tune only the final layers; keep BatchNorm frozen.
    for layer in base.layers[:-30]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-5),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS_FINE_TUNE,
        callbacks=callbacks,
    )

    # Reload the best validation checkpoint before testing.
    model = keras.models.load_model(MODEL_PATH)
    loss, accuracy = model.evaluate(test_ds, verbose=0)
    print(f"\nTest loss: {loss:.4f}")
    print(f"Test accuracy: {accuracy:.4f}")

    y_true = np.concatenate([y.numpy().ravel() for _, y in test_ds])
    probabilities = model.predict(test_ds, verbose=0).ravel()
    y_pred = (probabilities >= 0.5).astype(int)

    print("\nClassification report:")
    print(classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=CLASS_NAMES,
        zero_division=0,
    ))
    print("Confusion matrix (rows=true, columns=predicted):")
    print(confusion_matrix(y_true, y_pred, labels=[0, 1]))

    metadata = {
        "class_names": CLASS_NAMES,
        "image_size": list(IMAGE_SIZE),
        "threshold": 0.5,
        "model_type": "MobileNetV2 transfer learning",
    }
    (MODEL_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"Metadata saved to: {MODEL_DIR / 'metadata.json'}")


if __name__ == "__main__":
    main()

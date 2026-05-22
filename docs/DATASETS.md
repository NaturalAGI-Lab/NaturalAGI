# Datasets

This document describes the `datasets/` directory structure, its purpose, and how it was prepared.

## Overview

The `datasets/` folder contains all image data used for training, testing, and evaluating the NaturalAGI MNIST digit recognition system. The dataset is distributed as `datasets.zip` (32MB) in the repository root and can be unpacked with:

```bash
make unpack_dataset
```

Total size (unpacked): ~91MB

## Directory Structure

```
datasets/
├── train/                        # Active training samples (3.1MB, 805 images)
│   ├── 0_1/   (33 images)
│   ├── 1_1/   (33 images)
│   ├── 1_3/   (44 images)
│   ├── 2_1/   (66 images)
│   ├── 2_2/   (33 images)
│   ├── 3_1/   (36 images)
│   ├── 4_1/   (77 images)
│   ├── 4_2/   (65 images)
│   ├── 5_1/   (66 images)
│   ├── 6_1/   (77 images)
│   ├── 7_1/   (99 images)
│   ├── 8_1/   (88 images)
│   └── 9_2/   (88 images)
│
├── inactive/                     # Inactive subclasses (1.1MB, 286 images)
│   ├── 1_2/   (44 images)
│   ├── 7_2/  (110 images)
│   ├── 8_2/   (55 images)
│   └── 9_1/   (77 images)
│
├── test/                         # Test set (47MB, 12,000 images)
│   ├── 0/ through 9/            (1,200 images each)
│
├── mnist_all/                    # Full MNIST subset (39MB, 10,000 images)
│   ├── 0/   (980 images)
│   ├── 1/  (1,135 images)
│   ├── 2/  (1,032 images)
│   ├── 3/  (1,010 images)
│   ├── 4/    (982 images)
│   ├── 5/    (892 images)
│   ├── 6/    (958 images)
│   ├── 7/  (1,028 images)
│   ├── 8/    (974 images)
│   └── 9/  (1,009 images)
│
├── mnist_all_manifest.csv        # Manifest with annotation status per image
├── mnist_filter.ipynb            # Notebook for filtering/curating MNIST images
├── manual_annotator.ipynb        # Notebook for manual image annotation
└── README.md
```

## Active vs Inactive Subclasses

The digit classes are split into subclasses that represent structurally distinct handwriting styles. The active/inactive split is defined in `src/training/training.ipynb`:

```python
classes_to_subclasses = {
    0: [1],
    1: [1, 3],
    2: [1, 2],
    3: [1],
    4: [1, 2],
    5: [1],
    6: [1],
    7: [1],
    8: [1],
    9: [2],
}
```

**Active** (in `train/`): subclasses used for concept creation and training.
**Inactive** (in `inactive/`): subclasses excluded from training — either redundant, low quality, or not contributing to classification accuracy.

## Naming Convention

Subclass folders use the format `{digit}_{subclass}`, e.g.:
- `1_1` — digit 1, subclass 1 (vertical stroke)
- `1_3` — digit 1, subclass 3 (stroke with serif)
- `4_2` — digit 4, subclass 2 (closed-top variant)

## Manifest

`mnist_all_manifest.csv` contains ~10,000 entries with columns:

| Column | Description |
|--------|-------------|
| `image_path` | Relative path to the PNG image |
| `class` | Digit class (0-9) |
| `structure` | Annotation status: `complete`, `incomplete`, or `unreviewed` |

## How It Was Prepared

1. Raw MNIST images were filtered and curated using `mnist_filter.ipynb`
2. Images were manually annotated for structure quality using `manual_annotator.ipynb` (results in manifest CSV)
3. Training samples were prepared per subclass in `datasets/train/`
4. Active subclasses (matching `classes_to_subclasses`) were copied to `datasets/train/`
5. Remaining subclasses were placed in `datasets/inactive/`
6. The entire `datasets/` folder was packed into `datasets.zip` for version control

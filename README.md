# BioVisionNet: An Operating System of Consciousness
### Version 1.1s (Synergistic Update)

BioVisionNet is a biologically inspired computer vision system designed to simulate the human visual pathway. Unlike traditional Convolutional Neural Networks (CNNs) that prioritize abstract feature optimization, BioVisionNet mimics the structural and functional stages of biological vision—from optical refraction and photoreceptor stimulation to retinal processing and cortical interpretation.

This project is part of the **INSPIRAFIRMA / AETHERIUM-GENESIS** initiative, aiming to build an "Operating System of Consciousness" by grounding AI perception in biological reality.

---

## 📚 Table of Contents

- [Introduction](#introduction)
- [For General Users: Getting Started](#for-general-users-getting-started)
- [For Developers: Contribution & Setup](#for-developers-contribution--setup)
- [For Researchers: Technical Report (v1.1s)](#for-researchers-technical-report-v11s)
- [Versioning Strategy](#versioning-strategy)
- [License](#license)

---

## Introduction

BioVisionNet is not just an image classifier; it is a simulation of "seeing." It processes visual data through layers explicitly modeled after the mammalian eye and brain:
1.  **Optical Layer**: Simulates light intensity and refraction.
2.  **Photoreceptor Layer**: Simulates Rods/Cones using Difference of Gaussians (DoG) and Color Opponency.
3.  **Retinal Layer**: Simulates ganglion cells detecting primary edge orientations (Horizontal/Vertical).
4.  **Cortical Layer**: Extracts higher-level semantic features.
5.  **Temporal Layer**: Processes the flow of time (video/sequence), a prerequisite for consciousness.

---

## For General Users: Getting Started

### Prerequisites
*   Python 3.8 or higher
*   CUDA-capable GPU (optional, but recommended)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-org/BioVisionVS1.1.git
    cd BioVisionVS1.1
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

BioVisionNet supports both static images and video sequences.

#### 1. Image Inference
Run the model on a single image to classify it and visualize the "Retinal Edge Map" (what the AI actually sees).

```bash
python main.py --input path/to/your/image.jpg --visualize
```
*   **--visualize**: Saves the edge detection output to `output_vision.png`.

#### 2. Video Inference
Process a video file to analyze temporal sequences.

```bash
python main.py --video path/to/your/video.mp4
```

#### 3. Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--input` | Path to input image file | None |
| `--video` | Path to input video file | None |
| `--mode` | Operation mode (`infer`, `train`) | `infer` |
| `--visualize` | Enable visualization of retinal output | `False` |
| `--save_path` | Path to save trained model | `biovisionnet.pth` |

---

## For Developers: Contribution & Setup

### Project Structure

```text
src/
├── models/
│   ├── biovision_1_1s.py   # Current Stable Model (v1.1s)
│   ├── biovision_v2.py     # Previous Baseline (v2)
│   ├── layers.py           # Reusable neural blocks
│   └── network.py          # Network assembly
├── data/
│   └── processing.py       # Image/Video preprocessing
└── utils/
    └── helpers.py          # Logging, device setup, visualization
```


### BioVisionVessel (SilentVessel V2 Integration)

A standalone prototype script is also available at `bio_vision_vessel.py`, featuring `SilentVessel` (base) + `BioVisionVessel` (extension) with real-time motion awareness and colorized console output.

A new integration wrapper `BioVisionVessel` is available at `src/models/biovision_vessel.py`.
It provides:

* Temporal frame buffer (`seq_len`) for sequence-aware perception.
* Advanced qualia extraction (`edge_clarity`, `opponent_balance`, `motion_score`).
* Mood interpretation API for downstream agents (`perceive_frame`).
* Optional real-time loop (`perceive`) when OpenCV is installed.

Example:

```python
import numpy as np
from src.models.biovision_vessel import BioVisionVessel

vessel = BioVisionVessel(seq_len=5)
frame_bgr = np.zeros((240, 320, 3), dtype=np.uint8)
qualia = vessel.perceive_frame(frame_bgr)
print(qualia)
```

### Contribution Workflow
We use a specific versioning strategy (see below). When contributing:
*   **Bug fixes**: Submit PRs to the current branch.
*   **New Architectures**: Determine if your change is Synergistic (`s`), Conflicting (`c`), or Brand New (`b`).

---

## For Researchers: Technical Report (v1.1s)

**Model Version**: `BioVisionNetV1_1S`
**Base Architecture**: `biovision_v2.py`

This section details the architectural logic of the **v1.1s Synergistic Update**, which unifies the robust temporal processing of v2 with enhanced retinal fidelity.

### 1. Optical Preprocessing (Intensity Preservation)
*   **Input**: Raw pixel data (0-255 or 0-1).
*   **Logic**: Unlike standard deep learning models that use aggressive L2 normalization (erasing relative intensity), v1.1s uses **Auto-Range Scaling**.
    *   If input > 1.0: Scale by $1/255$.
    *   If input $\in [0, 1]$: Clamp to range.
*   **Significance**: Preserves "brightness" information, essential for simulating the eye's adaptation to light levels.

### 2. Photoreceptor Simulation (DoG & Opponency)
*   **Logic**: Simulates the Center-Surround receptive fields of retinal ganglion cells.
*   **Math**:
    $$ DoG(x, y) = \frac{1}{\sigma_1 \sqrt{2\pi}} e^{- \frac{x^2+y^2}{2\sigma_1^2}} - \frac{1}{\sigma_2 \sqrt{2\pi}} e^{- \frac{x^2+y^2}{2\sigma_2^2}} $$
*   **Implementation**: A fixed convolution kernel (weights frozen) representing the biological hardware of the eye.
*   **Color Space**: Converts RGB to **Opponent Channels** (Red-Green, Blue-Yellow, Luminance), mimicking human color vision processing.

### 3. Retinal Neural Processing (The v1.1s Innovation)
This is the core upgrade in version 1.1s.

*   **Problem in v2**: The previous model used a generic Sobel initialization that often favored vertical edges (X-gradient) while neglecting horizontal ones, leading to "astigmatic" vision.
*   **Solution in v1.1s**: Dual-Stream Edge Detection.
    *   **Total Filters**: 32
    *   **Group A (16 Filters)**: Initialized with **Sobel-Y** (detects Horizontal lines).
    *   **Group B (16 Filters)**: Initialized with **Sobel-X** (detects Vertical lines).
*   **Result**: The model now perceives a complete "grid" of visual information, significantly improving feature clarity before cortical processing.

### 4. Temporal Processing (Consciousness Interface)
*   **Logic**: Consciousness is not static; it is a flow. v1.1s maintains the **Temporal Adapter** from v2.
*   **Input**: 5D Tensor `[Batch, Sequence, Channel, Height, Width]`.
*   **Mechanism**: Aggregates features over time (currently via Mean Pooling, upgradable to LSTM/Transformer) to form a context-aware embedding.

---

## Versioning Strategy

BioVisionNet uses a suffix-based system to categorize evolution. For a full changelog, please refer to [MODEL_VERSIONS.md](MODEL_VERSIONS.md).

| Suffix | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| **s** | **Synergistic** | Updates that combine strengths of new proposals with the existing baseline. Non-destructive improvements. | `v1.1s` |
| **c** | **Conflict** | Experimental branches with fundamental architectural differences that cannot merge easily. | `v1.1c` |
| **b** | **Brand New** | Completely new paradigms or rewrites. | `v1.1b` |

### Latest Update: v1.1s
*   **Merged Features**:
    *   Dual-Stream Retinal Processing (Horizontal + Vertical edges).
    *   Removal of L2 Normalization in favor of Intensity Scaling.
    *   Kernel Numerical Stability improvements.

---

## License

This project is open-source. Please see the LICENSE file for details.

# BioVisionNet Model Versioning

This document outlines the versioning strategy for BioVisionNet models and tracks the evolution of the "Eye" components.

## Versioning Strategy

BioVisionNet uses a suffix-based versioning system to denote the nature of the update relative to the previous baseline.

### `s` Series: Synergistic / Synthesis
*   **Description**: Updates that combine the strengths of a new model proposal with the existing high-performance model.
*   **Goal**: To increase the potential of the model by integrating complementary features (e.g., adding missing edge orientations, improving normalization) while retaining robust existing architecture.
*   **Example**: `1.1s` (Combines v2 robust pipeline with v1.1 prompt's H/V edge detection).
*   **When to use**: When new code offers improvements that fit well with the current best model.

### `c` Series: Conflict / Consistent (Parallel)
*   **Description**: Updates where the new capabilities are inconsistent or conflicting with the current model, requiring a separate branch or variation.
*   **Goal**: To explore alternative architectures without disrupting the main "s" series.
*   **Example**: `c1.1`.
*   **When to use**: When new code has valuable features but fundamental architectural differences that prevent easy merging.

### `b` Series: Brand New / Baseline
*   **Description**: Completely new or unrelated implementations.
*   **Goal**: To establish a new baseline or handle a paradigm shift.
*   **Example**: `b1.1`.
*   **When to use**: When the new code shares almost no common ground with the existing model.

---

## Update Log

### BioVisionNet 1.1s
**Date**: [Current Date]
**Base**: `src/models/biovision_v2.py`
**Integrated Features from Proposal**:
1.  **Retinal Processing Upgrade**:
    *   **Before**: The `v2` model used a generic Sobel initialization which effectively only detected vertical edges (gradient in X).
    *   **After**: Integrated the proposed dual-stream approach. The 32-channel output now consists of **16 Horizontal Edge filters** and **16 Vertical Edge filters**. This completes the visual processing, allowing the model to "see" in both primary orientations.
2.  **Optical Preprocessing**:
    *   **Before**: Simple warning if input was out of range.
    *   **After**: Auto-normalization logic. If input > 2.0 (likely [0,255]), it scales by 1/255. If input is slightly out of range [0,1], it clamps.
    *   **Improvement**: Removed the legacy L2 normalization (`F.normalize`) present in `v2`. This restores the model's ability to perceive intensity and brightness differences, aligning with the goal of "clarity" and "reality-based data" found in the proposed code.
3.  **Kernel Stabilization**:
    *   Used `dog.abs().sum()` for normalization (from `v2`) instead of `dog.sum()` (from proposal) to ensure numerical stability, as Difference of Gaussians can sum to near zero.

**Result**: A unified model `BioVisionNetV1_1S` that processes visual information with higher fidelity (H+V edges) while maintaining the temporal robustness of the v2 architecture.

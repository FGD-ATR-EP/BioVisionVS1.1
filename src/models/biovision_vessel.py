from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple

import numpy as np
import torch

from src.models.biovision_1_1s import BioVisionNetV1_1S


@dataclass
class QualiaState:
    edge_clarity: float
    opponent_balance: float
    motion_score: float
    mood: str


class BioVisionVessel:
    """
    Bio-inspired perception wrapper around BioVisionNet.

    This class keeps a short frame history (temporal dynamics) and exposes
    higher-level "qualia-like" values suitable for reporting and downstream
    integration.
    """

    def __init__(
        self,
        model: Optional[BioVisionNetV1_1S] = None,
        seq_len: int = 5,
        frame_size: Tuple[int, int] = (224, 224),
        device: Optional[torch.device] = None,
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.seq_len = seq_len
        self.frame_size = frame_size

        self.bio_vision_net = model or BioVisionNetV1_1S(num_classes=4)
        self.bio_vision_net.to(self.device)
        self.bio_vision_net.eval()

        self.frame_sequence: Deque[torch.Tensor] = deque(maxlen=self.seq_len)
        self.embedding_sequence: Deque[torch.Tensor] = deque(maxlen=2)

    def _preprocess_for_model(self, frame_bgr: np.ndarray) -> torch.Tensor:
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("Expected frame shape [H, W, 3] in BGR format.")

        frame_rgb = frame_bgr[..., ::-1].copy()
        frame_tensor = torch.from_numpy(frame_rgb).float() / 255.0
        frame_tensor = frame_tensor.permute(2, 0, 1).unsqueeze(0)
        frame_tensor = torch.nn.functional.interpolate(
            frame_tensor,
            size=self.frame_size,
            mode="bilinear",
            align_corners=False,
        )
        return frame_tensor.squeeze(0)

    @staticmethod
    def _opponent_balance(frame_bgr: np.ndarray) -> float:
        b = frame_bgr[..., 0].astype(np.float32)
        g = frame_bgr[..., 1].astype(np.float32)
        r = frame_bgr[..., 2].astype(np.float32)

        rg = np.mean(r - g) / 255.0
        by = np.mean(b - (r + g) / 2.0) / 255.0

        # Positive values = warm RG-dominant, negative = cool BY-dominant
        return float(np.clip(rg - by, -1.0, 1.0))

    def _extract_advanced_qualia(self, frame_bgr: np.ndarray) -> Tuple[float, float, float]:
        frame_tensor = self._preprocess_for_model(frame_bgr)
        self.frame_sequence.append(frame_tensor)

        edge_clarity = 0.0
        motion_score = 0.0

        if len(self.frame_sequence) == self.seq_len:
            input_tensor = torch.stack(list(self.frame_sequence), dim=0).unsqueeze(0).to(self.device)
            with torch.no_grad():
                edge_maps, context_embedding, _ = self.bio_vision_net(input_tensor)

            edge_clarity = float(edge_maps.abs().mean().item())

            self.embedding_sequence.append(context_embedding.squeeze(0).detach().cpu())
            if len(self.embedding_sequence) == 2:
                prev_emb, curr_emb = self.embedding_sequence[0], self.embedding_sequence[1]
                similarity = torch.nn.functional.cosine_similarity(
                    prev_emb.unsqueeze(0), curr_emb.unsqueeze(0)
                ).item()
                motion_score = float(np.clip((1.0 - similarity) * 0.5, 0.0, 1.0))

        opponent_balance = self._opponent_balance(frame_bgr)
        return edge_clarity, opponent_balance, motion_score

    @staticmethod
    def _interpret(edge_clarity: float, opponent_balance: float, motion_score: float) -> str:
        if motion_score > 0.7:
            return "KINETIC / STIMULATED (Motion Awareness)"
        if edge_clarity < 0.2:
            return "BLURRED / UNKNOWN (Lack of Edge Clarity)"
        if opponent_balance > 0.5:
            return "HIGH RG-BALANCE / INTENSE (Warm Tone)"
        if opponent_balance < -0.5:
            return "HIGH BY-BALANCE / CALM (Cool Tone)"
        return "PERCEPTUALLY STABLE"

    def perceive_frame(self, frame_bgr: np.ndarray) -> QualiaState:
        edge_clarity, opponent_balance, motion_score = self._extract_advanced_qualia(frame_bgr)
        mood = self._interpret(edge_clarity, opponent_balance, motion_score)
        return QualiaState(
            edge_clarity=edge_clarity,
            opponent_balance=opponent_balance,
            motion_score=motion_score,
            mood=mood,
        )

    def perceive(self, source: int = 0) -> None:
        """
        Optional real-time loop for webcam/video source.
        Requires OpenCV (`opencv-python`) installed.
        """
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV is required for `perceive`. Install with `pip install opencv-python`."
            ) from exc

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open source: {source}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                qualia = self.perceive_frame(frame)
                status_bar = (
                    f"\r[👁️ Qualia]: Edge:{qualia.edge_clarity:.2f} | "
                    f"OpColor:{qualia.opponent_balance:.2f} | "
                    f"Motion:{qualia.motion_score:.2f} | Sense: {qualia.mood}"
                )
                print(status_bar, end="")

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print()

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, Optional, Tuple

import numpy as np
import torch

from src.models.biovision_1_1s import BioVisionNetV1_1S


@dataclass
class QualiaState:
    edge_clarity: float
    opponent_balance: float
    motion_score: float
    mood: str


@dataclass
class AkashicEnvelope:
    stream: str
    subject: str
    timestamp_utc: str
    payload: Dict[str, float | str]


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
        ema_decay: float = 0.2,
        environment_window: int = 240,
        stream: str = "AetherBusExtreme",
        subject: str = "qualia.state",
    ):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.seq_len = seq_len
        self.frame_size = frame_size

        self.bio_vision_net = model or BioVisionNetV1_1S(num_classes=4)
        self.bio_vision_net.to(self.device)
        self.bio_vision_net.eval()

        self.frame_sequence: Deque[torch.Tensor] = deque(maxlen=self.seq_len)
        self.temporal_embedding: Optional[torch.Tensor] = None
        self.ema_decay = float(np.clip(ema_decay, 0.0, 0.99))

        self.stream = stream
        self.subject = subject
        self.brightness_history: Deque[float] = deque(maxlen=max(30, environment_window))
        self.motion_history: Deque[float] = deque(maxlen=max(30, environment_window))
        self.edge_history: Deque[float] = deque(maxlen=max(30, environment_window))

    def _preprocess_for_model(self, frame_bgr: np.ndarray) -> torch.Tensor:
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("Expected frame shape [H, W, 3] in BGR format.")

        cpu_tensor = torch.from_numpy(frame_bgr)
        if self.device.type == "cuda":
            pinned = torch.empty_like(cpu_tensor, pin_memory=True)
            pinned.copy_(cpu_tensor, non_blocking=False)
            frame_tensor = pinned.to(self.device, non_blocking=True)
        else:
            frame_tensor = cpu_tensor.to(self.device)

        frame_tensor = frame_tensor[..., [2, 1, 0]].permute(2, 0, 1).float().unsqueeze(0) / 255.0
        frame_tensor = torch.nn.functional.interpolate(
            frame_tensor,
            size=self.frame_size,
            mode="bilinear",
            align_corners=False,
        )
        return frame_tensor.squeeze(0)

    @staticmethod
    def _dynamic_limits(history: Deque[float], fallback: Tuple[float, float]) -> Tuple[float, float]:
        if len(history) < 30:
            return fallback
        values = np.asarray(history, dtype=np.float32)
        mean = float(values.mean())
        std = float(values.std() + 1e-6)
        return mean - std, mean + std

    def _observe_environment(self, frame_bgr: np.ndarray, edge_clarity: float, motion_score: float) -> float:
        brightness = float(frame_bgr.mean() / 255.0)
        self.brightness_history.append(brightness)
        self.edge_history.append(edge_clarity)
        self.motion_history.append(motion_score)
        return brightness

    def _build_akashic_envelope(self, qualia: QualiaState) -> AkashicEnvelope:
        return AkashicEnvelope(
            stream=self.stream,
            subject=self.subject,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            payload={
                "edge_clarity": qualia.edge_clarity,
                "opponent_balance": qualia.opponent_balance,
                "motion_score": qualia.motion_score,
                "mood": qualia.mood,
            },
        )

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

            curr_emb = context_embedding.squeeze(0).detach().cpu()
            if self.temporal_embedding is None:
                self.temporal_embedding = curr_emb
            else:
                prev_emb = self.temporal_embedding
                self.temporal_embedding = (1.0 - self.ema_decay) * curr_emb + self.ema_decay * prev_emb
                similarity = torch.nn.functional.cosine_similarity(
                    prev_emb.unsqueeze(0), self.temporal_embedding.unsqueeze(0)
                ).item()
                motion_score = float(np.clip((1.0 - similarity) * 0.5, 0.0, 1.0))

        opponent_balance = self._opponent_balance(frame_bgr)
        return edge_clarity, opponent_balance, motion_score

    def _interpret(
        self,
        edge_clarity: float,
        opponent_balance: float,
        motion_score: float,
        brightness: float,
    ) -> str:
        _, motion_high = self._dynamic_limits(self.motion_history, fallback=(0.0, 0.7))
        edge_low, _ = self._dynamic_limits(self.edge_history, fallback=(0.2, 1.0))
        brightness_low, brightness_high = self._dynamic_limits(self.brightness_history, fallback=(0.12, 0.92))

        if motion_score > max(0.35, motion_high):
            return "KINETIC / STIMULATED (Motion Awareness)"
        if edge_clarity < max(0.05, edge_low):
            return "BLURRED / UNKNOWN (Lack of Edge Clarity)"
        if brightness < brightness_low:
            return "ADAPTED LOW-LIGHT / QUIET"
        if brightness > brightness_high:
            return "ADAPTED HIGH-LIGHT / ALERT"
        if opponent_balance > 0.5:
            return "HIGH RG-BALANCE / INTENSE (Warm Tone)"
        if opponent_balance < -0.5:
            return "HIGH BY-BALANCE / CALM (Cool Tone)"
        return "PERCEPTUALLY STABLE"

    def perceive_frame(self, frame_bgr: np.ndarray) -> QualiaState:
        edge_clarity, opponent_balance, motion_score = self._extract_advanced_qualia(frame_bgr)
        brightness = self._observe_environment(frame_bgr, edge_clarity, motion_score)
        mood = self._interpret(edge_clarity, opponent_balance, motion_score, brightness)
        return QualiaState(
            edge_clarity=edge_clarity,
            opponent_balance=opponent_balance,
            motion_score=motion_score,
            mood=mood,
        )

    def perceive(
        self,
        source: int = 0,
        output_callback: Optional[Callable[[QualiaState], None]] = None,
        bus_publisher: Optional[Callable[[AkashicEnvelope], None]] = None,
    ) -> None:
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
                if output_callback is not None:
                    output_callback(qualia)

                if bus_publisher is not None:
                    bus_publisher(self._build_akashic_envelope(qualia))

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

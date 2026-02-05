from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    cv2 = None

try:
    from colorama import Fore, Style, init
except Exception:  # pragma: no cover - fallback when colorama is unavailable
    class _NoColor:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = RESET = ""

    class _NoStyle:
        BRIGHT = RESET_ALL = ""

    Fore = _NoColor()
    Style = _NoStyle()

    def init(autoreset: bool = True):
        return None

import torch

from src.models.biovision_1_1s import BioVisionNetV1_1S

# Initialize Colorama
init(autoreset=True)


@dataclass
class QualiaState:
    edge_clarity: float
    opponent_balance: float
    motion_score: float
    mood: str


class SilentVessel:
    """
    [Base Class]: The Digital Retina (Original V1)
    """

    def __init__(self):
        self.eye_state = "OPEN"
        print(f"{Fore.CYAN}[SilentVessel]: Retina Initialized. Ready to perceive light.")

    def _calculate_entropy(self, image_gray: np.ndarray) -> float:
        if cv2 is not None:
            histogram = cv2.calcHist([image_gray], [0], None, [256], [0, 256])
            histogram = histogram.ravel()
        else:
            histogram, _ = np.histogram(image_gray.ravel(), bins=256, range=(0, 256))

        histogram = histogram / (histogram.sum() + 1e-7)
        logs = np.log2(histogram + 1e-7)
        entropy = -1 * (histogram * logs).sum()
        return float(entropy)

    def _analyze_color_temp(self, image_bgr: np.ndarray) -> float:
        b = image_bgr[..., 0]
        r = image_bgr[..., 2]
        warmth = (np.mean(r) - np.mean(b)) / 255.0
        return float(warmth)

    def perceive(self, source: int = 0):
        raise NotImplementedError


class BioVisionVessel(SilentVessel):
    """
    [Extension]: Bio-Inspired Vision System
    Simulates BioVisionNet stages (Retina -> Cortex -> Temporal Dynamics)
    while preserving V1 prototype behavior.
    """

    def __init__(
        self,
        seq_len: int = 5,
        frame_size: Tuple[int, int] = (224, 224),
        use_model: bool = True,
        model: Optional[BioVisionNetV1_1S] = None,
        device: Optional[torch.device] = None,
    ):
        super().__init__()

        self.seq_len = seq_len
        self.frame_size = frame_size
        self.frame_sequence: List[np.ndarray] = []
        self.prev_gray: Optional[np.ndarray] = None

        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_model = use_model
        self.bio_vision_net = None

        if self.use_model:
            self.bio_vision_net = model or BioVisionNetV1_1S(num_classes=4)
            self.bio_vision_net.to(self.device)
            self.bio_vision_net.eval()

        print(f"{Fore.MAGENTA}[BioVisionVessel]: BioVisionNet Architecture loaded.")
        print(
            f"{Fore.MAGENTA}[BioVisionVessel]: Temporal Dynamics (SeqLen={self.seq_len}) Activated."
        )

    def _preprocess_for_model(self, frame_bgr: np.ndarray) -> torch.Tensor:
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

    def _calculate_motion_real(self, current_gray: np.ndarray) -> float:
        """
        [Simulation of LSTM Motion Feature]
        Uses frame difference for real prototype-time motion awareness.
        """
        if self.prev_gray is None:
            self.prev_gray = current_gray
            return 0.0

        if cv2 is not None:
            frame_diff = cv2.absdiff(self.prev_gray, current_gray)
        else:
            frame_diff = np.abs(self.prev_gray.astype(np.int16) - current_gray.astype(np.int16)).astype(
                np.uint8
            )

        motion_score = np.mean(frame_diff) / 255.0
        self.prev_gray = current_gray
        return float(min(motion_score * 5.0, 1.0))

    def _calculate_opponent_balance(self, frame_bgr: np.ndarray) -> float:
        b = frame_bgr[..., 0].astype(np.float32)
        g = frame_bgr[..., 1].astype(np.float32)
        r = frame_bgr[..., 2].astype(np.float32)

        rg = np.mean(r - g) / 255.0
        by = np.mean(b - (r + g) / 2.0) / 255.0
        return float(np.clip(rg - by, -1.0, 1.0))

    def _extract_advanced_qualia(self, frame_bgr: np.ndarray) -> Tuple[float, float, float]:
        if cv2 is not None:
            gray_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = np.dot(frame_bgr[..., :3], [0.114, 0.587, 0.299]).astype(np.uint8)

        motion_score = self._calculate_motion_real(gray_frame)

        raw_entropy = self._calculate_entropy(gray_frame)
        edge_clarity = min(raw_entropy / 6.0, 1.0)

        if self.use_model and self.bio_vision_net is not None:
            self.frame_sequence.append(frame_bgr)
            if len(self.frame_sequence) > self.seq_len:
                self.frame_sequence.pop(0)

            if len(self.frame_sequence) == self.seq_len:
                seq_tensors = [self._preprocess_for_model(f) for f in self.frame_sequence]
                input_tensor = torch.stack(seq_tensors, dim=0).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    edge_maps, _, _ = self.bio_vision_net(input_tensor)
                edge_clarity = float(min(edge_maps.abs().mean().item(), 1.0))

        opponent_balance = self._calculate_opponent_balance(frame_bgr)
        return edge_clarity, opponent_balance, motion_score

    @staticmethod
    def _interpret(edge_clarity: float, opponent_balance: float, motion_score: float) -> Tuple[str, str]:
        mood = "BALANCED"
        color_code = Fore.GREEN

        if motion_score > 0.3:
            mood = f"KINETIC / STIMULATED (Motion: {motion_score:.2f})"
            color_code = Fore.YELLOW + Style.BRIGHT
        elif edge_clarity < 0.3:
            mood = "BLURRED / FOGGY (Low Structure)"
            color_code = Fore.BLACK + Style.BRIGHT
        elif opponent_balance > 0.4:
            mood = "INTENSE / WARM (Red-Dominant)"
            color_code = Fore.RED
        elif opponent_balance < -0.4:
            mood = "CALM / COOL (Blue-Dominant)"
            color_code = Fore.BLUE
        else:
            mood = "PERCEPTUALLY STABLE"
            color_code = Fore.CYAN

        return mood, color_code

    def perceive_frame(self, frame_bgr: np.ndarray) -> QualiaState:
        edge_clarity, opponent_balance, motion_score = self._extract_advanced_qualia(frame_bgr)
        mood, _ = self._interpret(edge_clarity, opponent_balance, motion_score)
        return QualiaState(edge_clarity, opponent_balance, motion_score, mood)

    def perceive(self, source: int = 0):
        if cv2 is None:
            raise RuntimeError(
                "OpenCV is required for realtime `perceive`. Install with: pip install opencv-python"
            )

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"{Fore.RED}[Error]: Cannot open the Eye.")
            return

        print(f"{Fore.GREEN}[BioVisionVessel]: Connecting to Visual Cortex... Online.")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                small_frame = cv2.resize(frame, (320, 240))
                edge_clarity, opponent_balance, motion_score = self._extract_advanced_qualia(small_frame)
                mood, color_code = self._interpret(edge_clarity, opponent_balance, motion_score)

                status_bar = (
                    f"\r[🧠 BioVision]: "
                    f"Edge:{edge_clarity:.2f} | "
                    f"OpColor:{opponent_balance:.2f} | "
                    f"Motion:{motion_score:.2f} | "
                    f"State: {color_code}{mood}{Style.RESET_ALL}      "
                )
                print(status_bar, end="")

                if cv2.waitKey(50) & 0xFF == ord("q"):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print(f"\n{Fore.MAGENTA}[BioVisionVessel]: Disconnecting Neural Pathways.")


if __name__ == "__main__":
    vessel = BioVisionVessel()
    vessel.perceive()

"""
============================================================
  LIBRAS Bridge
  Arquivo: src/core/sign_recognizer.py
  Descricao: Pipeline MediaPipe + Classificador ML com
             suavizacao temporal por votacao e threshold
             de confiança — elimina o "piscar" de sinais.
============================================================
"""

import os
import pickle
import threading
import urllib.request
from collections import deque, Counter
from typing import Optional, Callable

import numpy as np

HAND_LANDMARKER_PATH = "models/hand_landmarker.task"
HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MAX_HANDS = 2
TOTAL_FEATURES = MAX_HANDS * 21 * 3  # 126


# ──────────────────────────────────────────────────────────
#  CONFIGURAÇÕES DE SUAVIZAÇÃO — ajuste aqui se necessário
# ──────────────────────────────────────────────────────────
class SmoothingConfig:
    # Tamanho do buffer de votação (frames analisados)
    BUFFER_SIZE: int = 20

    # Quantos frames do buffer precisam concordar para confirmar (0.0–1.0)
    # Ex: 0.65 = 65% dos frames precisam votar no mesmo sinal
    VOTE_THRESHOLD: float = 0.65

    # Confiança mínima do modelo por frame (0.0–1.0)
    # Frames abaixo desse valor são ignorados no buffer
    MIN_CONFIDENCE: float = 0.70

    # Frames consecutivos sem detecção para resetar o estado
    NO_HAND_RESET_FRAMES: int = 15

    # Cooldown em frames após confirmar uma palavra (evita repetição imediata)
    CONFIRMATION_COOLDOWN: int = 30


class TemporalSmoother:
    """
    Buffer de votação por janela deslizante.

    Coleta predições frame a frame e só confirma uma palavra
    quando a mesma classe aparece em >= VOTE_THRESHOLD do buffer
    E com confiança média >= MIN_CONFIDENCE.
    """

    def __init__(self, cfg: SmoothingConfig = SmoothingConfig()):
        self.cfg = cfg
        self._buffer: deque = deque(maxlen=cfg.BUFFER_SIZE)
        self._no_hand_count: int = 0
        self._cooldown_count: int = 0
        self._last_confirmed: Optional[str] = None

    def reset(self) -> None:
        self._buffer.clear()
        self._no_hand_count = 0
        self._cooldown_count = 0
        self._last_confirmed = None

    def update(
        self,
        label: Optional[str],
        confidence: float,
        hand_detected: bool,
    ) -> Optional[str]:
        """
        Recebe a predição do frame atual.
        Retorna o sinal confirmado ou None se ainda não há consenso.

        Parâmetros
        ----------
        label       : classe predita pelo modelo (ou None se sem mão)
        confidence  : probabilidade da classe predita (0.0–1.0)
        hand_detected: True se MediaPipe detectou mão no frame
        """

        # ── Sem mão detectada ───────────────────────────────────
        if not hand_detected or label is None:
            self._no_hand_count += 1
            if self._no_hand_count >= self.cfg.NO_HAND_RESET_FRAMES:
                self._buffer.clear()
                self._last_confirmed = None
                self._cooldown_count = 0
            return None

        self._no_hand_count = 0

        # ── Cooldown após confirmação ───────────────────────────
        if self._cooldown_count > 0:
            self._cooldown_count -= 1
            return None

        # ── Descarta frames com confiança baixa ─────────────────
        if confidence < self.cfg.MIN_CONFIDENCE:
            return None

        # ── Adiciona ao buffer ──────────────────────────────────
        self._buffer.append(label)

        # Ainda não temos frames suficientes para votar
        if len(self._buffer) < self.cfg.BUFFER_SIZE:
            return None

        # ── Votação ─────────────────────────────────────────────
        counts = Counter(self._buffer)
        top_label, top_count = counts.most_common(1)[0]
        vote_ratio = top_count / len(self._buffer)

        if vote_ratio >= self.cfg.VOTE_THRESHOLD:
            # Evita confirmar a mesma palavra em sequência imediata
            if top_label == self._last_confirmed:
                return None

            self._last_confirmed = top_label
            self._buffer.clear()
            self._cooldown_count = self.cfg.CONFIRMATION_COOLDOWN
            return top_label

        return None

    @property
    def buffer_fill(self) -> float:
        """Progresso do buffer (0.0–1.0) — útil para barra de progresso na UI."""
        return len(self._buffer) / self.cfg.BUFFER_SIZE

    @property
    def current_candidate(self) -> Optional[str]:
        """Sinal mais votado no buffer atual (para feedback visual em tempo real)."""
        if not self._buffer:
            return None
        return Counter(self._buffer).most_common(1)[0][0]


# ──────────────────────────────────────────────────────────
#  RECONHECEDOR PRINCIPAL
# ──────────────────────────────────────────────────────────
class SignRecognizer:
    """
    Orquestra MediaPipe HandLandmarker + classificador ML
    com suavização temporal.

    Uso
    ---
    recognizer = SignRecognizer()
    recognizer.load_model("models/sign_classifier.pkl")

    # A cada frame BGR da câmera:
    result = recognizer.process_frame(bgr_frame)
    # result.confirmed_word  → palavra confirmada (ou None)
    # result.candidate       → sinal mais provável no momento
    # result.confidence      → confiança da predição atual
    # result.buffer_progress → 0.0–1.0 para barra de progresso
    # result.hand_detected   → bool
    """

    class FrameResult:
        __slots__ = ("confirmed_word", "candidate", "confidence",
                     "buffer_progress", "hand_detected", "landmarks_drawn")

        def __init__(self):
            self.confirmed_word: Optional[str] = None
            self.candidate: Optional[str] = None
            self.confidence: float = 0.0
            self.buffer_progress: float = 0.0
            self.hand_detected: bool = False
            self.landmarks_drawn = None  # frame BGR com landmarks desenhados

    def __init__(
        self,
        smoothing_cfg: SmoothingConfig = SmoothingConfig(),
        on_word_confirmed: Optional[Callable[[str], None]] = None,
    ):
        self._cfg = smoothing_cfg
        self._on_word_confirmed = on_word_confirmed
        self._smoother = TemporalSmoother(smoothing_cfg)
        self._model = None
        self._labels: list[str] = []
        self._landmarker = None
        self._mp = None
        self._lock = threading.Lock()
        self._demo_mode = True

    # ── Carregamento ────────────────────────────────────────

    def load_model(self, path: str = "models/sign_classifier.pkl") -> bool:
        """Carrega o modelo treinado. Retorna True em caso de sucesso."""
        if not os.path.exists(path):
            print(f"[SignRecognizer] Modelo não encontrado: {path} — modo demo ativo.")
            return False
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._model = data["model"]
            self._labels = data["labels"]
            self._demo_mode = False
            acc = data.get("accuracy", 0.0)
            print(f"[SignRecognizer] Modelo carregado: {data.get('model_name','?')} "
                  f"| Acurácia: {acc*100:.1f}% | Sinais: {self._labels}")
            return True
        except Exception as e:
            print(f"[SignRecognizer] Erro ao carregar modelo: {e}")
            return False

    def init_mediapipe(self) -> bool:
        """Inicializa o HandLandmarker. Baixa o .task se necessário."""
        try:
            if not self._ensure_task_downloaded():
                return False
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.vision import (
                HandLandmarker, HandLandmarkerOptions, RunningMode
            )
            from mediapipe.tasks.python.core.base_options import BaseOptions

            opts = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=HAND_LANDMARKER_PATH),
                running_mode=RunningMode.IMAGE,
                num_hands=MAX_HANDS,
                min_hand_detection_confidence=0.7,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._landmarker = HandLandmarker.create_from_options(opts)
            self._mp = mp
            print("[SignRecognizer] MediaPipe HandLandmarker pronto.")
            return True
        except Exception as e:
            print(f"[SignRecognizer] Erro ao inicializar MediaPipe: {e}")
            return False

    # ── Processamento de frame ───────────────────────────────

    def process_frame(self, bgr_frame) -> "SignRecognizer.FrameResult":
        """
        Processa um frame BGR e retorna FrameResult.
        Thread-safe via lock interno.
        """
        result = self.FrameResult()

        if self._demo_mode:
            return self._demo_process(bgr_frame, result)

        with self._lock:
            try:
                import mediapipe as mp
                rgb = self._mp.Image(
                    image_format=self._mp.ImageFormat.SRGB,
                    data=bgr_frame[:, :, ::-1].copy()
                )
                detection = self._landmarker.detect(rgb)
                result.hand_detected = bool(detection.hand_landmarks)

                label, confidence = None, 0.0

                if result.hand_detected:
                    features = self._extract_features(detection)
                    if features is not None:
                        probas = self._model.predict_proba([features])[0]
                        idx = int(np.argmax(probas))
                        confidence = float(probas[idx])
                        label = self._labels[idx]

                result.confidence = confidence
                result.candidate = label

                confirmed = self._smoother.update(label, confidence, result.hand_detected)
                result.confirmed_word = confirmed
                result.buffer_progress = self._smoother.buffer_fill

                if confirmed and self._on_word_confirmed:
                    self._on_word_confirmed(confirmed)

                # Desenha landmarks no frame
                result.landmarks_drawn = self._draw_landmarks(bgr_frame, detection)

            except Exception as e:
                print(f"[SignRecognizer] Erro no frame: {e}")

        return result

    # ── Helpers privados ─────────────────────────────────────

    def _extract_features(self, detection) -> Optional[np.ndarray]:
        if not detection.hand_landmarks:
            return None
        all_feat = []
        for hand_lms in detection.hand_landmarks[:MAX_HANDS]:
            arr = np.array([[lm.x, lm.y, lm.z] for lm in hand_lms], dtype=np.float32)
            arr -= arr[0]
            mx = np.max(np.abs(arr))
            if mx > 0:
                arr /= mx
            all_feat.append(arr.flatten())
        fv = np.concatenate(all_feat)
        if len(fv) < TOTAL_FEATURES:
            fv = np.concatenate([fv, np.zeros(TOTAL_FEATURES - len(fv), dtype=np.float32)])
        return fv

    def _draw_landmarks(self, frame, detection):
        """Desenha os pontos das mãos no frame — cópia segura."""
        import cv2
        out = frame.copy()
        if not detection.hand_landmarks:
            return out
        h, w = out.shape[:2]
        for hand_lms in detection.hand_landmarks:
            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms]
            # Conexões básicas entre os pontos
            CONNECTIONS = [
                (0,1),(1,2),(2,3),(3,4),        # polegar
                (0,5),(5,6),(6,7),(7,8),         # indicador
                (0,9),(9,10),(10,11),(11,12),    # médio
                (0,13),(13,14),(14,15),(15,16),  # anelar
                (0,17),(17,18),(18,19),(19,20),  # mínimo
                (5,9),(9,13),(13,17),            # palma
            ]
            for a, b in CONNECTIONS:
                cv2.line(out, pts[a], pts[b], (0, 220, 120), 2)
            for pt in pts:
                cv2.circle(out, pt, 4, (255, 255, 255), -1)
                cv2.circle(out, pt, 4, (0, 180, 80), 1)
        return out

    @staticmethod
    def _ensure_task_downloaded() -> bool:
        os.makedirs("models", exist_ok=True)
        if os.path.exists(HAND_LANDMARKER_PATH):
            return True
        print("[SignRecognizer] Baixando hand_landmarker.task (~9 MB)...")
        try:
            def hook(b, bs, total):
                if total > 0:
                    print(f"\r  {min(b*bs*100/total,100):.0f}%", end="", flush=True)
            urllib.request.urlretrieve(HAND_LANDMARKER_URL, HAND_LANDMARKER_PATH, reporthook=hook)
            print("\n[SignRecognizer] Download concluído.")
            return True
        except Exception as e:
            print(f"\n[SignRecognizer] Falha no download: {e}")
            return False

    def _demo_process(self, frame, result: "SignRecognizer.FrameResult"):
        """Modo demo: simula detecções para testar a interface."""
        import cv2, random
        result.landmarks_drawn = frame.copy()
        cv2.putText(result.landmarks_drawn, "MODO DEMO — sem modelo treinado",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
        return result

    # ── Controle público ─────────────────────────────────────

    def reset(self) -> None:
        """Reseta o buffer de suavização (use ao limpar a frase na UI)."""
        self._smoother.reset()

    def close(self) -> None:
        """Libera recursos do MediaPipe."""
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass

    @property
    def is_demo_mode(self) -> bool:
        return self._demo_mode

    @property
    def labels(self) -> list[str]:
        return list(self._labels)
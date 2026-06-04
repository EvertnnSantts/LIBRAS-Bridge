"""
============================================================
  LIBRAS Bridge
  Arquivo: src/modules/patient/patient_module.py
============================================================
"""

import logging
from typing import Optional, Callable

import cv2
import numpy as np
from PIL import Image, ImageTk

from src.core.camera_capture import CameraCapture
from src.core.sign_recognizer import SignRecognizer, SmoothingConfig
from src.core.tts_engine import TTSEngine
from src.utils.config import AppConfig


class PatientModule:

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        tts_engine: TTSEngine,
        on_word_detected: Optional[Callable[[str], None]] = None,
        on_frame_ready: Optional[Callable] = None
    ) -> None:
        self._config = config
        self._logger = logger
        self._tts = tts_engine
        self._on_word_detected = on_word_detected
        self._on_frame_ready = on_frame_ready

        self._camera = CameraCapture(config=config, logger=logger)

        smoothing = SmoothingConfig()
        smoothing.MIN_CONFIDENCE = config.SIGN_CONFIDENCE_THRESHOLD
        self._recognizer = SignRecognizer(smoothing_cfg=smoothing)
        self._recognizer.load_model(config.MODEL_PATH)

        if not self._recognizer.is_demo_mode:
            self._recognizer.init_mediapipe()

        self._current_sentence: list[str] = []
        self._is_active: bool = False
        self._update_job = None

        self._logger.info("PatientModule inicializado.")

    def start(self, root_widget) -> bool:
        if not self._camera.open():
            self._logger.error("PatientModule: falha ao abrir câmera.")
            return False

        self._camera.start()
        self._is_active = True
        self._root_widget = root_widget
        self._schedule_update()

        self._logger.info("PatientModule iniciado.")
        return True

    def _schedule_update(self) -> None:
        if self._is_active and hasattr(self, "_root_widget"):
            self._update_job = self._root_widget.after(
                self._config.CAMERA_UPDATE_INTERVAL_MS,
                self._process_frame
            )

    def _process_frame(self) -> None:
        if not self._is_active:
            return

        frame = self._camera.get_frame()

        if frame is not None and isinstance(frame, np.ndarray) and frame.size > 0:
            try:
                frame_result = self._recognizer.process_frame(frame)

                if frame_result.confirmed_word:
                    self._handle_confirmed_sign(frame_result.confirmed_word)

                display_frame = (
                    frame_result.landmarks_drawn
                    if frame_result.landmarks_drawn is not None
                    and isinstance(frame_result.landmarks_drawn, np.ndarray)
                    and frame_result.landmarks_drawn.size > 0
                    else frame
                )
                self._update_camera_display(display_frame)
            except Exception as e:
                self._logger.error(f"Erro ao processar frame: {e}")

        self._schedule_update()

    def _handle_confirmed_sign(self, sign: str) -> None:
        self._current_sentence.append(sign)
        self._logger.info(f"Palavra reconhecida: '{sign}'")

        if self._on_word_detected:
            full_sentence = " ".join(self._current_sentence)
            self._on_word_detected(full_sentence)

        self._tts.speak(sign)

    def _update_camera_display(self, frame: np.ndarray) -> None:
        if self._on_frame_ready is None:
            return

        # Valida o frame antes de qualquer operação
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return

        try:
            # Garante que o frame tem 3 canais (BGR) antes de converter
            if len(frame.shape) == 2:
                # Frame em escala de cinza — converte para BGR primeiro
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                # Frame BGRA — remove canal alpha
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            pil_image = pil_image.resize((640, 480), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image=pil_image)
            self._on_frame_ready(photo)
        except Exception as e:
            self._logger.error(f"Erro ao converter frame para exibição: {e}")

    def clear_sentence(self) -> None:
        self._current_sentence.clear()
        self._recognizer.reset()
        self._logger.debug("Frase do paciente limpa.")

    def speak_sentence(self) -> None:
        if self._current_sentence:
            full_sentence = " ".join(self._current_sentence)
            self._tts.speak(full_sentence)
            self._logger.info(f"Falando frase completa: '{full_sentence}'")

    def get_current_sentence(self) -> str:
        return " ".join(self._current_sentence)

    def stop(self) -> None:
        self._is_active = False

        if self._update_job and hasattr(self, "_root_widget"):
            self._root_widget.after_cancel(self._update_job)
            self._update_job = None

        self._camera.stop()
        self._recognizer.close()

        self._logger.info("PatientModule parado e recursos liberados.")
"""
============================================================
  LIBRAS Bridge
  Arquivo: src/core/camera_capture.py
  Descrição: Gerencia a captura de vídeo da webcam usando
             OpenCV. Abstrai toda a lógica de abertura,
             leitura e liberação da câmera.

  CORREÇÃO (v2):
    - Reiniciar a câmera (stop → open → start) falhava porque:
        1. stop() setava _is_running=False mas a thread anterior
           podia ainda estar rodando quando open()/start() eram
           chamados, causando condição de corrida.
        2. Os flags internos (_camera_opened) não eram resetados
           corretamente antes de reabrir.
    - Solução:
        * stop() agora aguarda a thread anterior encerrar (join)
          ANTES de liberar o VideoCapture.
        * open() reseta todos os flags de estado antes de tentar
          abrir a câmera novamente.
        * start() verifica se uma thread anterior ainda está viva
          e a aguarda antes de criar a nova.
============================================================
"""

import logging
import threading
from typing import Optional

import cv2
import numpy as np

from src.utils.config import AppConfig


class CameraCapture:
    """
    Gerencia o ciclo de vida da câmera com suporte a reinicialização.

    Garante que stop() → open() → start() funcione quantas vezes
    for necessário sem deixar threads zumbis ou VideoCapture abertos.
    """

    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._is_running: bool = False
        self._capture_thread: Optional[threading.Thread] = None
        self._camera_opened: bool = False

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """
        Abre a câmera e configura os parâmetros de captura.
        Pode ser chamado novamente após stop() para reiniciar.

        Returns:
            True se a câmera foi aberta com sucesso, False caso contrário
        """
        # Reseta o estado anterior antes de tentar abrir novamente.
        # Necessário para reinicializações — sem isso, flags velhos
        # bloqueavam a reabertura.
        self._camera_opened = False
        self._current_frame = None

        # Garante que qualquer VideoCapture anterior foi liberado
        if self._cap is not None:
            self._cap.release()
            self._cap = None

        try:
            self._cap = cv2.VideoCapture(self._config.CAMERA_INDEX)

            if not self._cap.isOpened():
                self._logger.error(
                    f"Não foi possível abrir a câmera índice {self._config.CAMERA_INDEX}. "
                    "Verifique se a câmera está conectada e não está em uso."
                )
                return False

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.CAMERA_HEIGHT)
            self._cap.set(cv2.CAP_PROP_FPS, self._config.CAMERA_FPS)

            actual_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS)

            self._logger.info(
                f"Câmera aberta: {actual_width:.0f}x{actual_height:.0f} @ {actual_fps:.0f}fps"
            )

            self._camera_opened = True
            return True

        except Exception as e:
            self._logger.error(f"Erro ao abrir câmera: {e}")
            return False

    def start(self) -> None:
        """
        Inicia a thread de captura contínua de frames.

        Aguarda a thread anterior encerrar (se houver) antes de criar
        a nova, evitando condições de corrida em reinicializações.
        """
        if not self._camera_opened:
            self._logger.warning("Câmera não está aberta. Chame open() antes de start().")
            return

        # Se uma thread anterior ainda estiver viva (ex: stop() chamado
        # muito rapidamente), aguarda ela terminar antes de criar a nova.
        if self._capture_thread and self._capture_thread.is_alive():
            self._logger.debug("Aguardando thread de captura anterior encerrar...")
            self._capture_thread.join(timeout=3.0)

        self._is_running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="CaptureThread",
            daemon=True,
        )
        self._capture_thread.start()
        self._logger.info("Thread de captura de câmera iniciada.")

    def _capture_loop(self) -> None:
        """
        Loop de captura executado na thread separada.
        Lê frames continuamente e os disponibiliza via get_frame().
        """
        while self._is_running:
            if self._cap is None or not self._cap.isOpened():
                break

            ret, frame = self._cap.read()

            if not ret:
                self._logger.warning("Falha ao ler frame da câmera.")
                continue

            # Espelha horizontalmente (efeito espelho — importante para LIBRAS)
            frame = cv2.flip(frame, 1)

            with self._frame_lock:
                self._current_frame = frame.copy()

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Retorna o frame mais recente capturado.
        Thread-safe.

        Returns:
            np.ndarray BGR ou None se não houver frame disponível
        """
        with self._frame_lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
            return None

    def stop(self) -> None:
        """
        Para a thread de captura e libera os recursos da câmera.

        A ordem importa:
          1. Sinaliza a thread para parar (_is_running = False)
          2. Aguarda a thread encerrar (join) — ANTES de liberar o cap
          3. Libera o VideoCapture
          4. Reseta flags

        Sem o join antes do release, a thread ainda em execução poderia
        tentar ler de um VideoCapture já liberado, causando crash ou
        dados corrompidos no reconhecimento ao religar.
        """
        # 1. Sinaliza parada
        self._is_running = False

        # 2. Aguarda a thread encerrar ANTES de liberar a câmera
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        # 3. Libera o VideoCapture
        if self._cap is not None:
            self._cap.release()
            self._cap = None

        # 4. Reseta flags
        self._camera_opened = False

        # Limpa o frame armazenado para que get_frame() retorne None
        # até o próximo open()/start() — evita que o reconhecedor
        # processe um frame antigo após a reinicialização
        with self._frame_lock:
            self._current_frame = None

        self._logger.info("Câmera liberada.")

    # ------------------------------------------------------------------
    # Propriedade de estado
    # ------------------------------------------------------------------

    @property
    def is_opened(self) -> bool:
        """Retorna True se a câmera está aberta e funcionando."""
        return self._camera_opened and self._cap is not None and self._cap.isOpened()
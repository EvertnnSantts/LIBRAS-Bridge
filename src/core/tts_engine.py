"""
============================================================
  LIBRAS Bridge
  Arquivo: src/core/tts_engine.py
  Descrição: Motor de Text-to-Speech (TTS) para converter
             palavras/frases reconhecidas em LIBRAS para áudio
             falado, permitindo que o médico ouça o que o
             paciente está comunicando.

  BIBLIOTECA: pyttsx3
    - Funciona offline (sem necessidade de internet)
    - Suporta múltiplos idiomas (incluindo pt-BR com vozes instaladas)
    - Compatível com Windows (SAPI5), macOS (NSSpeechSynthesizer)
      e Linux (eSpeak)

  CORREÇÃO (v2):
    - pyttsx3 não é thread-safe: chamar runAndWait() de threads
      diferentes corrompe o estado interno do engine. A solução
      é manter UMA única thread dedicada ao TTS que fica viva
      durante toda a execução, consumindo textos de uma fila
      (queue.Queue). Isso resolve:
        1. Palavras sendo ignoradas após a primeira
        2. "Falar Frase" não funcionando
============================================================
"""

import logging
import queue
import threading
from typing import Optional

import pyttsx3


# Sentinela usada para encerrar a thread TTS de forma limpa
_STOP_SENTINEL = object()


class TTSEngine:
    """
    Wrapper em torno do pyttsx3 para síntese de fala thread-safe.

    Usa uma fila (queue.Queue) + uma única thread dedicada para garantir
    que o engine pyttsx3 seja sempre acessado a partir do mesmo thread,
    evitando o bug de estado corrompido que fazia apenas a primeira
    palavra ser falada.
    """

    def __init__(self, config, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger
        self._initialized: bool = False
        self._engine: Optional[pyttsx3.Engine] = None

        # Fila de textos a serem falados.
        # A thread TTS consome desta fila; speak() apenas enfileira.
        self._queue: queue.Queue = queue.Queue()

        # Thread única e persistente que roda o loop do pyttsx3
        self._tts_thread: Optional[threading.Thread] = None

        self._initialize_engine()

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

    def _initialize_engine(self) -> None:
        """Instancia e configura o engine pyttsx3, depois inicia a thread."""
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._config.TTS_RATE)
            self._engine.setProperty("volume", self._config.TTS_VOLUME)

            voices = self._engine.getProperty("voices")
            if voices and len(voices) > self._config.TTS_VOICE_INDEX:
                self._engine.setProperty(
                    "voice",
                    voices[self._config.TTS_VOICE_INDEX].id,
                )
                self._logger.info(
                    f"Voz TTS selecionada: {voices[self._config.TTS_VOICE_INDEX].name}"
                )
            else:
                self._logger.warning(
                    f"Voz índice {self._config.TTS_VOICE_INDEX} não disponível. "
                    "Usando voz padrão."
                )

            self._initialized = True

            # Inicia a thread dedicada APÓS o engine estar configurado
            self._tts_thread = threading.Thread(
                target=self._tts_loop,
                name="TTSThread",
                daemon=True,  # encerra automaticamente com o programa
            )
            self._tts_thread.start()

            self._logger.info("TTSEngine inicializado com sucesso.")

        except Exception as e:
            self._logger.error(f"Falha ao inicializar TTS: {e}")
            self._initialized = False

    # ------------------------------------------------------------------
    # Loop interno (roda na thread dedicada)
    # ------------------------------------------------------------------

    def _tts_loop(self) -> None:
        """
        Loop que fica vivo durante toda a execução do programa.
        Bloqueia em queue.get() aguardando o próximo texto.
        Quando recebe o sentinela _STOP_SENTINEL, encerra.

        POR QUE ISSO RESOLVE O PROBLEMA:
          O pyttsx3 exige que say() + runAndWait() sejam chamados
          sempre a partir da MESMA thread onde o engine foi criado.
          Antes, cada chamada a speak() criava uma thread nova —
          o engine recebia runAndWait() de threads diferentes e
          corrompía seu estado após a primeira fala.
          Aqui, apenas esta thread chama o engine, para sempre.
        """
        while True:
            try:
                # Bloqueia até haver algo na fila (sem consumir CPU)
                text = self._queue.get()

                # Verifica se deve encerrar
                if text is _STOP_SENTINEL:
                    break

                # Fala o texto — sempre na mesma thread
                self._engine.say(text)
                self._engine.runAndWait()
                self._logger.debug(f"TTS falou: '{text}'")

            except RuntimeError as e:
                self._logger.error(f"Erro de runtime no TTS: {e}")
            except Exception as e:
                self._logger.error(f"Erro inesperado no TTS: {e}")
            finally:
                # Marca a tarefa como concluída para queue.join() funcionar
                try:
                    self._queue.task_done()
                except ValueError:
                    pass  # task_done() sem get() pendente — seguro ignorar

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def speak(self, text: str) -> None:
        """
        Enfileira o texto para ser falado.
        Retorna imediatamente — não bloqueia a GUI.

        Args:
            text: O texto a ser falado em português
        """
        if not text or not text.strip():
            return
        if not self._initialized:
            self._logger.warning("TTS não disponível. Texto ignorado.")
            return

        # Apenas enfileira; a thread dedicada cuida do resto
        self._queue.put(text.strip())

    def shutdown(self) -> None:
        """
        Encerra a thread TTS de forma limpa.
        Chame ao fechar a aplicação.
        """
        if self._initialized and self._tts_thread and self._tts_thread.is_alive():
            self._queue.put(_STOP_SENTINEL)
            self._tts_thread.join(timeout=3.0)
            self._logger.info("TTSEngine encerrado.")

    def list_available_voices(self) -> list:
        """
        Retorna a lista de vozes disponíveis no sistema.

        Returns:
            Lista de strings 'índice: nome' de cada voz disponível
        """
        if not self._initialized or self._engine is None:
            return []
        try:
            voices = self._engine.getProperty("voices")
            return [f"{i}: {v.name}" for i, v in enumerate(voices)]
        except Exception as e:
            self._logger.error(f"Erro ao listar vozes: {e}")
            return []

    def set_rate(self, rate: int) -> None:
        """
        Altera a taxa de fala em tempo real (palavras por minuto).

        Args:
            rate: Nova taxa (sugerido: 100–200)
        """
        if self._initialized and self._engine:
            self._engine.setProperty("rate", rate)
            self._logger.debug(f"Taxa TTS alterada para: {rate} wpm")

    def set_volume(self, volume: float) -> None:
        """
        Altera o volume em tempo real.

        Args:
            volume: Novo volume (0.0 a 1.0)
        """
        if self._initialized and self._engine:
            volume = max(0.0, min(1.0, volume))
            self._engine.setProperty("volume", volume)
            self._logger.debug(f"Volume TTS alterado para: {volume}")
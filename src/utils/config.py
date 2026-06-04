"""
============================================================
  LIBRAS Bridge
  Arquivo: src/utils/config.py
  Descrição: Configurações globais da aplicação.
             Centraliza todas as constantes e parâmetros
             configuráveis em um único lugar (princípio
             DRY - Don't Repeat Yourself).
============================================================
"""

# --- Importações da Biblioteca Padrão ---
from dataclasses import dataclass, field   # dataclass: cria classes de dados sem boilerplate
from typing import Tuple                   # Tuple: usado para anotações de tipo de tuplas


@dataclass
class AppConfig:
    """
    Classe de configuração principal da aplicação.
    Usa @dataclass para geração automática de __init__, __repr__, etc.
    Todos os atributos têm valores padrão para funcionar sem configuração externa.
    """

    # -------------------------------------------------------
    # CONFIGURAÇÕES DA JANELA PRINCIPAL
    # -------------------------------------------------------

    # Largura inicial da janela em pixels
    WINDOW_WIDTH: int = 1280

    # Altura inicial da janela em pixels
    WINDOW_HEIGHT: int = 800

    # Largura mínima permitida ao redimensionar (evita quebrar o layout)
    MIN_WIDTH: int = 900

    # Altura mínima permitida ao redimensionar
    MIN_HEIGHT: int = 600

    # -------------------------------------------------------
    # CONFIGURAÇÕES DA CÂMERA (Módulo Paciente)
    # -------------------------------------------------------

    # Índice da câmera a ser usada pelo OpenCV
    # 0 = webcam padrão do sistema; 1, 2... = câmeras adicionais
    CAMERA_INDEX: int = 0

    # Largura de captura do frame da câmera em pixels
    # Valores comuns: 640, 1280. Menor = mais rápido, maior = mais preciso
    CAMERA_WIDTH: int = 640

    # Altura de captura do frame da câmera em pixels
    CAMERA_HEIGHT: int = 480

    # Taxa de quadros por segundo da câmera
    # 30 FPS é suficiente para reconhecimento de gestos em tempo real
    CAMERA_FPS: int = 30

    # Intervalo em milissegundos entre atualizações do frame na GUI
    # 33ms ≈ 30 FPS. Valor menor = mais fluido, porém mais uso de CPU
    CAMERA_UPDATE_INTERVAL_MS: int = 33

    # -------------------------------------------------------
    # CONFIGURAÇÕES DO MEDIAPIPE (Detecção de Mãos)
    # -------------------------------------------------------

    # Número máximo de mãos que o MediaPipe tentará detectar simultaneamente
    # LIBRAS geralmente usa 1 ou 2 mãos
    MP_MAX_HANDS: int = 2

    # Confiança mínima para aceitar uma detecção inicial de mão (0.0 a 1.0)
    # Valores mais altos = menos falsos positivos, mas pode perder detecções reais
    MP_DETECTION_CONFIDENCE: float = 0.7

    # Confiança mínima para manter o rastreamento de uma mão já detectada
    # Pode ser menor que a detecção, pois o rastreamento é mais estável
    MP_TRACKING_CONFIDENCE: float = 0.5

    # -------------------------------------------------------
    # CONFIGURAÇÕES DO MODELO DE RECONHECIMENTO
    # -------------------------------------------------------

    # Caminho para o arquivo do modelo treinado de reconhecimento de sinais
    # O modelo deve estar no formato .pkl (scikit-learn) ou .h5 (Keras/TensorFlow)
    MODEL_PATH: str = "models/sign_classifier.pkl"

    # Número mínimo de frames consecutivos com o mesmo sinal para confirmar uma detecção
    # Evita que gestos transitórios sejam registrados como palavras
    SIGN_CONFIRM_FRAMES: int = 15

    # Confiança mínima do modelo para aceitar uma predição como válida (0.0 a 1.0)
    SIGN_CONFIDENCE_THRESHOLD: float = 0.75

    # Tempo em segundos de "pausa" entre sinais para separar palavras distintas
    SIGN_PAUSE_DURATION: float = 1.5

    # -------------------------------------------------------
    # CONFIGURAÇÕES DE TEXT-TO-SPEECH (Módulo Paciente)
    # -------------------------------------------------------

    # Taxa de fala em palavras por minuto (padrão pyttsx3: 200)
    # Valores menores = fala mais lenta e clara (bom para contexto médico)
    TTS_RATE: int = 150

    # Volume da fala (0.0 = mudo, 1.0 = volume máximo)
    TTS_VOLUME: float = 0.9

    # Índice da voz a usar (0 = primeira voz disponível no sistema)
    # No Windows: 0=masculina, 1=feminina. Varia por SO e idioma instalado
    TTS_VOICE_INDEX: int = 0

    # -------------------------------------------------------
    # CONFIGURAÇÕES DO VLIBRAS (Módulo Médico)
    # -------------------------------------------------------

    # URL base da API do VLibras para tradução de texto para LIBRAS
    # Documentação: https://vlibras.gov.br/doc/
    VLIBRAS_API_URL: str = "https://vlibras.gov.br/api/translate"

    # URL do widget VLibras para embedar em webview
    # Este widget renderiza o avatar 3D que executa os sinais
    VLIBRAS_WIDGET_URL: str = "vlibras_local/player.html"

    # Timeout em segundos para requisições à API do VLibras
    VLIBRAS_TIMEOUT: int = 10

    # -------------------------------------------------------
    # CONFIGURAÇÕES DE INTERFACE (Cores e Fontes)
    # -------------------------------------------------------

    # Cor de fundo principal da aplicação (hexadecimal)
    # Tom escuro de azul/cinza para ambiente hospitalar (profissional e não cansativo)
    COLOR_BG_PRIMARY: str = "#0F1B2D"

    # Cor de fundo secundária (painéis, cards)
    COLOR_BG_SECONDARY: str = "#162236"

    # Cor de destaque/acento (botões, indicadores ativos)
    COLOR_ACCENT: str = "#00C9A7"

    # Cor de alerta/atenção (erros, avisos)
    COLOR_WARNING: str = "#FFB347"

    # Cor de texto principal (branco levemente suavizado para conforto visual)
    COLOR_TEXT_PRIMARY: str = "#E8EDF5"

    # Cor de texto secundário (subtítulos, labels menos importantes)
    COLOR_TEXT_SECONDARY: str = "#8899AA"

    # Cor do separador/borda entre elementos
    COLOR_BORDER: str = "#243450"

    # Família de fonte para títulos e cabeçalhos
    FONT_FAMILY_HEADING: str = "Helvetica Neue"

    # Família de fonte para texto corrido e labels
    FONT_FAMILY_BODY: str = "Helvetica"

    # Tamanho da fonte para títulos principais
    FONT_SIZE_TITLE: int = 18

    # Tamanho da fonte padrão para texto de interface
    FONT_SIZE_NORMAL: int = 11

    # Tamanho da fonte para texto pequeno (labels, hints)
    FONT_SIZE_SMALL: int = 9

    # -------------------------------------------------------
    # CONFIGURAÇÕES DE LOG
    # -------------------------------------------------------

    # Diretório onde os arquivos de log serão armazenados
    LOG_DIR: str = "logs"

    # Número máximo de bytes por arquivo de log antes de rotacionar
    # 5 MB = 5 * 1024 * 1024 bytes
    LOG_MAX_BYTES: int = 5 * 1024 * 1024

    # Número de arquivos de backup de log a manter (rotação)
    LOG_BACKUP_COUNT: int = 3

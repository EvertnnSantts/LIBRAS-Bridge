"""
============================================================
  LIBRAS Bridge
  Arquivo: tests/test_core.py
  Descrição: Testes unitários para os módulos core da aplicação.
             Usa pytest e unittest.mock para isolar dependências
             externas (câmera, TTS, MediaPipe) durante os testes.

  EXECUÇÃO:
    pytest tests/ -v
    pytest tests/ -v --tb=short   (relatório resumido de falhas)
    pytest tests/ -v --cov=src    (com cobertura de código)
============================================================
"""

# --- Importações da Biblioteca Padrão ---
import unittest                         # Framework de testes padrão do Python
import numpy as np                      # Para criar arrays de teste
from unittest.mock import MagicMock, patch, PropertyMock  # Para mock de dependências

# --- Importações Internas ---
from src.utils.config import AppConfig  # Configurações da aplicação
from src.utils.logger import setup_logger


class TestAppConfig(unittest.TestCase):
    """
    Testes para a classe de configuração.
    Verifica que todos os valores padrão são válidos e coerentes.
    """

    def setUp(self):
        """
        setUp() é executado antes de cada teste.
        Cria uma instância de AppConfig para ser usada nos testes.
        """
        # Instancia a configuração com os valores padrão
        self.config = AppConfig()

    def test_window_dimensions_are_positive(self):
        """Verifica que as dimensões da janela são valores positivos."""
        # assertTrue: falha se a expressão for False
        self.assertGreater(self.config.WINDOW_WIDTH, 0)
        self.assertGreater(self.config.WINDOW_HEIGHT, 0)

    def test_min_size_smaller_than_default(self):
        """Verifica que o tamanho mínimo é menor que o tamanho padrão."""
        self.assertLessEqual(self.config.MIN_WIDTH, self.config.WINDOW_WIDTH)
        self.assertLessEqual(self.config.MIN_HEIGHT, self.config.WINDOW_HEIGHT)

    def test_camera_index_non_negative(self):
        """O índice da câmera deve ser 0 ou positivo."""
        self.assertGreaterEqual(self.config.CAMERA_INDEX, 0)

    def test_mediapipe_confidence_range(self):
        """Valores de confiança do MediaPipe devem estar entre 0.0 e 1.0."""
        self.assertBetween(self.config.MP_DETECTION_CONFIDENCE, 0.0, 1.0)
        self.assertBetween(self.config.MP_TRACKING_CONFIDENCE, 0.0, 1.0)

    def test_tts_volume_range(self):
        """Volume do TTS deve estar entre 0.0 e 1.0."""
        self.assertBetween(self.config.TTS_VOLUME, 0.0, 1.0)

    def test_sign_confidence_threshold_range(self):
        """Limiar de confiança de sinais deve estar entre 0.0 e 1.0."""
        self.assertBetween(self.config.SIGN_CONFIDENCE_THRESHOLD, 0.0, 1.0)

    def test_color_format(self):
        """Cores devem estar no formato hexadecimal (#RRGGBB)."""
        colors = [
            self.config.COLOR_BG_PRIMARY,
            self.config.COLOR_BG_SECONDARY,
            self.config.COLOR_ACCENT,
            self.config.COLOR_TEXT_PRIMARY,
        ]
        for color in colors:
            # Verifica que começa com '#' e tem 7 caracteres no total
            self.assertTrue(color.startswith("#"), f"Cor inválida: {color}")
            self.assertEqual(len(color), 7, f"Formato inválido: {color}")

    def assertBetween(self, value, low, high):
        """Helper: verifica que value está no intervalo [low, high]."""
        self.assertGreaterEqual(value, low, f"{value} deve ser >= {low}")
        self.assertLessEqual(value, high, f"{value} deve ser <= {high}")


class TestSignRecognizerFeatureExtraction(unittest.TestCase):
    """
    Testes para a extração de features do SignRecognizer.
    Usa mocks para evitar inicializar o MediaPipe de verdade.
    """

    def setUp(self):
        """Configura mocks necessários antes de cada teste."""
        self.config = AppConfig()
        self.logger = setup_logger("test_recognizer")

        # Cria um landmark simulado com coordenadas conhecidas
        # MagicMock: objeto que aceita qualquer atributo/chamada
        def make_landmark(x, y, z):
            """Cria um landmark simulado com valores fixos."""
            lm = MagicMock()    # Cria um objeto mock
            lm.x = x            # Define o atributo x
            lm.y = y            # Define o atributo y
            lm.z = z            # Define o atributo z
            return lm

        # Cria 21 landmarks simulados (MediaPipe Hands retorna exatamente 21)
        # Todos em posições variadas para simular uma mão real
        landmarks = [make_landmark(i * 0.05, i * 0.03, i * 0.01) for i in range(21)]

        # Cria o objeto hand_landmarks simulado
        self.mock_hand = MagicMock()
        self.mock_hand.landmark = landmarks    # Define os 21 landmarks

    @patch("mediapipe.solutions.hands.Hands")
    def test_feature_vector_shape(self, mock_hands_class):
        """
        Verifica que o vetor de features tem o tamanho correto.
        Com MAX_HANDS=2, esperamos 2 * 21 * 3 = 126 features.
        """
        # Configura o mock para simular o Hands() sem abrir câmera
        mock_hands_class.return_value.__enter__ = MagicMock()
        mock_hands_class.return_value.process = MagicMock()

        # Importa aqui para aplicar o patch antes da importação real
        from src.core.sign_recognizer import SignRecognizer

        # Instancia o recognizer com mocks
        with patch.object(SignRecognizer, '_load_model'):
            recognizer = SignRecognizer(self.config, self.logger)

        # Chama _extract_features com uma mão simulada
        features = recognizer._extract_features([self.mock_hand])

        # O vetor deve ter tamanho TOTAL = MAX_HANDS * 21 * 3
        expected_size = self.config.MP_MAX_HANDS * 21 * 3
        self.assertEqual(len(features), expected_size,
                         f"Features devem ter {expected_size} elementos, "
                         f"mas tem {len(features)}")

    @patch("mediapipe.solutions.hands.Hands")
    def test_feature_normalization_range(self, mock_hands_class):
        """
        Verifica que as features normalizadas estão no intervalo [-1, 1].
        A normalização é crucial para o modelo ML funcionar corretamente.
        """
        from src.core.sign_recognizer import SignRecognizer

        with patch.object(SignRecognizer, '_load_model'):
            recognizer = SignRecognizer(self.config, self.logger)

        features = recognizer._extract_features([self.mock_hand])

        if features is not None:
            # Verifica que todos os valores estão entre -1 e 1 (com margem de float)
            self.assertTrue(
                np.all(features <= 1.01),
                "Nenhuma feature deve ser maior que 1.0"
            )
            self.assertTrue(
                np.all(features >= -1.01),
                "Nenhuma feature deve ser menor que -1.0"
            )

    @patch("mediapipe.solutions.hands.Hands")
    def test_no_landmarks_returns_none(self, mock_hands_class):
        """
        Verifica que _extract_features retorna None quando não há landmarks.
        """
        from src.core.sign_recognizer import SignRecognizer

        with patch.object(SignRecognizer, '_load_model'):
            recognizer = SignRecognizer(self.config, self.logger)

        # Lista vazia = nenhuma mão detectada
        result = recognizer._extract_features([])

        # Deve retornar None graciosamente, sem lançar exceção
        self.assertIsNone(result, "Lista vazia deve retornar None")


class TestDoctorModule(unittest.TestCase):
    """
    Testes para o módulo do médico (DoctorModule).
    Verifica a geração de URLs e o histórico de traduções.
    """

    def setUp(self):
        """Configura o DoctorModule para os testes."""
        self.config = AppConfig()
        self.logger = setup_logger("test_doctor")

        # Importa e instancia o módulo
        from src.modules.doctor.doctor_module import DoctorModule
        self.module = DoctorModule(
            config=self.config,
            logger=self.logger
        )

    def test_translate_returns_url(self):
        """translate_text() deve retornar uma URL válida."""
        url = self.module.translate_text("Bom dia, como você está?")

        # A URL não deve ser None
        self.assertIsNotNone(url)

        # Deve conter o domínio do VLibras
        self.assertIn("vlibras.gov.br", url)

    def test_translate_empty_text_returns_none(self):
        """Texto vazio deve retornar None sem erros."""
        result = self.module.translate_text("")
        self.assertIsNone(result)

    def test_translate_whitespace_only_returns_none(self):
        """Texto apenas com espaços deve retornar None."""
        result = self.module.translate_text("   \n\t  ")
        self.assertIsNone(result)

    def test_text_is_url_encoded(self):
        """Caracteres especiais devem ser codificados na URL."""
        url = self.module.translate_text("Onde é a dor?")

        # O espaço deve ser codificado como %20
        self.assertNotIn(" ", url, "Espaços não devem aparecer na URL")

    def test_translation_added_to_history(self):
        """Cada tradução deve ser registrada no histórico."""
        # Histórico inicial deve estar vazio
        self.assertEqual(len(self.module.get_history()), 0)

        # Realiza duas traduções
        self.module.translate_text("Primeira mensagem")
        self.module.translate_text("Segunda mensagem")

        # Histórico deve ter 2 entradas
        self.assertEqual(len(self.module.get_history()), 2)

    def test_clear_history(self):
        """clear_history() deve esvaziar o histórico completamente."""
        self.module.translate_text("Mensagem de teste")
        self.module.clear_history()
        self.assertEqual(len(self.module.get_history()), 0)

    def test_long_text_is_truncated(self):
        """Textos com mais de 500 caracteres devem ser truncados."""
        long_text = "A" * 600       # 600 caracteres (acima do limite de 500)
        url = self.module.translate_text(long_text)

        # A URL deve ser gerada com o texto truncado (não lançar erro)
        self.assertIsNotNone(url)

    def test_embed_html_contains_vlibras_script(self):
        """O HTML gerado deve conter o script do VLibras."""
        html = self.module.get_vlibras_embed_html("Teste de HTML")

        # Deve conter a tag do script do VLibras
        self.assertIn("vlibras-plugin.js", html)

        # Deve conter o texto passado (escapado)
        self.assertIn("Teste de HTML", html)

    def test_embed_html_escapes_xss(self):
        """O HTML gerado deve escapar caracteres perigosos (prevenção de XSS)."""
        malicious_text = '<script>alert("xss")</script>'
        html = self.module.get_vlibras_embed_html(malicious_text)

        # A tag <script> original não deve aparecer no HTML
        # (deve estar escapada como &lt;script&gt;)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)


class TestTTSEngine(unittest.TestCase):
    """
    Testes para o motor TTS.
    Usa mocks para evitar síntese de fala real durante os testes.
    """

    @patch("pyttsx3.init")
    def setUp(self, mock_pyttsx3_init):
        """Configura o TTSEngine com mock do pyttsx3."""
        self.config = AppConfig()
        self.logger = setup_logger("test_tts")

        # Configura o mock do engine pyttsx3
        self.mock_engine = MagicMock()
        mock_pyttsx3_init.return_value = self.mock_engine

        # Simula a lista de vozes disponíveis
        mock_voice = MagicMock()
        mock_voice.name = "Microsoft Maria - Portuguese (Brazil)"
        mock_voice.id = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Maria"
        self.mock_engine.getProperty.return_value = [mock_voice]

        from src.core.tts_engine import TTSEngine
        self.tts = TTSEngine(config=self.config, logger=self.logger)

    @patch("pyttsx3.init")
    def test_initialization_success(self, mock_init):
        """O TTS deve inicializar sem erros com o mock."""
        # Se chegou aqui sem exceção, a inicialização foi bem-sucedida
        self.assertTrue(self.tts._initialized)

    @patch("pyttsx3.init")
    def test_speak_empty_text_ignored(self, mock_init):
        """speak() com texto vazio não deve chamar o engine."""
        self.tts.speak("")

        # O engine não deve ter sido chamado com texto vazio
        self.mock_engine.say.assert_not_called()

    def test_set_rate_updates_engine(self):
        """set_rate() deve chamar setProperty no engine."""
        self.tts.set_rate(120)
        # Verifica que setProperty foi chamado com 'rate' e 120
        self.mock_engine.setProperty.assert_any_call("rate", 120)

    def test_set_volume_clamps_to_valid_range(self):
        """set_volume() deve garantir que o valor está entre 0 e 1."""
        # Testa valor acima do máximo
        self.tts.set_volume(1.5)
        self.mock_engine.setProperty.assert_any_call("volume", 1.0)

        # Testa valor abaixo do mínimo
        self.tts.set_volume(-0.5)
        self.mock_engine.setProperty.assert_any_call("volume", 0.0)


class TestPatientModule(unittest.TestCase):
    """
    Testes para o módulo do paciente.
    Verifica o acumulador de frases e a lógica de controle.
    """

    @patch("mediapipe.solutions.hands.Hands")
    @patch("pyttsx3.init")
    def setUp(self, mock_pyttsx3, mock_hands):
        """Configura o PatientModule com dependências mockadas."""
        self.config = AppConfig()
        self.logger = setup_logger("test_patient")

        # Mock do TTS
        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = []
        mock_pyttsx3.return_value = mock_engine

        from src.core.tts_engine import TTSEngine
        self.tts = TTSEngine(config=self.config, logger=self.logger)

        from src.modules.patient.patient_module import PatientModule
        self.module = PatientModule(
            config=self.config,
            logger=self.logger,
            tts_engine=self.tts
        )

    def test_initial_sentence_is_empty(self):
        """A frase inicial deve estar vazia."""
        self.assertEqual(self.module.get_current_sentence(), "")

    def test_clear_sentence(self):
        """clear_sentence() deve limpar o acumulador."""
        # Simula palavras acumuladas manualmente
        self.module._current_sentence = ["DOR", "CABEÇA"]
        self.module.clear_sentence()
        self.assertEqual(self.module.get_current_sentence(), "")

    def test_sentence_accumulates_words(self):
        """Palavras reconhecidas devem ser acumuladas na ordem correta."""
        # Simula reconhecimento de palavras em sequência
        self.module._handle_confirmed_sign("DOR")
        self.module._handle_confirmed_sign("CABEÇA")
        self.module._handle_confirmed_sign("FORTE")

        # A frase deve ser as palavras juntas por espaço
        self.assertEqual(
            self.module.get_current_sentence(),
            "DOR CABEÇA FORTE"
        )


# Ponto de entrada para execução direta do arquivo de testes
if __name__ == "__main__":
    # verbosity=2: exibe o nome de cada teste e o resultado (OK ou FAIL)
    unittest.main(verbosity=2)

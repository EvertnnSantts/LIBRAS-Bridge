"""
============================================================
  LIBRAS Bridge
  Arquivo: src/modules/doctor/doctor_module.py
  Descrição: Módulo Médico — Texto → LIBRAS via VLibras.
             Gerencia a integração com o widget VLibras para
             renderizar o avatar 3D traduzindo o texto do
             médico para Língua Brasileira de Sinais.

  SOBRE O VLIBRAS:
    O VLibras é um conjunto de ferramentas de código aberto
    desenvolvido pelo Governo Federal do Brasil (UFPB/LAVID)
    que traduz conteúdos digitais para LIBRAS.
    Site: https://vlibras.gov.br/
    Repositório: https://github.com/spbgovbr-vlibras/vlibras-portal

  ESTRATÉGIA DE INTEGRAÇÃO:
    1. Usa o player VLibras local (pasta vlibras_local/)
    2. Abre no navegador padrão via file:// com o texto na URL
    3. O avatar 3D executa a tradução automaticamente
============================================================
"""

# --- Importações da Biblioteca Padrão ---
import os
import logging
import urllib.parse
import webbrowser
import datetime
from typing import Optional, Callable

# --- Importações Internas ---
from src.utils.config import AppConfig


class DoctorModule:
    """
    Módulo responsável por:
    1. Receber texto digitado pelo médico
    2. Enviar para o VLibras local para tradução em LIBRAS
    3. Gerenciar o estado da tradução e histórico
    """

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        on_translation_ready: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Inicializa o módulo do médico.

        Args:
            config:                Configurações da aplicação
            logger:                Instância do logger
            on_translation_ready:  Callback chamado quando a tradução estiver pronta
                                   Assinatura: (url: str) -> None
        """
        self._config = config
        self._logger = logger
        self._on_translation_ready = on_translation_ready

        self._translation_history: list = []
        self._is_translating: bool = False

        # Resolve o caminho absoluto do player VLibras local
        # Sobe 3 níveis a partir deste arquivo: doctor/ → modules/ → src/ → raiz do projeto
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../")
        )
        self._vlibras_local_path = os.path.join(project_root, "vlibras_local", "index.html")

        if os.path.exists(self._vlibras_local_path):
            self._logger.info(f"VLibras local encontrado em: {self._vlibras_local_path}")
        else:
            self._logger.warning(
                f"VLibras local NÃO encontrado em: {self._vlibras_local_path}. "
                "Copie a pasta vlibras-portal/app para vlibras_local/ na raiz do projeto."
            )

        self._logger.info("DoctorModule inicializado.")

    def _build_vlibras_url(self, encoded_text: str) -> str:
        """
        Constrói a URL correta do VLibras local ou remoto como fallback.

        Args:
            encoded_text: Texto já codificado para URL

        Returns:
            URL completa para abrir o VLibras com o texto
        """
        if os.path.exists(self._vlibras_local_path):
            # Usa o player local — converte caminho Windows para formato file://
            # Substitui barras invertidas por barras normais para compatibilidade
            path_normalizado = self._vlibras_local_path.replace("\\", "/")
            return f"file:///{path_normalizado.replace('index.html','player.html')}/#/translate/{encoded_text}"
        else:
            # Fallback para o portal online caso o local não exista
            self._logger.warning("Usando VLibras remoto como fallback.")
            return f"https://vlibras.gov.br/app/#/translate/{encoded_text}"

    def translate_text(self, text: str) -> Optional[str]:
        """
        Processa o texto e inicia a tradução para LIBRAS via VLibras local.

        Args:
            text: Texto em português para traduzir para LIBRAS

        Returns:
            URL do VLibras com o texto, ou None se o texto for inválido
        """
        text = text.strip()
        if not text:
            self._logger.warning("Texto vazio para tradução.")
            return None

        if len(text) > 500:
            self._logger.warning(f"Texto truncado de {len(text)} para 500 caracteres.")
            text = text[:500]

        self._logger.info(
            f"Traduzindo para LIBRAS: '{text[:50]}...'" if len(text) > 50
            else f"Traduzindo: '{text}'"
        )

        encoded_text = urllib.parse.quote(text, safe="")
        vlibras_url = self._build_vlibras_url(encoded_text)

        self._translation_history.append({
            "text": text,
            "url": vlibras_url,
            "timestamp": datetime.datetime.now().isoformat()
        })

        if self._on_translation_ready:
            self._on_translation_ready(vlibras_url)

        return vlibras_url

    def open_in_browser(self, text: str) -> None:
        """
        Abre o VLibras no navegador padrão do sistema.

        Args:
            text: Texto a ser traduzido
        """
        text = text.strip()
        if not text:
            return

        encoded_text = urllib.parse.quote(text, safe="")
        url = self._build_vlibras_url(encoded_text)

        self._logger.info(f"Abrindo VLibras no navegador: {url}")
        webbrowser.open(url)

    def get_history(self) -> list:
        """
        Retorna o histórico de traduções desta sessão.

        Returns:
            Lista de dicionários com 'text', 'url' e 'timestamp'
        """
        return self._translation_history.copy()

    def clear_history(self) -> None:
        """Limpa o histórico de traduções da sessão atual."""
        self._translation_history.clear()
        self._logger.debug("Histórico de traduções limpo.")

    def get_vlibras_embed_html(self, text: str) -> str:
        """
        Gera HTML de confirmação para exibir no painel interno.
        O avatar real roda no navegador externo.

        Args:
            text: Texto que está sendo traduzido

        Returns:
            String HTML para exibir no WebView interno
        """
        safe_text = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0F1B2D;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            font-family: Helvetica, sans-serif;
            color: #E8EDF5;
            text-align: center;
            padding: 24px;
        }}
        .icon {{ font-size: 48px; margin-bottom: 16px; }}
        .title {{
            font-size: 16px;
            font-weight: bold;
            color: #00C9A7;
            margin-bottom: 10px;
        }}
        .text-box {{
            background: #162236;
            border: 1px solid #243450;
            border-radius: 10px;
            padding: 14px 20px;
            font-size: 15px;
            color: #E8EDF5;
            margin-top: 12px;
            max-width: 400px;
            line-height: 1.6;
        }}
        .sub {{
            font-size: 12px;
            color: #7A90B0;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="icon">🤟</div>
    <p class="title">Tradução aberta no navegador</p>
    <div class="text-box">{safe_text}</div>
    <p class="sub">O avatar VLibras está sendo exibido<br>no seu navegador padrão.</p>
</body>
</html>"""

        return html
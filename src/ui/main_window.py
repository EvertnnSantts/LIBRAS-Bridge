"""
============================================================
  LIBRAS Bridge
  Arquivo: src/ui/main_window.py
  Descrição: Janela principal da aplicação com a interface
             gráfica completa. Implementa o padrão MVC onde
             esta classe é a View, comunicando-se com os
             módulos (Model) via callbacks.

  LAYOUT:
  ┌────────────────────────────────────────────────────┐
  │  HEADER: Logo + Título + Status do Sistema         │
  ├──────────────────────┬─────────────────────────────┤
  │  MÓDULO PACIENTE     │  MÓDULO MÉDICO              │
  │  ┌────────────────┐  │  ┌─────────────────────┐   │
  │  │  Feed Câmera   │  │  │  Campo de Texto     │   │
  │  └────────────────┘  │  └─────────────────────┘   │
  │  ┌────────────────┐  │  ┌─────────────────────┐   │
  │  │  Frase LIBRAS  │  │  │  Player VLibras     │   │
  │  └────────────────┘  │  └─────────────────────┘   │
  │  [Iniciar] [Limpar]  │  [Traduzir] [Navegador]    │
  ├──────────────────────┴─────────────────────────────┤
  │  FOOTER: Status Bar                                │
  └────────────────────────────────────────────────────┘
============================================================
"""

# --- Importações da Biblioteca Padrão ---
import logging                              # Para registro de logs
import tkinter as tk                        # Framework GUI
from tkinter import ttk, messagebox, font   # Widgets, diálogos e fontes
from typing import Optional, Self                 # Para anotações de tipo
import threading
import http.server
import socketserver
import os
import urllib.parse
import tkinterweb

# --- Importações Internas ---
from src.utils.config import AppConfig
from src.core.tts_engine import TTSEngine
from src.modules.patient.patient_module import PatientModule
from src.modules.doctor.doctor_module import DoctorModule


class MainWindow:
    """
    Janela principal da aplicação LIBRAS Bridge.
    Cria e gerencia toda a interface gráfica com dois painéis:
    - Esquerdo: Módulo Paciente (câmera + LIBRAS → texto/áudio)
    - Direito:  Módulo Médico  (texto → LIBRAS via VLibras)
    """

    def __init__(
        self,
        root: tk.Tk,
        config: AppConfig,
        logger: logging.Logger
    ) -> None:
        """
        Inicializa a janela principal.

        Args:
            root:   Widget raiz do Tkinter
            config: Configurações da aplicação
            logger: Instância do logger
        """
        self._root = root
        self._config = config
        self._logger = logger

        # Referência ao objeto PhotoImage da câmera (mantida para evitar garbage collection)
        # IMPORTANTE: Tkinter faz garbage collection de PhotoImage se não houver referência
        self._camera_photo = None

        # -------------------------------------------------------
        # INICIALIZAÇÃO DOS MÓDULOS DE LÓGICA
        # -------------------------------------------------------

        # Motor TTS compartilhado entre módulos
        self._tts = TTSEngine(config=config, logger=logger)

        # Módulo do paciente (com callbacks para atualizar a UI)
        self._patient_module = PatientModule(
            config=config,
            logger=logger,
            tts_engine=self._tts,
            on_word_detected=self._on_word_detected,        # Callback: nova palavra reconhecida
            on_frame_ready=self._on_camera_frame_ready      # Callback: novo frame da câmera
        )

        # Módulo do médico (com callback para atualizar o WebView)
        self._doctor_module = DoctorModule(
            config=config,
            logger=logger,
            on_translation_ready=self._on_translation_ready # Callback: tradução pronta
        )

        # Inicia servidor HTTP local para servir o VLibras
        self._vlibras_server_port = 8765
        self._start_vlibras_server()

        # -------------------------------------------------------
        # CONSTRUÇÃO DA INTERFACE GRÁFICA
        # -------------------------------------------------------

        # Configura os estilos visuais da aplicação (cores, fontes)
        self._setup_styles()

        # Constrói a estrutura de widgets da janela
        self._build_ui()

        self._logger.info("MainWindow construída.")

    def _start_vlibras_server(self) -> None:
        """Sobe um servidor HTTP local para servir os arquivos do VLibras."""
        vlibras_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../vlibras_local")
        )

        if not os.path.exists(vlibras_dir):
            self._logger.warning(f"Pasta vlibras_local não encontrada: {vlibras_dir}")
            self._vlibras_server_port = None
            return

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=vlibras_dir, **kwargs)

            def log_message(self, format, *args):
                pass  # Silencia os logs do servidor HTTP

        try:
            server = socketserver.TCPServer(("localhost", self._vlibras_server_port), Handler)
            server.allow_reuse_address = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._logger.info(
                f"Servidor VLibras local rodando em http://localhost:{self._vlibras_server_port}"
            )
        except Exception as e:
            self._logger.error(f"Falha ao iniciar servidor VLibras: {e}")
            self._vlibras_server_port = None

    def _setup_styles(self) -> None:
        """
        Configura os estilos visuais dos widgets usando ttk.Style.
        Centraliza todas as definições de cores, fontes e aparência.
        """

        # Obtém o objeto Style do ttk para configurar aparência
        style = ttk.Style(self._root)

        # Define o tema base — 'clam' é mais customizável que 'default'
        style.theme_use("clam")

        # -------------------------------------------------------
        # COR DE FUNDO DA JANELA RAIZ
        # -------------------------------------------------------

        # Configura a cor de fundo da janela principal
        self._root.configure(bg=self._config.COLOR_BG_PRIMARY)

        # -------------------------------------------------------
        # ESTILOS DOS FRAMES (contêineres)
        # -------------------------------------------------------

        # Frame principal com fundo escuro
        style.configure(
            "Main.TFrame",
            background=self._config.COLOR_BG_PRIMARY
        )

        # Frame de card (painel com fundo ligeiramente diferente)
        style.configure(
            "Card.TFrame",
            background=self._config.COLOR_BG_SECONDARY
        )

        # -------------------------------------------------------
        # ESTILOS DE LABELS (textos)
        # -------------------------------------------------------

        # Label de título grande
        style.configure(
            "Title.TLabel",
            background=self._config.COLOR_BG_PRIMARY,
            foreground=self._config.COLOR_TEXT_PRIMARY,
            font=(self._config.FONT_FAMILY_HEADING, self._config.FONT_SIZE_TITLE, "bold")
        )

        # Label de subtítulo para seções
        style.configure(
            "Section.TLabel",
            background=self._config.COLOR_BG_SECONDARY,
            foreground=self._config.COLOR_ACCENT,
            font=(self._config.FONT_FAMILY_HEADING, 13, "bold")
        )

        # Label de texto normal em fundo escuro
        style.configure(
            "Normal.TLabel",
            background=self._config.COLOR_BG_PRIMARY,
            foreground=self._config.COLOR_TEXT_PRIMARY,
            font=(self._config.FONT_FAMILY_BODY, self._config.FONT_SIZE_NORMAL)
        )

        # Label de texto em card (fundo secundário)
        style.configure(
            "Card.TLabel",
            background=self._config.COLOR_BG_SECONDARY,
            foreground=self._config.COLOR_TEXT_SECONDARY,
            font=(self._config.FONT_FAMILY_BODY, self._config.FONT_SIZE_SMALL)
        )

        # -------------------------------------------------------
        # ESTILOS DE BOTÕES
        # -------------------------------------------------------

        # Botão primário (ação principal)
        style.configure(
            "Primary.TButton",
            background=self._config.COLOR_ACCENT,
            foreground="#0F1B2D",
            font=(self._config.FONT_FAMILY_BODY, 10, "bold"),
            padding=(12, 6),
            relief="flat"
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#00A88A"), ("disabled", "#243450")],
            foreground=[("disabled", "#8899AA")]
        )

        # Botão secundário (ação alternativa)
        style.configure(
            "Secondary.TButton",
            background=self._config.COLOR_BG_PRIMARY,
            foreground=self._config.COLOR_TEXT_PRIMARY,
            font=(self._config.FONT_FAMILY_BODY, 10),
            padding=(12, 6),
            relief="flat"
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#243450")]
        )

        # Botão de perigo/alerta (ex: parar câmera)
        style.configure(
            "Danger.TButton",
            background="#E05555",
            foreground="#FFFFFF",
            font=(self._config.FONT_FAMILY_BODY, 10, "bold"),
            padding=(12, 6),
            relief="flat"
        )

        # -------------------------------------------------------
        # ESTILO DO SEPARADOR
        # -------------------------------------------------------

        style.configure(
            "Dark.TSeparator",
            background=self._config.COLOR_BORDER
        )

    def _build_ui(self) -> None:
        """
        Constrói toda a hierarquia de widgets da janela principal.
        Organizado em: Header → Corpo Principal (2 colunas) → Footer
        """

        # -------------------------------------------------------
        # CONTAINER RAIZ: ocupa toda a janela
        # -------------------------------------------------------

        # Frame raiz que preenche toda a janela
        # fill=BOTH: expande em ambas as direções
        # expand=True: cresce quando a janela é redimensionada
        self._main_frame = ttk.Frame(self._root, style="Main.TFrame")
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------
        # SEÇÃO: HEADER
        # -------------------------------------------------------
        self._build_header()

        # Linha divisória entre header e corpo
        ttk.Separator(
            self._main_frame,
            orient=tk.HORIZONTAL,
            style="Dark.TSeparator"
        ).pack(fill=tk.X, padx=0, pady=0)

        # -------------------------------------------------------
        # SEÇÃO: CORPO PRINCIPAL (dois painéis lado a lado)
        # -------------------------------------------------------

        # Frame que conterá os dois módulos lado a lado
        body_frame = ttk.Frame(self._main_frame, style="Main.TFrame")
        body_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Configura as colunas: cada metade ocupa 50% do espaço
        body_frame.columnconfigure(0, weight=1)     # Coluna 0: Módulo Paciente
        body_frame.columnconfigure(1, weight=1)     # Coluna 1: Módulo Médico
        body_frame.rowconfigure(0, weight=1)        # Linha única que expande

        # Constrói o painel do módulo paciente (esquerda)
        self._build_patient_panel(body_frame)

        # Separador vertical entre os dois módulos
        ttk.Separator(
            body_frame,
            orient=tk.VERTICAL,
            style="Dark.TSeparator"
        ).grid(row=0, column=1, sticky="ns", padx=0)

        # Constrói o painel do módulo médico (direita)
        self._build_doctor_panel(body_frame)

        # -------------------------------------------------------
        # SEÇÃO: FOOTER (barra de status)
        # -------------------------------------------------------

        ttk.Separator(
            self._main_frame,
            orient=tk.HORIZONTAL,
            style="Dark.TSeparator"
        ).pack(fill=tk.X)

        self._build_footer()

    def _build_header(self) -> None:
        """
        Constrói o cabeçalho da aplicação com logo, título e indicadores de status.
        """

        # Frame do header com padding vertical
        header = ttk.Frame(self._main_frame, style="Main.TFrame")
        header.pack(fill=tk.X, padx=20, pady=12)

        # -------------------------------------------------------
        # COLUNA ESQUERDA: Ícone + Título
        # -------------------------------------------------------

        left_frame = ttk.Frame(header, style="Main.TFrame")
        left_frame.pack(side=tk.LEFT)

        # Ícone da aplicação (emoji como substituto até ter imagem real)
        # Em produção, substituir por tk.Label com imagem PNG
        icon_label = tk.Label(
            left_frame,
            text="🤝",                              # Emoji de aperto de mãos (acessibilidade)
            font=("Segoe UI Emoji", 28),            # Fonte com suporte a emoji
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_PRIMARY
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 12))

        # Frame para empilhar título e subtítulo verticalmente
        title_frame = ttk.Frame(left_frame, style="Main.TFrame")
        title_frame.pack(side=tk.LEFT)

        # Título principal da aplicação
        title = tk.Label(
            title_frame,
            text="LIBRAS Bridge",
            font=(self._config.FONT_FAMILY_HEADING, 22, "bold"),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_PRIMARY
        )
        title.pack(anchor=tk.W)

        # Subtítulo descritivo
        subtitle = tk.Label(
            title_frame,
            text="Comunicação Hospitalar Acessível • LIBRAS ↔ Português",
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        )
        subtitle.pack(anchor=tk.W)

        # -------------------------------------------------------
        # COLUNA DIREITA: Indicadores de Status
        # -------------------------------------------------------

        right_frame = ttk.Frame(header, style="Main.TFrame")
        right_frame.pack(side=tk.RIGHT)

        # Indicador de status do sistema (câmera, TTS, etc.)
        self._status_indicator = tk.Label(
            right_frame,
            text="● Sistema Pronto",
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_ACCENT      # Verde = ativo/ok
        )
        self._status_indicator.pack(anchor=tk.E)

        # Versão da aplicação
        version_label = tk.Label(
            right_frame,
            text="v1.0.0 | LIBRAS Bridge",
            font=(self._config.FONT_FAMILY_BODY, 9),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        )
        version_label.pack(anchor=tk.E)

    def _build_patient_panel(self, parent: ttk.Frame) -> None:
        """
        Constrói o painel do Módulo Paciente (coluna esquerda).
        Contém: feed da câmera, display da frase reconhecida, botões de controle.

        Args:
            parent: Frame pai onde o painel será inserido
        """

        # Frame do painel esquerdo
        # sticky="nsew": estica em todas as direções para preencher a célula do grid
        patient_panel = ttk.Frame(parent, style="Main.TFrame")
        patient_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Configura o redimensionamento interno do painel
        patient_panel.columnconfigure(0, weight=1)
        patient_panel.rowconfigure(1, weight=1)    # A câmera expande verticalmente

        # -------------------------------------------------------
        # CABEÇALHO DO PAINEL
        # -------------------------------------------------------

        header_frame = ttk.Frame(patient_panel, style="Card.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", padx=0)

        # Adiciona padding interno ao header do card
        inner_header = ttk.Frame(header_frame, style="Card.TFrame")
        inner_header.pack(fill=tk.X, padx=16, pady=10)

        # Ícone + título do módulo
        tk.Label(
            inner_header,
            text="👤  MÓDULO PACIENTE",
            font=(self._config.FONT_FAMILY_HEADING, 13, "bold"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_ACCENT
        ).pack(side=tk.LEFT)

        # Subtítulo explicativo
        tk.Label(
            inner_header,
            text="LIBRAS → Texto e Áudio",
            font=(self._config.FONT_FAMILY_BODY, 9),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(side=tk.RIGHT)

        # -------------------------------------------------------
        # ÁREA DA CÂMERA
        # -------------------------------------------------------

        # Frame que conterá o feed da câmera
        camera_container = ttk.Frame(patient_panel, style="Main.TFrame")
        camera_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 0))
        camera_container.columnconfigure(0, weight=1)
        camera_container.rowconfigure(0, weight=1)

        # Label que exibe os frames da câmera
        # O Label é atualizado continuamente com PhotoImage pelo PatientModule
        self._camera_label = tk.Label(
            camera_container,
            text="📷 Câmera não iniciada\n\nClique em 'Iniciar Câmera'\npara começar",
            font=(self._config.FONT_FAMILY_BODY, 11),
            bg="#0A1420",                               # Fundo muito escuro para a câmera
            fg=self._config.COLOR_TEXT_SECONDARY,
            width=640,                                  # Largura fixa em pixels
            height=380,                                 # Altura fixa em pixels
            anchor=tk.CENTER,
            relief=tk.FLAT
        )
        self._camera_label.grid(row=0, column=0, sticky="nsew")

        # -------------------------------------------------------
        # ÁREA DE EXIBIÇÃO DA FRASE RECONHECIDA
        # -------------------------------------------------------

        sentence_frame = ttk.Frame(patient_panel, style="Card.TFrame")
        sentence_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 0))

        inner_sentence = tk.Frame(sentence_frame, bg=self._config.COLOR_BG_SECONDARY)
        inner_sentence.pack(fill=tk.X, padx=14, pady=10)

        # Label descritivo acima da frase
        tk.Label(
            inner_sentence,
            text="FRASE RECONHECIDA:",
            font=(self._config.FONT_FAMILY_BODY, 9, "bold"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(anchor=tk.W)

        # StringVar: variável Tkinter que notifica automaticamente os widgets
        # quando seu valor muda (vinculação de dados reativa)
        self._sentence_var = tk.StringVar(value="")

        # Label que exibe a frase reconhecida em tempo real
        self._sentence_label = tk.Label(
            inner_sentence,
            textvariable=self._sentence_var,            # Vinculado à StringVar
            font=(self._config.FONT_FAMILY_HEADING, 15, "bold"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_PRIMARY,
            wraplength=580,                             # Quebra de linha automática
            justify=tk.LEFT,
            anchor=tk.W,
            pady=4
        )
        self._sentence_label.pack(fill=tk.X, pady=(2, 0))

        # Placeholder quando nenhuma palavra foi reconhecida ainda
        self._sentence_placeholder = tk.Label(
            inner_sentence,
            text="Aguardando sinais em LIBRAS...",
            font=(self._config.FONT_FAMILY_BODY, 11, "italic"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        )
        self._sentence_placeholder.pack(anchor=tk.W)

        # -------------------------------------------------------
        # BOTÕES DE CONTROLE DO MÓDULO PACIENTE
        # -------------------------------------------------------

        buttons_frame = tk.Frame(patient_panel, bg=self._config.COLOR_BG_PRIMARY)
        buttons_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=10)

        # Botão: Iniciar/Parar câmera
        self._btn_camera = tk.Button(
            buttons_frame,
            text="▶  Iniciar Câmera",
            command=self._toggle_camera,
            font=(self._config.FONT_FAMILY_BODY, 10, "bold"),
            bg=self._config.COLOR_ACCENT,
            fg="#0F1B2D",
            activebackground="#00A88A",
            activeforeground="#0F1B2D",
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"                              # Cursor de mãozinha ao passar
        )
        self._btn_camera.pack(side=tk.LEFT, padx=(0, 8))

        # Flag para controlar o estado do botão câmera
        self._camera_running = False

        # Botão: Falar frase completa
        tk.Button(
            buttons_frame,
            text="🔊  Falar Frase",
            command=self._speak_patient_sentence,
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_PRIMARY,
            activebackground="#243450",
            activeforeground=self._config.COLOR_TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

        # Botão: Limpar frase acumulada
        tk.Button(
            buttons_frame,
            text="🗑  Limpar",
            command=self._clear_patient_sentence,
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg="#243450",
            fg=self._config.COLOR_TEXT_SECONDARY,
            activebackground="#1A2A40",
            activeforeground=self._config.COLOR_TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"
        ).pack(side=tk.LEFT)

    def _build_doctor_panel(self, parent: ttk.Frame) -> None:
        """
        Constrói o painel do Módulo Médico (coluna direita).
        Contém: campo de texto, player VLibras embutido, botões de ação.

        Args:
            parent: Frame pai onde o painel será inserido
        """

        # Frame do painel direito
        doctor_panel = ttk.Frame(parent, style="Main.TFrame")
        doctor_panel.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        doctor_panel.columnconfigure(0, weight=1)
        doctor_panel.rowconfigure(2, weight=1)    # O player VLibras expande

        # -------------------------------------------------------
        # CABEÇALHO DO PAINEL
        # -------------------------------------------------------

        header_frame = ttk.Frame(doctor_panel, style="Card.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew")

        inner_header = ttk.Frame(header_frame, style="Card.TFrame")
        inner_header.pack(fill=tk.X, padx=16, pady=10)

        tk.Label(
            inner_header,
            text="🩺  MÓDULO MÉDICO",
            font=(self._config.FONT_FAMILY_HEADING, 13, "bold"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg="#FFB347"                               # Amarelo/laranja para diferenciar do módulo paciente
        ).pack(side=tk.LEFT)

        tk.Label(
            inner_header,
            text="Texto → LIBRAS (VLibras)",
            font=(self._config.FONT_FAMILY_BODY, 9),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(side=tk.RIGHT)

        # -------------------------------------------------------
        # ÁREA DE ENTRADA DE TEXTO
        # -------------------------------------------------------

        input_container = tk.Frame(doctor_panel, bg=self._config.COLOR_BG_PRIMARY)
        input_container.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 0))

        # Label instrucional acima do campo de texto
        tk.Label(
            input_container,
            text="Digite o diagnóstico ou pergunta para o paciente:",
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(anchor=tk.W, pady=(0, 4))

        # Frame para o campo de texto + scrollbar
        text_frame = tk.Frame(
            input_container,
            bg=self._config.COLOR_BORDER,
            bd=0,
            relief=tk.FLAT
        )
        text_frame.pack(fill=tk.X, pady=0)

        # Text widget: campo de texto com múltiplas linhas
        # O médico digita o diagnóstico ou perguntas aqui
        self._doctor_text = tk.Text(
            text_frame,
            font=(self._config.FONT_FAMILY_BODY, 11),
            bg="#1A2940",                               # Fundo levemente diferente para destaque
            fg=self._config.COLOR_TEXT_PRIMARY,
            insertbackground=self._config.COLOR_ACCENT, # Cor do cursor de texto
            selectbackground="#243450",                 # Cor de seleção de texto
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=8,
            height=5,                                   # Altura em linhas de texto
            wrap=tk.WORD                                # Quebra linha entre palavras
        )
        self._doctor_text.pack(fill=tk.X, padx=1, pady=1)

        # Scrollbar vertical para o campo de texto
        text_scroll = ttk.Scrollbar(
            text_frame,
            orient=tk.VERTICAL,
            command=self._doctor_text.yview   # Conecta ao Text widget
        )
        # Vincula a scrollbar ao Text widget (atualiza a scrollbar ao rolar o texto)
        self._doctor_text.configure(yscrollcommand=text_scroll.set)

        # Texto de exemplo para orientar o médico
        example_text = (
            "Exemplo: Bom dia! Como você está se sentindo hoje? "
            "Vou precisar examinar você. Por favor, me diga onde está sentindo dor."
        )
        self._doctor_text.insert(tk.END, example_text)

        # Bind da tecla Ctrl+Enter para acionar a tradução rapidamente
        # <Control-Return>: evento do Tkinter para Ctrl+Enter
        self._doctor_text.bind("<Control-Return>", lambda e: self._translate_doctor_text())

        # Botões de ação abaixo do campo de texto
        btn_row = tk.Frame(input_container, bg=self._config.COLOR_BG_PRIMARY)
        btn_row.pack(fill=tk.X, pady=(8, 0))

        # Botão principal: Traduzir para LIBRAS
        tk.Button(
            btn_row,
            text="🤟  Traduzir para LIBRAS",
            command=self._translate_doctor_text,
            font=(self._config.FONT_FAMILY_BODY, 10, "bold"),
            bg="#FFB347",
            fg="#0F1B2D",
            activebackground="#E09000",
            activeforeground="#0F1B2D",
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

        # Botão: Abrir no navegador (fallback)
        tk.Button(
            btn_row,
            text="🌐  Abrir no Navegador",
            command=self._open_vlibras_browser,
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_PRIMARY,
            activebackground="#243450",
            activeforeground=self._config.COLOR_TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

        # Botão: Limpar campo de texto
        tk.Button(
            btn_row,
            text="🗑  Limpar",
            command=self._clear_doctor_text,
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg="#243450",
            fg=self._config.COLOR_TEXT_SECONDARY,
            activebackground="#1A2A40",
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # Dica sobre Ctrl+Enter
        tk.Label(
            btn_row,
            text="Ctrl+Enter para traduzir",
            font=(self._config.FONT_FAMILY_BODY, 8, "italic"),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(side=tk.RIGHT, padx=(0, 4))

        # -------------------------------------------------------
        # ÁREA DO PLAYER VLIBRAS
        # -------------------------------------------------------

        vlibras_container = tk.Frame(
            doctor_panel,
            bg=self._config.COLOR_BG_SECONDARY,
            relief=tk.FLAT
        )
        vlibras_container.grid(row=2, column=0, sticky="nsew", padx=12, pady=(10, 0))

        # Tenta carregar o tkinterweb para WebView embutido
        # Se não estiver instalado, usa fallback com instruções
        self._try_build_webview(vlibras_container)

        # -------------------------------------------------------
        # HISTÓRICO DE TRADUÇÕES
        # -------------------------------------------------------

        history_frame = tk.Frame(doctor_panel, bg=self._config.COLOR_BG_PRIMARY)
        history_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(8, 0))

        tk.Label(
            history_frame,
            text="ÚLTIMAS TRADUÇÕES DESTA SESSÃO:",
            font=(self._config.FONT_FAMILY_BODY, 8, "bold"),
            bg=self._config.COLOR_BG_PRIMARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(anchor=tk.W)

        # Listbox para exibir o histórico de traduções
        self._history_listbox = tk.Listbox(
            history_frame,
            font=(self._config.FONT_FAMILY_BODY, 9),
            bg="#0A1420",
            fg=self._config.COLOR_TEXT_SECONDARY,
            selectbackground=self._config.COLOR_ACCENT,
            selectforeground="#0F1B2D",
            relief=tk.FLAT,
            height=3,                                   # Altura em linhas
            bd=0
        )
        self._history_listbox.pack(fill=tk.X, pady=(4, 0))

        # Bind duplo clique no histórico para reusar a tradução
        self._history_listbox.bind("<Double-Button-1>", self._reuse_history_item)

    def _try_build_webview(self, parent: tk.Frame) -> None:
        try:
            self._webview = tkinterweb.HtmlFrame(
                parent,
                messages_enabled=False
            )
            self._webview.pack(fill=tk.BOTH, expand=True)

            # Carrega HTML de boas-vindas em vez da URL do VLibras
            # (tkinterweb não suporta JS — usamos HTML local com o script embutido)
            welcome_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0F1B2D;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            font-family: Helvetica, sans-serif;
            color: #E8EDF5;
            text-align: center;
            padding: 24px;
        }
        p { font-size: 15px; color: #7A90B0; line-height: 1.6; }
        span { display: block; font-size: 32px; margin-bottom: 12px; }
    </style>
</head>
<body>
    <div>
        <span>🤝</span>
        <p>Digite um texto acima e clique em<br><strong style="color:#00C9A7">Traduzir para LIBRAS</strong></p>
    </div>
</body>
</html>"""
            self._webview.load_html(welcome_html)

            self._logger.info("WebView tkinterweb inicializado com sucesso.")

        except ImportError:
            self._webview = None
            self._build_vlibras_fallback(parent)

        except Exception as e:
            self._logger.error(f"Erro ao inicializar WebView: {e}")
            self._webview = None
            self._build_vlibras_fallback(parent)

    def _build_vlibras_fallback(self, parent: tk.Frame) -> None:
        """
        Interface alternativa quando o WebView não está disponível.
        Exibe instruções claras para o usuário usar o VLibras no navegador.

        Args:
            parent: Frame pai
        """

        # Frame do conteúdo de fallback
        fallback = tk.Frame(parent, bg=self._config.COLOR_BG_SECONDARY)
        fallback.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Ícone grande
        tk.Label(
            fallback,
            text="🌐",
            font=("Segoe UI Emoji", 40),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY
        ).pack(pady=(20, 10))

        # Título
        tk.Label(
            fallback,
            text="Player VLibras",
            font=(self._config.FONT_FAMILY_HEADING, 14, "bold"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_PRIMARY
        ).pack()

        # Instrução principal
        tk.Label(
            fallback,
            text=(
                "Para visualizar o avatar LIBRAS embutido,\n"
                "instale a biblioteca tkinterweb:\n\n"
                "pip install tkinterweb\n\n"
                "Ou use o botão 'Abrir no Navegador'\n"
                "para ver a tradução no Chrome/Firefox."
            ),
            font=(self._config.FONT_FAMILY_BODY, 10),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_TEXT_SECONDARY,
            justify=tk.CENTER,
            pady=10
        ).pack()

        # Label que mostrará a URL da última tradução
        self._vlibras_url_label = tk.Label(
            fallback,
            text="",
            font=(self._config.FONT_FAMILY_BODY, 8, "italic"),
            bg=self._config.COLOR_BG_SECONDARY,
            fg=self._config.COLOR_ACCENT,
            wraplength=400,
            cursor="hand2"
        )
        self._vlibras_url_label.pack(pady=(5, 20))

    def _build_footer(self) -> None:
        """
        Constrói o rodapé com barra de status e informações do sistema.
        """

        footer = tk.Frame(self._main_frame, bg="#0A1420", height=28)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)    # Impede o frame de encolher ao conteúdo

        # Status bar com informação em tempo real
        self._status_bar = tk.Label(
            footer,
            text="✓ Sistema inicializado | MediaPipe carregado | TTS pronto | VLibras disponível",
            font=(self._config.FONT_FAMILY_BODY, 8),
            bg="#0A1420",
            fg=self._config.COLOR_TEXT_SECONDARY,
            anchor=tk.W,
            padx=10
        )
        self._status_bar.pack(side=tk.LEFT, fill=tk.Y)

        # Texto do rodapé direito
        tk.Label(
            footer,
            text="LIBRAS Bridge v1.0 • Desenvolvido para acessibilidade hospitalar",
            font=(self._config.FONT_FAMILY_BODY, 8),
            bg="#0A1420",
            fg="#243450",
            padx=10
        ).pack(side=tk.RIGHT, fill=tk.Y)

    # ===========================================================
    # CALLBACKS: Chamados pelos módulos de lógica
    # ===========================================================

    def _on_word_detected(self, sentence: str) -> None:
        """
        Callback chamado pelo PatientModule quando uma palavra é reconhecida.
        Atualiza o display da frase na interface.

        Args:
            sentence: A frase completa acumulada até o momento
        """
        # Atualiza a StringVar — isso automaticamente atualiza todos os Labels vinculados
        self._sentence_var.set(sentence)

        # Esconde o placeholder quando há texto real
        if sentence:
            self._sentence_placeholder.pack_forget()
        else:
            self._sentence_placeholder.pack(anchor=tk.W)

        # Atualiza a barra de status
        self._update_status(f"✓ Sinal reconhecido: {sentence.split()[-1] if sentence else ''}")

    def _on_camera_frame_ready(self, photo) -> None:
        """
        Callback chamado pelo PatientModule quando um frame processado está pronto.
        Atualiza o widget Label da câmera com a nova imagem.

        Args:
            photo: ImageTk.PhotoImage com o frame processado e anotado
        """
        # Atualiza a imagem exibida no Label da câmera
        self._camera_label.configure(image=photo, text="")

        # CRÍTICO: Mantém uma referência ao PhotoImage para evitar garbage collection
        # Sem esta linha, o Tkinter apaga a imagem após o garbage collector rodar
        self._camera_photo = photo

    def _on_translation_ready(self, url: str) -> None:
        self._logger.info(f"Tradução pronta: {url}")
        text = self._doctor_text.get("1.0", tk.END).strip()
        self._root.after(0, lambda: self._open_translation(text))

    def _open_translation(self, text: str) -> None:
        encoded_text = urllib.parse.quote(text, safe="")

        if self._vlibras_server_port and getattr(self, "_webview", None):
            url = f"http://localhost:{self._vlibras_server_port}/player.html#/translate/{encoded_text}"
            self._logger.info(f"Carregando VLibras no WebView: {url}")
            try:
                self._webview.load_url(url)
                self._update_status("✓ Traduzindo para LIBRAS...")
            except Exception as e:
                self._logger.error(f"Falha ao carregar VLibras no WebView: {e}")
                self._update_status("⚠️ Erro ao carregar VLibras no WebView")
        else:
            url = None
            if self._vlibras_server_port:
                url = f"http://localhost:{self._vlibras_server_port}/player.html#/translate/{encoded_text}"
            else:
                url = self._doctor_module.translate_text(text)

            if url:
                import subprocess
                try:
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                    self._logger.info(f"Abrindo VLibras no navegador: {url}")
                    self._update_status("✓ VLibras aberto no navegador")
                except Exception as e:
                    self._logger.error(f"Falha ao abrir navegador: {e}")
                    self._update_status("⚠️ Falha ao abrir navegador")

        if text and len(self._history_listbox.get(0, tk.END)) < 10:
            preview = text[:60] + "..." if len(text) > 60 else text
            self._history_listbox.insert(0, f"[{self._get_time()}] {preview}")


    # ===========================================================
    # HANDLERS DOS BOTÕES
    # ===========================================================

    def _toggle_camera(self) -> None:

        if not self._camera_running:
            # Inicia o módulo paciente
            success = self._patient_module.start(self._root)
            if success:
                self._camera_running = True
                # Atualiza o texto e cor do botão
                self._btn_camera.configure(
                    text="⏹  Parar Câmera",
                    bg="#E05555",
                    activebackground="#B04040"
                )
                self._update_status("✓ Câmera iniciada | Aguardando sinais LIBRAS...")
            else:
                # Falha ao abrir a câmera
                messagebox.showerror(
                    "Erro de Câmera",
                    "Não foi possível acessar a câmera.\n\n"
                    "Verifique se:\n"
                    "• A webcam está conectada\n"
                    "• Nenhum outro programa está usando a câmera\n"
                    "• As permissões de câmera estão concedidas"
                )
        else:
            # Para o módulo paciente
            self._patient_module.stop()
            self._camera_running = False
            # Restaura o botão ao estado inicial
            self._btn_camera.configure(
                text="▶  Iniciar Câmera",
                bg=self._config.COLOR_ACCENT,
                activebackground="#00A88A"
            )
            # Restaura o Label da câmera ao estado inicial
            self._camera_label.configure(
                image="",
                text="📷 Câmera não iniciada\n\nClique em 'Iniciar Câmera'\npara começar"
            )
            self._update_status("⏹ Câmera parada")

    def _speak_patient_sentence(self) -> None:
        """Fala a frase completa acumulada do paciente via TTS."""
        sentence = self._patient_module.get_current_sentence()
        if sentence:
            self._patient_module.speak_sentence()
            self._update_status(f"🔊 Falando: '{sentence[:40]}...' " if len(sentence) > 40 else f"🔊 Falando: '{sentence}'")
        else:
            messagebox.showinfo(
                "Nada para falar",
                "Nenhuma palavra foi reconhecida ainda.\nInicie a câmera e sinalize em LIBRAS."
            )

    def _clear_patient_sentence(self) -> None:
        """Limpa o acumulador de frase do paciente."""
        self._patient_module.clear_sentence()
        self._sentence_var.set("")
        self._sentence_placeholder.pack(anchor=tk.W)
        self._update_status("✓ Frase do paciente limpa")

    def _translate_doctor_text(self) -> None:
        """Lê o texto do campo do médico e envia para tradução."""
        # get("1.0", tk.END): obtém todo o texto do widget Text
        # "1.0" = linha 1, coluna 0 (início); tk.END = fim do texto
        text = self._doctor_text.get("1.0", tk.END).strip()

        if not text:
            messagebox.showwarning(
                "Campo Vazio",
                "Por favor, digite um texto para traduzir."
            )
            return

        # Chama o módulo do médico para processar a tradução
        url = self._doctor_module.translate_text(text)
        if url:
            self._update_status("✓ Texto enviado ao VLibras para tradução")

    def _open_vlibras_browser(self) -> None:
        """Abre o VLibras no navegador padrão como alternativa ao WebView."""
        text = self._doctor_text.get("1.0", tk.END).strip()
        if text:
            self._doctor_module.open_in_browser(text)
        else:
            # Abre o VLibras sem texto para o médico digitar diretamente no site
            import webbrowser
            webbrowser.open(self._config.VLIBRAS_WIDGET_URL)

    def _clear_doctor_text(self) -> None:
        """Limpa o campo de texto do médico."""
        # delete("1.0", tk.END): remove todo o conteúdo do Text widget
        self._doctor_text.delete("1.0", tk.END)

    def _reuse_history_item(self, event) -> None:
        """Ao dar duplo clique no histórico, restaura o texto no campo do médico."""
        # Obtém o índice do item selecionado na Listbox
        selection = self._history_listbox.curselection()
        if selection:
            # Obtém o texto do item selecionado
            item = self._history_listbox.get(selection[0])
            # Remove o prefixo de timestamp "[HH:MM:SS] "
            text = item.split("] ", 1)[1] if "] " in item else item
            # Substitui o conteúdo do campo de texto
            self._doctor_text.delete("1.0", tk.END)
            self._doctor_text.insert("1.0", text)

    # ===========================================================
    # UTILITÁRIOS
    # ===========================================================

    def _update_status(self, message: str) -> None:
        """
        Atualiza a mensagem exibida na barra de status do rodapé.

        Args:
            message: Texto a exibir na status bar
        """
        self._status_bar.configure(text=message)
        self._logger.debug(f"Status: {message}")

    def _get_time(self) -> str:
        """Retorna a hora atual no formato HH:MM:SS para o histórico."""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")

    def on_closing(self) -> None:
        """
        Handler chamado ao fechar a janela (botão X do SO).
        Garante o encerramento seguro de todos os recursos.
        """
        self._logger.info("Encerrando aplicação...")

        # Para o módulo paciente se estiver ativo
        if self._camera_running:
            self._patient_module.stop()

        # Destrói a janela raiz, encerrando o mainloop
        self._root.destroy()

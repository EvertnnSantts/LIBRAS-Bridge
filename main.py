"""
============================================================
  LIBRAS Bridge - Comunicação Hospitalar Acessível
  Arquivo: main.py
  Descrição: Ponto de entrada principal da aplicação.
             Inicializa a interface gráfica e os módulos.
============================================================
"""

# --- Importações da Biblioteca Padrão ---
import sys                      # Fornece acesso a variáveis e funções do interpretador Python
import logging                  # Módulo para registro de logs da aplicação
from pathlib import Path        # Manipulação de caminhos de arquivos de forma orientada a objetos

# --- Importações de Terceiros ---
import tkinter as tk            # Biblioteca padrão para criação de interfaces gráficas (GUI)
from tkinter import ttk         # Extensão do tkinter com widgets com estilos mais modernos

# --- Importações Internas do Projeto ---
from src.ui.main_window import MainWindow        # Classe que gerencia a janela principal da aplicação
from src.utils.logger import setup_logger        # Função utilitária para configurar o sistema de logs
from src.utils.config import AppConfig           # Classe de configurações globais da aplicação


def main() -> None:
    """
    Função principal de inicialização da aplicação.
    Configura o ambiente, cria a janela principal e inicia o loop de eventos.
    """

    # Configura o sistema de logging para registrar eventos e erros
    # O logger escreve no console e em arquivo para facilitar a depuração
    logger = setup_logger(
        name="libras_bridge",                   # Nome do logger (identificador único)
        log_file="logs/app.log",                # Caminho do arquivo onde os logs serão salvos
        level=logging.DEBUG                     # Nível mínimo: DEBUG captura tudo (INFO, WARNING, ERROR também)
    )

    # Registra o início da aplicação no log
    logger.info("=== LIBRAS Bridge iniciando... ===")

    # Carrega as configurações globais da aplicação (tamanhos, cores, caminhos, etc.)
    config = AppConfig()

    # Cria a instância da janela raiz do Tkinter
    # Tk() é o widget "root" — o container de mais alto nível de toda a GUI
    root = tk.Tk()

    # Define o título exibido na barra de título da janela do sistema operacional
    root.title("LIBRAS Bridge — Comunicação Hospitalar Acessível")

    # Define o tamanho inicial da janela em pixels (largura x altura)
    root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")

    # Define o tamanho mínimo para evitar que o usuário redimensione demais e quebre o layout
    root.minsize(config.MIN_WIDTH, config.MIN_HEIGHT)

    # Centraliza a janela na tela do monitor ao abrir
    _center_window(root, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    # Configura o ícone da janela (se existir o arquivo de ícone)
    icon_path = Path("assets/icon.png")         # Caminho para o ícone da aplicação
    if icon_path.exists():                       # Só tenta carregar se o arquivo existir
        try:
            # PhotoImage carrega imagens PNG para uso no Tkinter
            icon = tk.PhotoImage(file=str(icon_path))
            root.iconphoto(True, icon)           # True = aplica o ícone em todas as janelas filhas também
        except Exception as e:
            # Se falhar ao carregar o ícone, apenas registra o aviso e continua normalmente
            logger.warning(f"Não foi possível carregar o ícone: {e}")

    # Instancia a janela principal da aplicação, passando o root e as configurações
    # MainWindow é responsável por criar e organizar todos os frames/módulos
    app = MainWindow(root=root, config=config, logger=logger)

    # Define o protocolo de fechamento da janela (botão X do SO)
    # Ao clicar em fechar, chama o método de encerramento seguro da aplicação
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # Registra que a interface foi carregada com sucesso
    logger.info("Interface gráfica carregada com sucesso.")

    # Inicia o loop principal de eventos do Tkinter
    # mainloop() bloqueia aqui e fica processando eventos (cliques, teclas, etc.)
    # até que a janela seja fechada
    root.mainloop()

    # Quando mainloop() retorna (janela fechada), registra o encerramento
    logger.info("=== LIBRAS Bridge encerrado. ===")


def _center_window(window: tk.Tk, width: int, height: int) -> None:
    """
    Calcula e aplica a posição para centralizar a janela na tela.

    Args:
        window: A janela raiz do Tkinter a ser centralizada.
        width:  A largura desejada da janela em pixels.
        height: A altura desejada da janela em pixels.
    """
    # Obtém a largura total da tela do monitor em pixels
    screen_width = window.winfo_screenwidth()

    # Obtém a altura total da tela do monitor em pixels
    screen_height = window.winfo_screenheight()

    # Calcula a posição X (horizontal) para centralizar a janela
    # Fórmula: (largura_da_tela - largura_da_janela) / 2
    x = (screen_width - width) // 2

    # Calcula a posição Y (vertical) para centralizar a janela
    # Fórmula: (altura_da_tela - altura_da_janela) / 2
    y = (screen_height - height) // 2

    # Aplica a geometria no formato "LARGURAxALTURA+X+Y"
    # O +X+Y define a posição do canto superior esquerdo da janela
    window.geometry(f"{width}x{height}+{x}+{y}")


# Ponto de entrada do script Python
# Esta condição garante que main() só seja chamada quando este arquivo
# for executado diretamente (não quando importado como módulo)
if __name__ == "__main__":
    main()

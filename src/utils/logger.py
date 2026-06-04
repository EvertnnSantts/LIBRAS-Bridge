"""
============================================================
  LIBRAS Bridge
  Arquivo: src/utils/logger.py
  Descrição: Configuração do sistema de logging da aplicação.
             Grava logs tanto no console (para desenvolvimento)
             quanto em arquivo rotativo (para produção).
============================================================
"""

# --- Importações da Biblioteca Padrão ---
import logging                                          # Módulo de logging padrão do Python
import sys                                             # Acesso ao stdout para o handler de console
from pathlib import Path                               # Manipulação de caminhos de forma orientada a objetos
from logging.handlers import RotatingFileHandler      # Handler que rotaciona o arquivo de log por tamanho


def setup_logger(
    name: str,
    log_file: str = "logs/app.log",
    level: int = logging.DEBUG
) -> logging.Logger:
    """
    Cria e configura um logger com dois handlers:
      1. StreamHandler → exibe logs coloridos no console (terminal)
      2. RotatingFileHandler → grava logs em arquivo com rotação automática

    Args:
        name:     Nome único do logger (geralmente o nome do módulo ou app)
        log_file: Caminho do arquivo de log a ser criado/atualizado
        level:    Nível mínimo de log a registrar (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Instância do logger configurado e pronto para uso
    """

    # Obtém (ou cria) um logger com o nome especificado
    # Se já existir um logger com esse nome, retorna o existente
    logger = logging.getLogger(name)

    # Define o nível mínimo de mensagens que este logger processará
    # Mensagens abaixo deste nível são ignoradas silenciosamente
    logger.setLevel(level)

    # Evita adicionar handlers duplicados caso esta função seja chamada múltiplas vezes
    # handlers é uma lista; se já tiver algum, o logger já foi configurado
    if logger.handlers:
        return logger

    # -------------------------------------------------------
    # FORMATO DAS MENSAGENS DE LOG
    # -------------------------------------------------------

    # Define o formato de cada linha de log
    # %(asctime)s   → data e hora do evento (ex: 2024-01-15 10:30:45,123)
    # %(name)s      → nome do logger
    # %(levelname)s → nível do log (DEBUG, INFO, etc.)
    # %(filename)s  → nome do arquivo onde o log foi gerado
    # %(lineno)d    → número da linha no arquivo
    # %(message)s   → a mensagem em si
    log_format = (
        "%(asctime)s | %(name)s | %(levelname)-8s | "
        "%(filename)s:%(lineno)d | %(message)s"
    )

    # Cria o objeto Formatter com o formato definido acima
    formatter = logging.Formatter(
        fmt=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"    # Formato da data/hora sem milissegundos
    )

    # -------------------------------------------------------
    # HANDLER 1: CONSOLE (StreamHandler)
    # Exibe os logs no terminal enquanto a aplicação está rodando
    # -------------------------------------------------------

    # StreamHandler direciona os logs para o stdout (saída padrão do terminal)
    console_handler = logging.StreamHandler(sys.stdout)

    # Define o nível mínimo para este handler específico
    # INFO é suficiente no console (evita poluição com mensagens DEBUG)
    console_handler.setLevel(logging.INFO)

    # Aplica o formatador ao handler do console
    console_handler.setFormatter(formatter)

    # Adiciona o handler de console ao logger
    logger.addHandler(console_handler)

    # -------------------------------------------------------
    # HANDLER 2: ARQUIVO ROTATIVO (RotatingFileHandler)
    # Grava todos os logs em arquivo, rotacionando quando atinge o tamanho máximo
    # -------------------------------------------------------

    # Cria o diretório de logs se ele não existir
    # parents=True: cria diretórios intermediários se necessário
    # exist_ok=True: não lança erro se o diretório já existir
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # RotatingFileHandler: rotaciona o arquivo quando atinge maxBytes
    # maxBytes=5MB: quando o arquivo chega a 5MB, renomeia para app.log.1 e cria novo app.log
    # backupCount=3: mantém no máximo 3 arquivos de backup (app.log.1, .2, .3)
    # encoding='utf-8': garante suporte a caracteres especiais do português
    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=5 * 1024 * 1024,   # 5 MB em bytes
        backupCount=3,               # Mantém 3 arquivos de backup
        encoding="utf-8"             # Codificação UTF-8 para suporte ao português
    )

    # O arquivo recebe TODOS os logs a partir do nível DEBUG
    file_handler.setLevel(logging.DEBUG)

    # Aplica o mesmo formatador ao handler de arquivo
    file_handler.setFormatter(formatter)

    # Adiciona o handler de arquivo ao logger
    logger.addHandler(file_handler)

    # Retorna o logger completamente configurado
    return logger

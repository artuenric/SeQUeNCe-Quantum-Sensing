# logging_setup.py

import logging
import sequence.utils.log as seq_log
from typing import List

# Importa a lista diretamente do nosso novo arquivo de configuração
from .tracked_modules import TRACKED_MODULES

def setup_logger(timeline, log_file_name: str, mode: str = 'custom'):
    """
    Configura o logger, permitindo escolher entre dois modos.

    Args:
        timeline (Timeline): A timeline da simulação.
        log_file_name (str): O nome do arquivo de log de saída. Sem extensão.
        mode (str): 'custom' para rastrear apenas nossos módulos,
                    'verbose' para registrar tudo.
    """
    log_file_name += ".txt"
    print(f"Configurando logger para o modo: '{mode}'")

    if mode == 'verbose':
        # MODO VERBOSO: Usa o logger padrão do Python para capturar tudo.
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            filename=log_file_name,
            filemode="w"
        )
        print(f"Todos os logs serão salvos em '{log_file_name}'.")

    elif mode == 'custom':
        # MODO CUSTOMIZADO: Usa o logger do SeQUeNCe com nosso filtro.
        seq_log.set_logger(__name__, timeline, log_file_name)
        seq_log.set_logger_level('INFO')
        
        # Simplesmente usamos a lista que importamos. Sem ler arquivos!
        for module_name in TRACKED_MODULES:
            seq_log.track_module(module_name)
        
        print(f"Apenas os módulos {TRACKED_MODULES} serão rastreados em '{log_file_name}'.")

    else:
        raise ValueError(f"Modo de log '{mode}' desconhecido. Use 'custom' ou 'verbose'.")
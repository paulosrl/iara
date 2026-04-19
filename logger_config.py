import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE = "/app/app_errors.log" if os.path.exists("/app") else "app_errors.log"

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # Handler para arquivo com ROTAÇÃO (Máximo 5MB, mantém 3 backups)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler para console (importante para Docker logs)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger

import logging
import os

def setup_logging():
    os.makedirs("logs", exist_ok = True)

    logging.basicConfig(
        filename = "logs/netbox.log",
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s"
    )
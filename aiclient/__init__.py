import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    filename='log.log',
    filemode='a'
)
logger = logging.getLogger('AIClient')

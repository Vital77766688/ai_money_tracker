import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.ERROR,
    filename='log.log',
    filemode='a'
)
logger = logging.getLogger('BugdetApp')

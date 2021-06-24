
import logging


def _get_logger(app_name):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
                                  '%(module)s:[%(funcName)s]:%(lineno)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    log = logging.getLogger(app_name)
    log.addHandler(ch)
    log.setLevel(logging.DEBUG)
    return log


__VERSION__ = "0.1.0"
__NAME__ = "XML Tree"
__APP_NAME__ = str.format(f"{__NAME__}")

logger = _get_logger(__APP_NAME__)

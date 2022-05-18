
import logging
import os
import sys

from PyQt5.QtGui import QIcon

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))


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
__APP_NAME__ = str.format(f"{__NAME__}:{__VERSION__}")

logger = _get_logger(__APP_NAME__)


def theme_icon_with_fallback(icon_name):
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        logger.debug(f"Falling back to resources for icon {icon_name}")
        icon_path = os.path.join(os.path.dirname(__file__), f"../resources/images/{icon_name}.svg")
        icon = QIcon(icon_path)
    return icon

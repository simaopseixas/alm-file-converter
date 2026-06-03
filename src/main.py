import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui_converter import ConverterWidget
from gui_logger import LoggerWindow


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    icon_path = Path(__file__).resolve().parent / "attributes" / "ALM.ico"
    app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize the logger
    logger = LoggerWindow()
    logger.setWindowIcon(QIcon(str(icon_path)))
    logger.resize(1000, 500)
    logger.show()

    # logger.print("=======================================================================================================================================")
    # logger.print("                                                         ALM File Converter                                                            ")
    # logger.print("=======================================================================================================================================")

    logger.print("=======================================================================================================================================")
    logger.print("                                                                                                                                       ")
    logger.print("                        ###    ##       ##     ##        #######  ##  ##       ######                                                  ")
    logger.print("                       ## ##   ##       ###   ###        ##       ##  ##       ##                                                      ")
    logger.print("                      ##   ##  ##       #### ####        ######   ##  ##       ######                                                  ")
    logger.print("                      #######  ##       ## ### ##        ##       ##  ##       ##                                                      ")
    logger.print("                      ##   ##  #######  ##  #  ##        ##       ##  #######  ######                                                  ")
    logger.print("                                                                                                                                       ")
    logger.print("                                    ######  #######  ##   ##  ##   ##  #######  ######   #######  ######  ######                       ")
    logger.print("                                    ##      ##   ##  ###  ##  ##   ##  ##       ##   ##    ##     ##      ##   ##                      ")
    logger.print("                                    ##      ##   ##  #### ##  ##   ##  ######   ######     ##     ######  ######                       ")
    logger.print("                                    ##      ##   ##  ## ####   ## ##   ##       ##   ##    ##     ##      ##   ##                      ")
    logger.print("                                    ######  #######  ##  ###    ###    #######  ##   ##    ##     ######  ##   ##                      ")
    logger.print("                                                                                                                                       ")
    logger.print("=======================================================================================================================================")

    # Initialize the main window
    window = ConverterWidget(logger)
    logger.set_main_window(window)
    window.show()

    sys.exit(app.exec())
import os
import sys
import time

from ABGR import apply_abgr

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, qApp, QFileDialog, QLabel
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QProgressBar, QMessageBox, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, QPoint, QCoreApplication
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer

TOP_NAME = "arca.live/b/aiart"
APP_NAME = "ABG Remover GUI"
APP_TITLE = "ABG Remover GUI - 드래그 드랍하여 배경과 이미지를 분리!"

if getattr(sys, 'frozen', False):
#pyinstaller를 통해 만들어진 .exe 로 수행한 경우 최초경로. .exe가 압축이 풀리면서 사용자 appdata 폴더의 임시폴더에 생성되므로 기억해야 함.
    execute_path = os.path.dirname(os.path.abspath(sys.executable))  
else:
    execute_path = os.path.dirname(os.path.abspath(__file__)) 
SRC_MODEL = execute_path+"\\" + "model\\isnetis.onnx"


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path).replace("\\", "/")


class Worker(QThread):
    progressChanged = pyqtSignal(int)

    def __init__(self, filenames):
        super().__init__()
        self.power = True
        self.filenames = filenames
        self.count = len(filenames)
        self.index = 0

    def run(self):
        while self.power:
            if self.index < self.count:
                print("iter", self.index)
                filename = self.filenames[self.index]
                apply_abgr(SRC_MODEL, filename)
                self.progressChanged.emit(int(self.index / self.count * 99))
                self.index += 1
            else:
                self.power = False
                self.progressChanged.emit(100)

    def stop(self):
        # 멀티쓰레드를 종료하는 메소드
        self.power = False
        self.quit()
        self.wait(3000)  # 3초 대기 (바로 안꺼질수도)


class ProgressDialog(QDialog):
    def __init__(self, parent, filenames):
        super().__init__()
        self.filenames = filenames
        self.parent = parent
        self.initUI(parent.pos())
        QTimer.singleShot(100,self.start)
        super().exec_()

    def initUI(self, parent_pos):
        self.setWindowTitle('Sub Window')
        self.setGeometry(parent_pos.x(), parent_pos.y(), 200, 100)
        layout = QVBoxLayout()

        progressbar = QProgressBar(self)
        progressbar.setAlignment(Qt.AlignCenter)
        self.progressbar = progressbar

        label = QLabel("Loading...")
        label.setAlignment(Qt.AlignCenter)
        font = label.font()
        font.setPointSize(18)
        label.setFont(font)
        self.label = label

        button = QPushButton("확인")
        button.clicked.connect(self.on_button_clicked)
        button.setEnabled(False)
        self.button = button

        layout.addStretch(1)
        layout.addWidget(self.progressbar)
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.button)
        layout.addStretch(1)

        self.setLayout(layout)

    def set_value(self, value):
        print(value)
        self.label.setText(str(value) + "%")
        self.progressbar.setValue(value)

        if value >= 100:
            self.button.setEnabled(True)

    def start(self):
        print("start")
        worker = Worker(self.filenames)
        worker.progressChanged.connect(self.set_value)
        self.worker = worker
        worker.start()

    def on_button_clicked(self):
        self.worker.stop()
        self.reject()

    def closeEvent(self, event):
        if self.worker and self.worker.power:
            reply = QMessageBox.question(self, '확인', '정말 작업을 중지하시겠습니까?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.worker.stop()
                event.accept()
            else:
                event.ignore()


class MyWidget(QMainWindow):

    def __init__(self, app):
        super().__init__()
        self.app = app

        self.init_window()
        self.init_content()
        self.init_menubar()
        self.setAcceptDrops(True)
        self.show()

    def init_window(self):
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(resource_path('icon.ico')))
        self.settings = QSettings(TOP_NAME, APP_NAME)
        self.setFixedSize(512, 512)
        self.move(self.settings.value("pos", QPoint(300, 300)))

    def init_content(self):
        main_layout = QVBoxLayout()
        button = QPushButton("", self)
        button.resize(512, 512)
        button.clicked.connect(self.show_select_dialog)
        button.setStyleSheet("background-image: url("+resource_path("content.png")+");")
        self.button = button

        main_layout.addStretch(10)
        main_layout.addWidget(self.button, 512)
        main_layout.addStretch(10)
        self.setLayout(main_layout)

    def init_menubar(self):
        selectAction = QAction('Select File(s)', self)
        selectAction.setShortcut('Ctrl+O')
        selectAction.setStatusTip('Select File(s) to apply ABG Removing')
        selectAction.triggered.connect(self.show_select_dialog)

        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+W')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.quit_app)

        aboutAction = QAction('About', self)
        aboutAction.setStatusTip('About application')
        aboutAction.triggered.connect(self.show_about_dialog)

        self.statusBar()

        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        filemenu = menubar.addMenu('&File')
        filemenu.addAction(selectAction)
        filemenu.addAction(exitAction)
        filemenu = menubar.addMenu('&Etc')
        filemenu.addAction(aboutAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        self.apply_abgr_to_files(files)

    def closeEvent(self, e):
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        e.accept()

    def show_select_dialog(self):
        select_dialog = QFileDialog()
        select_dialog.setFileMode(QFileDialog.ExistingFiles)
        fname = select_dialog.getOpenFileNames(self, 'Open file to apply ABGR', '', 'PNG File(*.png)')

        print(fname)
        if fname != "" and type(fname[0]) == list and len(fname[0]) > 0:
            self.apply_abgr_to_files(fname[0])

    def show_about_dialog(self):
        QMessageBox.information(self, 'About', """
본진 : 아카라이브 AI그림 채널 https://arca.live/b/aiart
만든이 : https://arca.live/b/aiart @DeepCreamPy
원본 WebUI 확장기능 : https://github.com/KutsuyaYuki/ABG_extension
원본 ABGRemoving : https://huggingface.co/spaces/skytnt/anime-remove-background
        """)

    # filenames must be ["full src", "full src", ...]
    def apply_abgr_to_files(self, filenames):
        reply = QMessageBox.question(self,'작업 확인','총 '+str(len(filenames))+' 개의 이미지를 작업합니다. 계속하시겠습니까?', 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            pd = ProgressDialog(self, filenames)

    def quit_app(self):
        time.sleep(0.1)
        self.close()
        self.app.closeAllWindows()
        QCoreApplication.exit(0)


if __name__ == '__main__':
    input_list = sys.argv
    app = QApplication(sys.argv)
    widget = MyWidget(app)

    time.sleep(0.1)
    if getattr(sys, 'frozen', False):
    #pyinstaller를 통해 만들어진 .exe 로 수행한 경우 최초경로. .exe가 압축이 풀리면서 사용자 appdata 폴더의 임시폴더에 생성되므로 기억해야 함.
        execute_path = os.path.dirname(os.path.abspath(sys.executable))  
    else:
        execute_path = os.path.dirname(os.path.abspath(__file__)) 

    if not os.path.isfile(SRC_MODEL):
        QMessageBox.critical(widget, '에러', "모델 파일이 존재하지 않습니다. 경로는 'model/isnetis.ckpt'입니다.")
        QTimer.singleShot(100,widget.quit_app)
    elif len(input_list) > 1:
        src_list = input_list[1:]
        widget.apply_abgr_to_files(src_list)

    sys.exit(app.exec_())
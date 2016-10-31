from mainwindow import Ui_MainWindow
from PyQt5.QtWidgets import QMessageBox, QMainWindow,QApplication, QGroupBox, QGridLayout, QProgressBar, QLabel, QFileDialog
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from copy import deepcopy
import pafy
import time
import string
import requests
import shutil
import os
import threading


# http://stackoverflow.com/a/1094933/5163807
# made my day
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class Communicate(QObject):
    signal = pyqtSignal(int, int, float, float, float)



class ytDownloader(Ui_MainWindow):
    def __init__(self):
        Ui_MainWindow.__init__(self)
        self.videoObj = None
        self.currentIndex = -1
        self.downloadQueue = []

    def configureUI(self):
        self.hideDownloadItemGrid(True)
        self.urlInput.returnPressed.connect(self.reloadDiGrid)
        self.videoFormatSelector.currentIndexChanged.connect(self.setCurrentIndex)
        self.addButton.clicked.connect(self.downloadInit)

    def selectDownloadLocation(self):
        dirname = QFileDialog.getExistingDirectory(self, "Select download location")
        if dirname:
            self.downloadLocationInput.setText(dirname)

    def hideDownloadItemGrid(self, b):
        targetWidgets = [self.videoAuthor, self.videoDownloadSize, self.videoViews, self.videoDuration, self.videoFormatSelector, self.videoThumb, self.videoTitle ]
        for widget in targetWidgets:
            widget.setVisible(not b)

    
    def reloadDiGrid(self):
        if self.videoObj : del self.videoObj; self.videoObj = None
        self.hideDownloadItemGrid(False)
        try:
            self.videoObj = pafy.new(self.urlInput.text(), basic=True)
        except Exception as e:
            if (len (str(e).split(":", 1)) > 1):
                QMessageBox.information(None, "Err...", str(e).split(":", 1)[1], QMessageBox.Ok, QMessageBox.Ok)
            else:
                QMessageBox.information(None, "Err...", str(e).split(":", 1)[0], QMessageBox.Ok, QMessageBox.Ok)
            return

        self.videoTitle.setText("<i>"+self.videoObj.title+"</i>")
        self.videoAuthor.setText("<b>"+self.videoObj.author+"</i>")
        self.videoViews.setText("<b>" + str(self.videoObj.viewcount) + "</b> views")
        self.videoDuration.setText("<b>Duration :</b> " + self.videoObj.duration)
        
        # parse the list of supported stream formats from self.videoObj.*stream
        
        self.streamsList = self.videoObj.streams + self.videoObj.audiostreams + self.videoObj.videostreams
        for item in self.streamsList:
            itemstr = item.__str__()
            if itemstr.startswith("normal"):
                itemstr = itemstr.replace("normal", "video")
                itemicon = QIcon("resources/ic_music_video_black_24px.svg")
            elif itemstr.startswith("video"):
                itemicon = QIcon("resources/ic_video_label_black_24px.svg")
                itemstr = itemstr.replace("video", "video-only")
            elif itemstr.startswith("audio"):
                itemicon = QIcon("resources/ic_audiotrack_black_24px.svg")
            else:
                itemicon = QIcon()
            self.videoFormatSelector.addItem(itemicon, itemstr)
            self.videoFormatSelector.setCurrentIndex(self.streamsList.index(self.videoObj.getbest()))

        try:
            r = requests.get(self.videoObj.bigthumb, stream=True)
            thumbfile = "."+self.videoObj.videoid
            if r.status_code == 200:
                with open(thumbfile, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                    self.videoThumb.setPixmap(QPixmap(thumbfile).scaled(64, 64, transformMode=Qt.SmoothTransformation))
            else:
                raise 
        except Exception as e:
            print("Thumbnail retrieval failed", e)
            pass 

    def setCurrentIndex(self, i):
        self.currentIndex = i
        self.videoDownloadSize.setText("<b>" + sizeof_fmt(self.streamsList[i].get_filesize()) + "</b>")

    def downloadInit(self):
        if (self.downloadLocationInput.text().strip() == ""):
            self.downloadLocationInput.setText(os.path.join(os.path.expanduser('~'), 'Downloads'))
        downloadStream = self.streamsList[self.currentIndex]
        targetFile = os.path.join(self.downloadLocationInput.text(), self.videoObj.title)
        newGroup = QGroupBox()
        grid = QGridLayout()
        di_title = QLabel(self.videoTitle.text())
        di_thumb = QLabel()
        di_thumb.setPixmap(QPixmap(self.videoThumb.pixmap()))
        di_speed = QLabel("")
        di_pbar = QProgressBar()
        di_completed = QLabel("")
        di_size = QLabel("")
        di_eta = QLabel("")
        grid.addWidget(di_thumb, 0, 0, 2, 1)
        grid.addWidget(di_title, 0, 1, 1, 3)
        grid.addWidget(di_completed, 0, 4, 1, 1)
        grid.addWidget(di_pbar, 1, 1, 1, 2)
        grid.addWidget(di_speed, 1, 3, 1, 1)
        grid.addWidget(di_size, 1, 4, 1, 1)
        grid.addWidget(di_eta, 1, 5, 1, 1)
        comm = Communicate()
        
        def updateValues(total_bytes, bytes_downloaded, ratio, rate, eta):
            di_pbar.setValue(ratio*100)
            di_speed.setText(str(rate) + " kbps")
            di_completed.setText(sizeof_fmt(bytes_downloaded))
            di_size.setText(sizeof_fmt(total_bytes))
            m, s = divmod(eta, 60)
            h, m = divmod(m, 60)
            di_eta.setText("%d:%02d:%02d" % (h,m,s))

        comm.signal.connect(updateValues)
        th = threading.Thread(target=downloadStream.download, args=(targetFile, False, updateValues,))
        th.start()

        newGroup.setLayout(grid)
        self.downloadListLayout.insertWidget(0, newGroup)
        self.downloadQueue.append(newGroup)         


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = ytDownloader()
    ui.setupUi(MainWindow)
    ui.configureUI()
    MainWindow.show()
    sys.exit(app.exec_())
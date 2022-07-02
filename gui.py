import os
import matplotlib 
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.image as img
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PyQt5 import uic, QtCore , QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout ,QListWidgetItem ,QFileDialog
import numpy as np
import ctypes

myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

import cv2
from image_process import rotate_image, resize_image, mirror_image, save_lbl

img_files = []
dir_source=""
dir_output=""
selected_pos={}
rects = {}
selected_item=""

angle_start = ""
angle_step = ""
angle_stop = ""
scale_start = ""
scale_step = ""
scale_stop = ""
mirror = False
save_format = "csv"

Form = uic.loadUiType(os.path.join(os.getcwd(), "theme.ui"))[0]
class MainWindow(QMainWindow , Form):
    def __init__(self, *args, **kwargs):
        QMainWindow.__init__(self, *args, **kwargs)
        
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('./assets/icon.png'))
        self.listWidget.setIconSize(QtCore.QSize(50, 50))
        self.choose_source_button.clicked.connect(self.source_button_choose)
        self.choose_output_button.clicked.connect(self.output_button_choose)
        self.generate_btn.clicked.connect(self.generate_btn_action)
        self.clear_button.clicked.connect(self.clear)
        self.listWidget.itemClicked.connect(self.img_selected)
       
        self.fig =  plt.figure(facecolor='#363d3a')
        self.ax = self.fig.add_axes([0.05, 0.05, 0.9, 0.9], frame_on=True, facecolor='#2a2e2c')

        self.ax.tick_params(axis="both", labelcolor='none', top=False, bottom=False, left=False, right=False)
        
        self.canvas = FigureCanvas(self.fig)

        self.old_rect = None
        self.start_labeling_flag = False
        self.coord1 = [0, 0]
        self.coord2 = [0, 0]
        self.canvas.mpl_connect('button_press_event', self.mouse_click)
        self.canvas.mpl_connect('button_release_event', self.mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self.mouse_event)

        l = QVBoxLayout(self.img_widget)
        l.addWidget(self.canvas)

        self.thread = None

        self.sacle_txtbx_start.textChanged.connect(self.scale_start_changed)
        self.sacle_txtbx_step.textChanged.connect(self.scale_step_changed)
        self.sacle_txtbx_stop.textChanged.connect(self.scale_stop_changed)
        self.angle_txtbx_start.textChanged.connect(self.angle_start_changed)
        self.angle_txtbx_step.textChanged.connect(self.angle_step_changed)
        self.angle_txtbx_stop.textChanged.connect(self.angle_stop_changed)
        self.mirror_chkbx.stateChanged.connect(self.mirror_changed)

        self.save_format_btn_csv.toggled.connect(self.save_format_btn_changed)

    def source_button_choose(self):
        global dir_source,img_files,selected_pos,selected_item,rects
        dir_source=str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if(dir_source==""):
            return
        self.source_dir.setText(dir_source)
        img_files=[dir_source + "/" + _ for _ in os.listdir(dir_source) if _.endswith(".jpg") or _.endswith(".png")]
        self.listWidget.clear()
        selected_pos={}
        selected_item=""
        rects = {}
        self.ax.clear()
        self.canvas.draw()
        self.old_rect=None
        for dir in img_files:
            icon = QtGui.QIcon(dir)
            selected_pos[dir]=[[-1,-1],[-1,-1]]
            item = QListWidgetItem(icon, dir)
            size = QtCore.QSize()
            size.setHeight(50)
            size.setWidth(50)
            item.setSizeHint(size)
            self.listWidget.addItem(item)
            
    def output_button_choose(self):
        global dir_output
        dir_output=str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.textBrowser_2.setText(dir_output)
        
    def clear(self):
        global selected_pos,selected_item
        if(selected_item==""):
            return
        selected_pos[selected_item]=[[-1,-1],[-1,-1]]
        if selected_item in rects:
            rects.pop(selected_item)
        if self.old_rect is not None:
            self.ax.patches.remove(self.old_rect)
        self.fig.canvas.draw()
        self.old_rect=None
        self.textBrowser.setText("")
        self.textBrowser_3.setText("")
        self.textBrowser_4.setText("")
        self.textBrowser_5.setText("")
        
    def img_selected(self, item):
        global selected_item
        image = img.imread(item.text())
        selected_item=item.text()
        self.ax.imshow(image)
        self.canvas.draw()
        self.ax.set_facecolor("#2a2e2c")

        if self.old_rect is not None:
                self.ax.patches.remove(self.old_rect)
        if item.text() in rects:
            rect = rects[item.text()]
            self.ax.add_patch(rect)
            self.old_rect = rect
        else:
            self.old_rect = None
        self.fig.canvas.draw()

        if(selected_pos[item.text()][0][0]==-1):
            self.textBrowser.setText("")
            self.textBrowser_3.setText("")
        else:
            self.textBrowser.setText(str(selected_pos[item.text()][0][0]))
            self.textBrowser_3.setText(str(selected_pos[item.text()][0][1]))
            
        if(selected_pos[item.text()][1][0]==-1):
            self.textBrowser_4.setText("")
            self.textBrowser_5.setText("")
        else:
            self.textBrowser_4.setText(str(selected_pos[item.text()][1][0]))
            self.textBrowser_5.setText(str(selected_pos[item.text()][1][1]))
            
    def mouse_click(self, event):
        self.start_labeling_flag = True
        if event.xdata is None or event.ydata is None or selected_item=="":
            self.start_labeling_flag = False
            return
        self.coord1[0] = round(event.xdata)
        self.coord1[1] = round(event.ydata)

    def mouse_release(self, event):
        if self.start_labeling_flag:
            self.start_labeling_flag = False
            if event.xdata is None or event.ydata is None:
                self.coord2[0] = self.x
                self.coord2[1] = self.y
            else:
                self.coord2[0] = round(event.xdata)
                self.coord2[1] = round(event.ydata)

            selected_pos[selected_item][0][0] = self.coord1[0]
            selected_pos[selected_item][0][1] = self.coord1[1]
            selected_pos[selected_item][1][0] = self.coord2[0]
            selected_pos[selected_item][1][1] = self.coord2[1]

            self.textBrowser.setText(str(selected_pos[selected_item][0][0]))
            self.textBrowser_3.setText(str(selected_pos[selected_item][0][1]))
            self.textBrowser_4.setText(str(selected_pos[selected_item][1][0]))
            self.textBrowser_5.setText(str(selected_pos[selected_item][1][1]))

    def mouse_event(self, event):
        if self.start_labeling_flag:
            if event.xdata is not None and event.ydata is not None:
                self.x = round(event.xdata)
                self.y = round(event.ydata)
                rect = patches.Rectangle((self.coord1[0], self.coord1[1]), self.x - self.coord1[0], self.y - self.coord1[1], linewidth=1, edgecolor='r', facecolor='none')
                rects[selected_item] = rect
                if self.old_rect is not None:
                    self.ax.patches.remove(self.old_rect)
                self.ax.add_patch(rect)
                self.old_rect = rect
                self.fig.canvas.draw()
    
    def scale_start_changed(self, value):
        global scale_start
        try:
            value = float(value)
        except Exception:
            self.sacle_txtbx_start.setText(str(scale_start))
            return
        scale_start = value
    
    def scale_stop_changed(self, value):
        global scale_stop
        try:
            value = float(value)
        except Exception:
            self.sacle_txtbx_stop.setText(str(scale_stop))
            return
        scale_stop = value     
    
    def scale_step_changed(self, value):
        global scale_step
        try:
            value = float(value)
        except Exception:
            self.sacle_txtbx_step.setText(str(scale_step))
            return
        scale_step = value
         
    def angle_start_changed(self, value):
        global angle_start
        try:
            value = float(value)
        except Exception:
            self.angle_txtbx_start.setText(str(angle_start))
            return
        angle_start = value
        
    def angle_stop_changed(self, value):
        global angle_stop
        try:
            value = float(value)
        except Exception:
            self.angle_txtbx_stop.setText(str(angle_stop))
            return
        angle_stop = value
        
    def angle_step_changed(self, value):
        global angle_step
        try:
            value = float(value)
        except Exception:
            self.angle_txtbx_step.setText(str(angle_step))
            return
        angle_step = value
        
    def mirror_changed(self, state):
        global mirror
        mirror = state

    def save_format_btn_changed(self):
        global save_format
        if self.save_format_btn_csv.isChecked():
            save_format = "csv"
        else:
            save_format = "json"
    
    def generate_btn_action(self):
        if scale_start == "" or scale_stop == "" or scale_step == "":
            return
        if angle_start == "" or angle_stop == "" or angle_step == "":
            return
        if dir_source=="" or dir_output=="":
            return
        if len(selected_pos)==0:
            return
        
        self.generate_btn.setText("Running ...")
        self.generate_btn.setDisabled(True)
        self.clear_button.setDisabled(True)
        self.choose_source_button.setDisabled(True)
        self.choose_output_button.setDisabled(True)
        self.thread = GenThread(self)
        self.thread.update_trigger.connect(self.update)
        self.thread.finished_trigger.connect(self.finished)
        self.thread.start()
    
    def update(self, n, total):
        self.generate_btn.setText(f"{n}/{total}")

    def finished(self):
        self.thread = None
        self.generate_btn.setText("Generate")
        self.generate_btn.setDisabled(False)
        self.clear_button.setDisabled(False)
        self.choose_source_button.setDisabled(False)
        self.choose_output_button.setDisabled(False)

class GenThread(QtCore.QThread):
    update_trigger = QtCore.pyqtSignal(int, int)
    finished_trigger = QtCore.pyqtSignal()

    def __init__(self, window):
        QtCore.QThread.__init__(self, parent=window)
        self.supported_formats = ["jpg", "png", "bmp"]
        self.src_path = dir_source
        self.dst_path = dir_output
        self.angle_start = angle_start
        self.angle_step = angle_step
        self.angle_stop = angle_stop
        self.scale_start = scale_start
        self.scale_step = scale_step
        self.scale_stop = scale_stop
        self.mirror = mirror
        self.save_format = save_format
        self.lbl_dict = selected_pos
        self.window = window

    def run(self):
        if not os.path.exists(self.dst_path):
            os.makedirs(self.dst_path)
        images_pathes = os.listdir(self.src_path)
        temp_list = []
        [temp_list.append(img_path) if img_path.endswith(".jpg") or img_path.endswith(".png") or img_path.endswith(".bmp") else None for img_path in images_pathes]
        images_pathes = temp_list
        total_num = len(images_pathes)
        self.update_trigger.emit(0, total_num)
        for n, img_path in enumerate(images_pathes):
            img_format = img_path.split(".")[-1]
            if not img_format in self.supported_formats:
                continue
            # img_path = os.path.join(self.src_path, img_path)
            img_path = self.src_path + "/" + img_path
            orig_img = cv2.imread(img_path)
            img_name = img_path.split("/")[-1].replace("." + img_format, "")
            if not img_path in self.lbl_dict:
                continue
            lbl = np.array(self.lbl_dict[img_path])
            for scale in np.arange(self.scale_start, self.scale_stop + self.scale_step, self.scale_step):
                for angle in np.arange(self.angle_start, self.angle_stop + self.angle_step, self.angle_step):
                    img, lbl = resize_image(orig_img, lbl, scale)
                    img, lbl = rotate_image(img, lbl, angle)
                    
                    img_save_name = img_name + "_" + str(angle) + "_" + str(scale) + "." + img_format
                    save_path = os.path.join(self.dst_path, img_save_name)
                    save_lbl(self.dst_path, lbl, img_save_name, self.save_format)
                    cv2.imwrite(save_path, img)

                    if self.mirror:
                        img, lbl = mirror_image(img, lbl)
                        img_save_name = img_name + "_" + str(angle) + "_" + str(scale) + "_flip" + "." + img_format
                        save_path = os.path.join(self.dst_path, img_save_name)
                        save_lbl(self.dst_path, lbl, img_save_name, self.save_format)
                        cv2.imwrite(save_path, img)
            self.update_trigger.emit(n, total_num)
        self.finished_trigger.emit()
    
       
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
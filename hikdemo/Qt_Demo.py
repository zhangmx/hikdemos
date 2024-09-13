# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QVBoxLayout, QPushButton, QComboBox, QWidget
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
from ctypes import *


from MvCameraControl_class import *
from MvErrorDefine_const import *
from CameraParams_header import *

winfun_ctype = WINFUNCTYPE

stFrameInfo = POINTER(MV_FRAME_OUT_INFO_EX)
pData = POINTER(c_ubyte)
FrameInfoCallBack = winfun_ctype(None, pData, stFrameInfo, c_void_p)

class QtDemo(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUI()
        self.cam = MvCamera()
        self.deviceList = MV_CC_DEVICE_INFO_LIST()
        self.isOpen = False
        self.isGrabbing = False
        self.CALL_BACK_FUN = FrameInfoCallBack(self.image_callback)

    def initUI(self):
        self.setWindowTitle('Qt Camera Demo')
        self.setGeometry(100, 100, 800, 600)

        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout(self.centralWidget)

        self.comboDevices = QComboBox(self)
        self.layout.addWidget(self.comboDevices)

        self.btnDiscover = QPushButton('Discover Cameras', self)
        self.btnDiscover.clicked.connect(self.enum_devices)
        self.layout.addWidget(self.btnDiscover)

        self.btnStart = QPushButton('Start Camera', self)
        self.btnStart.clicked.connect(self.start_camera)
        self.layout.addWidget(self.btnStart)

        self.btnCapture = QPushButton('Capture Image', self)
        self.btnCapture.clicked.connect(self.capture_image)
        self.layout.addWidget(self.btnCapture)

        self.labelImage = QLabel(self)
        self.labelImage.setFixedSize(640, 480)  # 限制label的大小
        self.labelImage.setScaledContents(True)  # 允许缩放内容
        self.layout.addWidget(self.labelImage)

    def enum_devices(self):
        self.deviceList = MV_CC_DEVICE_INFO_LIST()
        n_layer_type = (MV_GIGE_DEVICE | MV_USB_DEVICE | MV_GENTL_CAMERALINK_DEVICE
                        | MV_GENTL_CXP_DEVICE | MV_GENTL_XOF_DEVICE)
        ret = self.cam.MV_CC_EnumDevices(n_layer_type, self.deviceList)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Enum devices fail! ret = :" + hex(ret), QMessageBox.Ok)
            return

        if self.deviceList.nDeviceNum == 0:
            QMessageBox.warning(self, "Info", "Find no device", QMessageBox.Ok)
            return

        self.comboDevices.clear()
        for i in range(0, self.deviceList.nDeviceNum):
            mvcc_dev_info = cast(self.deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            dev_name = ""
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE or mvcc_dev_info.nTLayerType == MV_GENTL_GIGE_DEVICE:
                dev_name = "".join([chr(c) for c in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName if c != 0])
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                dev_name = "".join([chr(c) for c in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName if c != 0])
            self.comboDevices.addItem(dev_name)

    def start_camera(self):
        if self.isOpen:
            QMessageBox.warning(self, "Error", 'Camera is Running!', QMessageBox.Ok)
            return

        nSelCamIndex = self.comboDevices.currentIndex()
        if nSelCamIndex < 0:
            QMessageBox.warning(self, "Error", 'Please select a camera!', QMessageBox.Ok)
            return

        stDeviceList = cast(self.deviceList.pDeviceInfo[nSelCamIndex], POINTER(MV_CC_DEVICE_INFO)).contents
        ret = self.cam.MV_CC_CreateHandle(stDeviceList)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Create handle fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return

        ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Open device fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return

        ret = self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_ON)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Set trigger mode fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return
        
        ret = self.cam.MV_CC_SetEnumValue("TriggerSource", MV_TRIGGER_SOURCE_SOFTWARE)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Set trigger mode fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return

        ret = self.cam.MV_CC_RegisterImageCallBackEx(self.CALL_BACK_FUN, None)
        if ret != 0:
            QMessageBox.warning(self, "Error", "Register image callback fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return

        ret = self.cam.MV_CC_StartGrabbing()
        if ret != 0:
            QMessageBox.warning(self, "Error", "Start grabbing fail! ret[0x%x]" % ret, QMessageBox.Ok)
            return

        self.isOpen = True
        self.isGrabbing = True

    def capture_image(self):
        if not self.isGrabbing:
            QMessageBox.warning(self, "Error", 'Camera is not grabbing!', QMessageBox.Ok)
            return

        ret = self.cam.MV_CC_SetCommandValue("TriggerSoftware")
        if ret != 0:
            QMessageBox.warning(self, "Error", "Trigger software fail! ret[0x%x]" % ret, QMessageBox.Ok)

    def image_callback(self, pData, pFrameInfo, pUser):
        stFrameInfo = cast(pFrameInfo, POINTER(MV_FRAME_OUT_INFO_EX)).contents
        if stFrameInfo:
            data = (c_ubyte * stFrameInfo.nFrameLen).from_address(addressof(pData.contents))
            image = QImage(data, stFrameInfo.nWidth, stFrameInfo.nHeight, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(self.labelImage.size(), aspectRatioMode=Qt.KeepAspectRatio)
            self.labelImage.setPixmap(scaled_pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = QtDemo()
    mainWindow.show()
    sys.exit(app.exec_())
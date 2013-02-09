#!/usr/bin/python

# SENTINEL
# A USB rocket launcher face-tracking solution
# For Linux and Windows
#
# Hardware requirements:
# - Dream Cheeky brand USB rocket launcher (tested with Thunder model, should also work with Storm)
# - small webcam attached to USB rocket launcher, in /dev/video0
#
# Software requirements (Linux):
# - Python 2.7, 32-bit
# - libusb (in Ubuntu/Debian, apt-get install libusb-dev)
# - PyUSB 1.0 (https://github.com/walac/pyusb)
# - NumPy (in Ubuntu/Debian, apt-get install python-numpy)
# - OpenCV Python bindings (in Ubuntu/Debian, apt-get install python-opencv)
# - PIL (in Ubuntu/Debian, apt-get install python-imaging)
# - streamer (in Ubuntu/Debian, apt-get install streamer)
#
# Software requirements (Windows):
# - Python 2.7, 32-bit
# - libusb (http://sourceforge.net/projects/libusb-win32/files/)
#     - After installing, plug in USB rocket launcher, launch <libusb path>\bin\inf-wizard.exe,
#       and create and run an INF driver file for the USB rocket launcher using the wizard
# - PyUSB 1.0 (https://github.com/walac/pyusb)
# - NumPy (http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy)
# - OpenCV Python bindings (http://sourceforge.net/projects/opencvlibrary/files/opencv-win/2.3.1/OpenCV-2.3.1-win-superpack.exe/download)
#     - After installing, copy the contents of <opencv path>\build\python\2.7 (it should contain cv.py and cv2.pyd)
#       to c:\Python27\Lib
# - PIL (http://www.lfd.uci.edu/~gohlke/pythonlibs/#pil)

import os
import sys
import time
import usb.core
import cv
from PIL import Image

class LauncherDriver():
   # this code mostly taken from https://github.com/nmilford/stormLauncher

   def __init__(self):
      self.dev = usb.core.find(idVendor=0x2123, idProduct=0x1010)
      if self.dev is None:
         raise ValueError('Launcher not found.')
      if os.name == 'posix' and self.dev.is_kernel_driver_active(0) is True:
         self.dev.detach_kernel_driver(0)
      self.dev.set_configuration()

   def turretUp(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x02,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretDown(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x01,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretLeft(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x04,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretRight(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x08,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretStop(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x20,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretFire(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x10,0x00,0x00,0x00,0x00,0x00,0x00])

class Turret():
   def __init__(self):
      self.launcher = LauncherDriver()

   # roughly centers the turret
   def center(self):
      self.launcher.turretLeft()
      time.sleep(5)
      self.launcher.turretRight()
      time.sleep(2)
      self.launcher.turretStop()

      self.launcher.turretUp()
      time.sleep(1)
      self.launcher.turretDown()
      time.sleep(0.25)
      self.launcher.turretStop()

   # adjusts the turret's position (units are fairly arbitary but work ok)
   def adjust(self, rightDist, downDist):
      rightSeconds = rightDist * 0.64
      downSeconds = downDist * 0.48

      if rightSeconds > 0:
         self.launcher.turretRight()
         time.sleep(rightSeconds)
         self.launcher.turretStop()
      elif rightSeconds < 0:
         self.launcher.turretLeft()
         time.sleep(- rightSeconds)
         self.launcher.turretStop()

      if downSeconds > 0:
         self.launcher.turretDown()
         time.sleep(downSeconds)
         self.launcher.turretStop()
      elif downSeconds < 0:
         self.launcher.turretUp()
         time.sleep(- downSeconds)
         self.launcher.turretStop()

class Camera():
   def __init__(self, cam_address):
      self.cam_address = cam_address

   def dispose(self):
      if os.name == 'posix':
         os.system("killall display")

   def capture(self, img_file):
      if os.name == 'posix':
         os.system("streamer -c " + self.cam_address + " -b 16 -o " + img_file)
         # generates 320x240 greyscale jpeg
      else:
         os.system("CommandCam")
         # generates 640x480 color bitmap

   def face_detect(self, img_file, haar_file, out_file):
      hc = cv.Load(haar_file)
      img = cv.LoadImage(img_file, 0)
      img_w, img_h = Image.open(img_file).size
      faces = cv.HaarDetectObjects(img, hc, cv.CreateMemStorage())
      xAdj, yAdj = 0, 0
      for (x,y,w,h),n in faces:
         cv.Rectangle(img, (x,y), (x+w,y+h), 255)
         xAdj = ((x + w/2) - img_w/2) / float(img_w)
         yAdj = ((y + w/2) - img_h/2) / float(img_h)
      cv.SaveImage(out_file, img)
      return xAdj, yAdj

   def display(self, img_file):
      os.system("killall display")
      img = Image.open(img_file)
      img.show()

if __name__ == '__main__':
   if os.name == 'posix' and not os.geteuid() == 0:
       sys.exit("Script must be run as root.")
   turret = Turret()
   camera = Camera('/dev/video0')

   turret.center()

   while True:
      try:
         img_file = 'capture.jpeg' if os.name == 'posix' else 'image.bmp'
         camera.capture(img_file)
         xAdj, yAdj = camera.face_detect(img_file, "haarcascade_frontalface_default.xml", 'capture_faces.jpg')
         if os.name == 'posix': camera.display('capture_faces.jpg')
         print xAdj, yAdj
         turret.adjust(xAdj, yAdj)
      except KeyboardInterrupt:
         camera.dispose()
         break

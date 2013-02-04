#!/usr/bin/python

# Hardware requirements:
# - Dream Cheeky brand USB rocket launcher (tested with Thunder model, should also work with Storm)
# - small webcam attached to USB rocket launcher, in /dev/video0
#
# Software requirements:
# - libusb (in Ubuntu/Debian, apt-get install libusb-dev)
# - PyUSB 1.0 (https://github.com/walac/pyusb)
# - OpenCV Python bindings (in Ubuntu/Debian, apt-get install python-opencv)
# - PIL
# - streamer (in Ubuntu/Debian, apt-get install streamer)

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
      if self.dev.is_kernel_driver_active(0) is True:
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

   def adjust(self, rightPixels, downPixels):
      rightSeconds = rightPixels / 500.
      downSeconds = downPixels / 500.

      print rightSeconds, downSeconds

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
   def dispose(self):
      os.system("killall display")

   def capture(self, img_file):
      os.system("streamer -c /dev/video0 -b 16 -o " + img_file)

   def face_detect(self, img_file, haar_file, out_file):
      hc = cv.Load(haar_file)
      img = cv.LoadImage(img_file, 0)
      img_w, img_h = 320, 240
      faces = cv.HaarDetectObjects(img, hc, cv.CreateMemStorage())
      result = 0, 0
      for (x,y,w,h),n in faces:
         cv.Rectangle(img, (x,y), (x+w,y+h), 255)
         result = ((x + w/2) - img_w/2, (y + w/2) - img_h/2)
      cv.SaveImage(out_file, img)
      return result

   def display(self, img_file):
      os.system("killall display")
      img = Image.open(img_file)
      img.show()

if __name__ == '__main__':
   if not os.geteuid() == 0:
       sys.exit("Script must be run as root.")
   turret = Turret()
   camera = Camera()

   while True:
      try:
         camera.capture('capture.jpeg')
         xAdj, yAdj = camera.face_detect('capture.jpeg', "haarcascade_frontalface_default.xml", 'capture_faces.jpg')
         camera.display('capture_faces.jpg')
         print xAdj, yAdj
         turret.adjust(xAdj, yAdj)
      except KeyboardInterrupt:
         camera.dispose()
         break

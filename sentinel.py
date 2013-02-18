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
import cv   #legacy OpenCV functions
import cv2
import subprocess
from PIL import Image
from optparse import OptionParser

# http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class LauncherDriver():
   # Low level launcher driver commands
   # this code mostly taken from https://github.com/nmilford/stormLauncher
   # with bits from https://github.com/codedance/Retaliation
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

   def ledOn(self):
      self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x01, 0x00,0x00,0x00,0x00,0x00,0x00])

   def ledOff(self):
      self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x00, 0x00,0x00,0x00,0x00,0x00,0x00])

class Turret():
   def __init__(self, opts):
      self.opts = opts
      self.launcher = LauncherDriver()

      # initial setup
      self.center()
      self.launcher.ledOff()

   # turn off turret properly
   def dispose(self):
      self.launcher.turretStop()
      turret.launcher.ledOff()

   # roughly centers the turret
   def center(self):
      self.launcher.turretLeft()
      time.sleep(4)
      self.launcher.turretRight()
      time.sleep(2)
      self.launcher.turretStop()

      self.launcher.turretUp()
      time.sleep(1)
      self.launcher.turretDown()
      time.sleep(0.25)
      self.launcher.turretStop()

   # adjusts the turret's position (units are fairly arbitary but work ok)
   def adjust(self, right_dist, down_dist):
      right_seconds = right_dist * 0.64
      down_seconds = down_dist * 0.48

      if right_seconds > 0:
         self.launcher.turretRight()
         time.sleep(right_seconds)
         self.launcher.turretStop()
      elif right_seconds < 0:
         self.launcher.turretLeft()
         time.sleep(- right_seconds)
         self.launcher.turretStop()

      if down_seconds > 0:
         self.launcher.turretDown()
         time.sleep(down_seconds)
         self.launcher.turretStop()
      elif down_seconds < 0:
         self.launcher.turretUp()
         time.sleep(- down_seconds)
         self.launcher.turretStop()

      # OpenCV takes pictures VERY quickly, so if we use it (Windows only), we must
      # add an artificial delay to reduce camera wobble and improve clarity
      if os.name != 'posix':
         time.sleep(.2)

   # turn on LED if face detected in range, and fire missiles if armed
   def ready_aim_fire(self):
      if face_detected and abs(x_adj)<.05 and abs(y_adj)<.05:
         turret.launcher.ledOn()
         if self.opts.armed:
            turret.launcher.turretFire()
      else:
         turret.launcher.ledOff()

class Camera():
   def __init__(self, opts):
      self.opts = opts
      # camera numbers start at 0 in Linux but 1 in Windows
      if os.name == 'posix':
         self.cam_number = opts.camera
      else:
         self.cam_number = int(opts.camera) + 1
      self.current_image_viewer = None # image viewer not yet launched

      if os.name != 'posix':
         self.webcam = cv2.VideoCapture(self.cam_number) #open a channel to our camera
         if(not self.webcam.isOpened()): #return error if unable to connect to hardware
            raise ValueError('Error connecting to specified camera')
         self.clear_buffer()

   # turn off camera properly
   def dispose(self):
      if os.name == 'posix':
         os.system("killall display")
      else:
         self.webcam.release()

   # grabs several images from buffer to attempt to clear out old images
   def clear_buffer(self):
      for i in range(self.opts.buffer_size):
         if not self.webcam.retrieve(channel=0):
            raise ValueError('no more images in buffer, mate')

   # captures a single frame - currently a platform-dependent implementation
   def capture(self):
      if os.name == 'posix':
         # on Linux, use streamer to generate a jpeg, then have OpenCV load it into self.current_frame

         img_file = 'capture.jpeg'
         os.system("streamer -q -c /dev/video" + self.cam_number + " -s " + self.opts.image_dimensions + " -b 16 -o " + img_file)
         self.current_frame = cv2.imread(img_file)
      else:
         # on Windows, use OpenCV to grab latest camera frame and store in self.current_frame

         if not self.webcam.grab():
            raise ValueError('frame grab failed')
         self.clear_buffer()

         retval, most_recent_frame = self.webcam.retrieve(channel=0)
         if not retval:
            raise ValueError('frame capture failed')
         self.current_frame = most_recent_frame

   def face_detect(self):
      def draw_reticule(img, x, y, width, height, color, style = "corners"):
         w, h = width, height
         if style == "corners":
            cv2.line(img, (x,y), (x+w/3,y), color, 2)
            cv2.line(img, (x+2*w/3,y), (x+w,y), color, 2)
            cv2.line(img, (x+w,y), (x+w,y+h/3), color, 2)
            cv2.line(img, (x+w,y+2*h/3), (x+w,y+h), color, 2)
            cv2.line(img, (x,y), (x,y+h/3), color, 2)
            cv2.line(img, (x,y+2*h/3), (x,y+h), color, 2)
            cv2.line(img, (x,y+h), (x+w/3,y+h), color, 2)
            cv2.line(img, (x+2*w/3,y+h), (x+w,y+h), color, 2)
         else:
            cv2.rectangle(img, (x,y), (x+w,y+h), color)

      img = self.current_frame
      img_w, img_h = map(int, self.opts.image_dimensions.split('x'))
      img = cv2.resize(img, (img_w, img_h))
      face_filter = cv2.CascadeClassifier(self.opts.haar_file)
      faces = face_filter.detectMultiScale(img, minNeighbors=4)
      faces = map(lambda f: f.tolist(), faces) # a bit silly, but works correctly regardless of
                                               # whether faces is an ndarray or empty tuple
      print 'faces detected: ' + str(faces)
      faces.sort(key=lambda face:face[2]*face[3]) # sort by size of face (we use the last face for computing x_adj, y_adj)

      x_adj, y_adj = 0, 0
      if len(faces) > 0:
         face_detected = True

         # draw a rectangle around all faces except last face
         for (x,y,w,h) in faces[:-1]:
            draw_reticule(img, x, y, w, h, (0 , 0, 60), "box")

         # get last face, draw target, and calculate distance from center
         (x,y,w,h) = faces[-1]
         draw_reticule(img, x, y, w, h, (0 , 0, 170), "corners")
         x_adj =  ((x + w/2) - img_w/2) / float(img_w)
         y_adj = ((y + h/2) - img_h/2) / float(img_h)
      else:
         face_detected = False
      cv2.imwrite(self.opts.processed_img_file, img)

      return face_detected, x_adj, y_adj

   def display(self):
      #display the image with faces indicated by a rectangle
      if os.name == 'posix':
         if self.current_image_viewer:
            os.system("killall display")
         img = Image.open(self.opts.processed_img_file)
         img.show()
         self.current_image_viewer = 'display'
      else:
         if not self.current_image_viewer:
            ImageViewer = 'rundll32 "C:\Program Files\Windows Photo Viewer\PhotoViewer.dll" ImageView_Fullscreen'
            self.current_image_viewer = subprocess.Popen('%s %s\%s' % (ImageViewer, os.getcwd(), self.opts.processed_img_file))

if __name__ == '__main__':
   if os.name == 'posix' and not os.geteuid() == 0:
       sys.exit("Script must be run as root.")

   # command-line options
   parser = OptionParser()
   parser.add_option("-a", "--arm", action="store_true", dest="armed", default=False,
                     help="enable the rocket launcher to fire")
   parser.add_option("-b", "--buffer", dest="buffer_size", default=2,
                     help="size of camera buffer. Default: 2", metavar="SIZE")
   parser.add_option("-c", "--camera", dest="camera", default='0',
                     help="specify the camera # to use. Default: 0", metavar="NUM")
   parser.add_option("-d", "--dimensions", dest="image_dimensions", default='320x240',
                     help="image dimensions (recommended: 320x240 or 640x480). Default: 320x240", metavar="WIDTHxHEIGHT")
   parser.add_option("--nd", "--no-display", action="store_true", dest="no_display", default=False,
                     help="do not display captured images")
   parser.add_option("-r", "--reset", action="store_true", dest="reset_only", default=False,
                     help="reset the camera and exit")
   parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                     help="output timing information")
   opts, args = parser.parse_args()
   print opts

   # additional options
   opts = AttributeDict(vars(opts)) # converting opts to an AttributeDict so we can add extra options
   opts.haar_file = 'haarcascade_frontalface_default.xml'
   opts.processed_img_file = 'capture_faces.jpg'

   turret = Turret(opts)
   camera = Camera(opts)

   if not opts.reset_only:
      while True:
         try:
            start_time = time.time()

            camera.capture()
            capture_time = time.time()

            face_detected, x_adj, y_adj = camera.face_detect()
            detection_time = time.time()

            if not opts.no_display:
               camera.display()

            if face_detected:
               print "adjusting turret: x=" + str(x_adj) + ", y=" + str(y_adj)
               turret.adjust(x_adj, y_adj)
            movement_time = time.time()

            if opts.verbose:
               print "capture time: " + str(capture_time - start_time)
               print "detection time: " + str(detection_time - capture_time)
               print "movement time: " + str(movement_time - detection_time)

            turret.ready_aim_fire()
         except KeyboardInterrupt:
            turret.dispose()
            camera.dispose()
            break

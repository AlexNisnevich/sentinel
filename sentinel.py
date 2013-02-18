#!/usr/bin/python

# SENTINEL
# A USB rocket launcher face-tracking solution
# For Linux and Windows
#
# Installation: see README.md
#
# Usage: sentinel.py [options]
#
# Options:
#   -h, --help            show this help message and exit
#   -a, --arm             enable the rocket launcher to fire
#   -b SIZE, --buffer=SIZE
#                         size of camera buffer. Default: 2
#   -c NUM, --camera=NUM  specify the camera # to use. Default: 0
#   -d WIDTHxHEIGHT, --dimensions=WIDTHxHEIGHT
#                         image dimensions (recommended: 320x240 or 640x480).
#                         Default: 320x240
#   --nd, --no-display    do not display captured images
#   -r, --reset           reset the camera and exit
#   -v, --verbose         output timing information

import os
import sys
import time
import usb.core
import cv
import cv2
import subprocess
from optparse import OptionParser

# globals
FNULL = open(os.devnull, 'w')

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
      self.missiles_remaining = 4
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
            time.sleep(3) # roughly how long it takes to fire
            self.missiles_remaining -= 1
            print 'Missile fired! Estimated ' + str(self.missiles_remaining) + ' missiles remaining.'
            if self.missiles_remaining < 1:
               raw_input("Ammunition depleted. Awaiting order to continue assault. [ENTER]")
               self.missiles_remaining = 4
         else:
            print 'Turret trained but not firing because of the --disarm directive.'
      else:
         turret.launcher.ledOff()

class Camera():
   def __init__(self, opts):
      self.opts = opts
      self.current_image_viewer = None # image viewer not yet launched

      if os.name != 'posix':
         self.webcam = cv2.VideoCapture(int(self.opts.camera)) #open a channel to our camera
         if(not self.webcam.isOpened()): #return error if unable to connect to hardware
            raise ValueError('Error connecting to specified camera')
         self.clear_buffer()

   # turn off camera properly
   def dispose(self):
      if os.name == 'posix':
         if self.current_image_viewer:
            subprocess.call(['killall', self.current_image_viewer])
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
         subprocess.call("streamer -q -c /dev/video" + self.opts.camera + " -s "
               + self.opts.image_dimensions + " -b 16 -o " + img_file, stdout=FNULL, shell=True)
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

      img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) #convert image to greyscale
      img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) #convert back to color so we can put color in our final image

      faces = map(lambda f: f.tolist(), faces) # a bit silly, but works correctly regardless of
                                               # whether faces is an ndarray or empty tuple
      if self.opts.verbose:
         print 'faces detected: ' + str(faces)
      faces.sort(key=lambda face:face[2]*face[3]) # sort by size of face (we use the last face for computing x_adj, y_adj)
      y_offset = .05
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
         y_adj = ((y + h/2) - img_h/2) / float(img_h) - y_offset
      else:
         face_detected = False
      cv2.imwrite(self.opts.processed_img_file, img)

      return face_detected, x_adj, y_adj

   def display(self):
      # display the OpenCV-processed images
      if os.name == 'posix':
         if self.current_image_viewer:
            subprocess.call(['killall', self.current_image_viewer])
         subprocess.call("display " + self.opts.processed_img_file + ' &', stdout=FNULL, stderr=FNULL, shell=True)
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
   parser.add_option("-d", "--disarm", action="store_false", dest="armed", default=True,
                     help="enable the rocket launcher to fire")
   parser.add_option("-b", "--buffer", dest="buffer_size", default=2,
                     help="size of camera buffer. Default: 2", metavar="SIZE")
   parser.add_option("-c", "--camera", dest="camera", default='0',
                     help="specify the camera # to use. Default: 0", metavar="NUM")
   parser.add_option("-s", "--size", dest="image_dimensions", default='320x240',
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
               if opts.verbose:
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

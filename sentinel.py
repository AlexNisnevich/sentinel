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
#   -l ID, --launcher=ID  specify VendorID of the missile launcher to use.
#                         Default: '2123' (dreamcheeky thunder)
#   -d, --disarm          track faces but do not fire any missiles
#   -r, --reset           reset the turret position and exit
#   --nd, --no-display    do not display captured images
#   -c NUM, --camera=NUM  specify the camera # to use. Default: 0
#   -s WIDTHxHEIGHT, --size=WIDTHxHEIGHT
#                         image dimensions (recommended: 320x240 or 640x480).
#                         Default: 320x240
#   -v, --verbose         detailed output, including timing information

import os
import sys
import time
import usb.core
import cv2
import subprocess
import shutil
import math
import threading
from optparse import OptionParser

# globals
FNULL = open(os.devnull, 'w')


# http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

# Launcher commands for USB Missile Launcher (VendorID:0x1130 ProductID:0x0202 Tenx Technology, Inc.)
class Launcher1130():
    # Commands and control messages are derived from
    # http://sourceforge.net/projects/usbmissile/ and http://code.google.com/p/pymissile/

    # 7 Bytes of Zeros to fill 64 Bit packet (8 Bit for direction/action + 56 Bit of Zeros to fill packet)
    cmdFill = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    # Low level launcher driver commands
    # this code mostly taken from https://github.com/nmilford/stormLauncher
    # with bits from https://github.com/codedance/Retaliation
    def __init__(self):
        # HID detach for Linux systems...not tested with 0x1130 product

        if self.dev is None:
                raise ValueError('Missile launcher not found.')
        if sys.platform == "linux2":
            try:
                if self.dev.is_kernel_driver_active(1) is True:
                    self.dev.detach_kernel_driver(1)
                else:
                    self.dev.detach_kernel_driver(0)
            except Exception, e:
                pass

        self.dev.set_configuration()

        self.missile_capacity = 3
        self.vert_speed = 0.48
        self.horiz_speed = 0.64

        #directional constants
        self.LEFT   =   [0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x08, 0x08]
        self.RIGHT  =   [0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x08, 0x08]
        self.UP     =   [0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x08, 0x08]
        self.DOWN   =   [0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x08, 0x08]
        self.FIRE   =   [0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x08, 0x08]
        self.STOP   =   [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x08]

    def turretLeft(self):
        cmd = self.LEFT + self.cmdFill
        self.turretMove(cmd)

    def turretRight(self):
        cmd = self.RIGHT + self.cmdFill
        self.turretMove(cmd)

    def turretUp(self):
        cmd = self.UP + self.cmdFill
        self.turretMove(cmd)

    def turretDown(self):
        cmd = self.DOWN + self.cmdFill
        self.turretMove(cmd)

    def turretDirection(self, directionCommand):
        md = directionCommand + self.cmdFill
        self.turretMove(cmd)

    def turretFire(self):
        cmd = self.FIRE + self.cmdFill
        self.turretMove(cmd)

    def turretStop(self):
        cmd = self.STOP + self.cmdFill
        self.turretMove(cmd)

    def ledOn(self):
        # cannot turn on LED. Device has no LED.
        pass

    def ledOff(self):
        # cannot turn off LED. Device has no LED.
        pass

    # Missile launcher requires two init-packets before the actual command can be sent.
    # The init-packets consist of 8 Bit payload, the actual command is 64 Bit payload
    def turretMove(self, cmd):
        # Two init-packets plus actual command
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x01, [ord('U'), ord('S'), ord('B'), ord('C'), 0, 0, 4, 0])
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x01, [ord('U'), ord('S'), ord('B'), ord('C'), 0, 64, 2, 0])
        self.dev.ctrl_transfer(0x21, 0x09, 0x2, 0x00, cmd)

        # roughly centers the turret
    def center(self):
        print 'Centering camera ...'
        self.turretLeft()
        time.sleep(3.5)
        self.turretLeft()
        time.sleep(3.5)
        self.turretRight()
        time.sleep(3)
        self.turretRight()
        time.sleep(2)
        self.turretStop()
        self.turretUp()
        time.sleep(3)
        self.turretDown()
        time.sleep(1.5)
        self.turretStop()

# Launcher commands for DreamCheeky Thunder (VendorID:0x2123 ProductID:0x1010)
class Launcher2123():
    # Low level launcher driver commands
    # this code mostly taken from https://github.com/nmilford/stormLauncher
    # with bits from https://github.com/codedance/Retaliation
    def __init__(self):
        self.dev = usb.core.find(idVendor=0x2123, idProduct=0x1010)

        # HID detach for Linux systems...tested with 0x2123 product

        if self.dev is None:
            raise ValueError('Missile launcher not found.')
        if sys.platform == "linux2":
            try:
                if self.dev.is_kernel_driver_active(1) is True:
                    self.dev.detach_kernel_driver(1)
                else:
                    self.dev.detach_kernel_driver(0)
            except Exception, e:
                pass

        self.missile_capacity = 4
        self.vert_speed = 0.48
        self.horiz_speed = 1.2

        #define directional constants        
        self.DOWN = 0x01
        self.UP = 0x02
        self.LEFT = 0x04
        self.RIGHT = 0x08



    def turretUp(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretDown(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretLeft(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretRight(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretDirection(self,direction):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, direction, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretStop(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def turretFire(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x02, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def ledOn(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def ledOff(self):
        self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    # roughly centers the turret
    def center(self):
        print 'Centering camera ...'

        self.turretLeft()
        time.sleep(4)
        self.turretRight()
        time.sleep(2)
        self.turretStop()

        self.turretUp()
        time.sleep(1)
        self.turretDown()
        time.sleep(0.25)
        self.turretStop()

class Turret():
    def __init__(self, opts):
        self.opts = opts

        # Choose correct Launcher
        if opts.launcherID == "1130":
            self.launcher = Launcher1130();
        else:
            self.launcher = Launcher2123();

        self.missiles_remaining = self.launcher.missile_capacity

        # initial setup
        self.center()
        self.launcher.ledOff()
        self.cooldown_time = 3
        self.killcam_count = 0

    # turn off turret properly
    def dispose(self):
        self.launcher.turretStop()
        turret.launcher.ledOff()

    # roughly centers the turret
    def center(self):
        self.launcher.center()

    # adjusts the turret's position (units are fairly arbitary but work ok)
    def adjust(self, right_dist, down_dist):
        right_seconds = right_dist * self.launcher.horiz_speed
        down_seconds = down_dist * self.launcher.vert_speed

        directionRight=0
        directionDown=0
        if right_seconds > 0:
            directionRight = self.launcher.RIGHT
        elif right_seconds < 0:
            directionRight = self.launcher.LEFT

        if down_seconds > 0:
            directionDown = self.launcher.DOWN
        elif down_seconds < 0:
            directionDown = self.launcher.UP

        self.launcher.turretDirection(directionDown | directionRight)

        if (abs(right_seconds)>abs(down_seconds)):
            time.sleep(abs(down_seconds))
            self.launcher.turretDirection(directionRight)
            time.sleep(abs(right_seconds-down_seconds))            
        else:
            time.sleep(abs(right_seconds))
            self.launcher.turretDirection(directionDown)
            time.sleep(abs(down_seconds-right_seconds))          
        
        self.launcher.turretStop()

        # OpenCV takes pictures VERY quickly, so if we use it (Windows and OS X), we must
        # add an artificial delay to reduce camera wobble and improve clarity
        time.sleep(.2)

    #stores images of the targets within the killcam folder
    def killcam(self, camera):
        # create killcam dir if none exists, then find first unused filename
        if not os.path.exists("killcam"):
            os.makedirs("killcam")
        filename_locked_on = os.path.join("killcam", "lockedon" + str(self.killcam_count) + ".jpg")
        while os.path.exists(filename_locked_on):
            self.killcam_count += 1
            filename_locked_on = os.path.join("killcam", "lockedon" + str(self.killcam_count) + ".jpg")

        # save the image with the target being locked on

        cv2.imwrite(filename_locked_on, camera.frame_mod)

        # wait a little bit to attempt to catch the target's reaction.
        time.sleep(1)  # tweak this value for most hilarious action shots
        camera.new_frame_available = False #force camera to obtain image after movement has completed

        # take another picture of the target while it is being fired upon
        filename_firing = os.path.join("killcam", "firing" + str(self.killcam_count) + ".jpg")
        camera.face_detect(filename=filename_firing) 
        if not opts.no_display:
            camera.display()

        self.killcam_count += 1

    # compensate vertically for distance to target
    def projectile_compensation(self, target_y_size):
        if target_y_size != 0:
            # objects further away will need a greater adjustment to hit target
            adjust_amount = 0.1 * math.log(target_y_size)
        else:
            # log 0 will throw an error, so handle this case even though unlikely to occur
            adjust_amount = 0

        # tilt the turret up to try to increase range
        self.adjust(0, adjust_amount)
        if opts.verbose:
            print "size of target: %.6f" % target_y_size
            print "compensation amount: %.6f" % adjust_amount

    # turn on LED if face detected in range, and fire missiles if armed
    def ready_aim_fire(self, x_adj, y_adj, target_y_size, camera=None):
        fired = False
        if face_detected and abs(x_adj) < .05 and abs(y_adj) < .05:
            turret.launcher.ledOn()  # LED will turn on when target is locked
            if self.opts.armed:
                # aim a little higher if our target is in the distance
                self.projectile_compensation(target_y_size)

                turret.launcher.turretFire()
                self.missiles_remaining -= 1
                fired = True

                if camera:
                    self.killcam(camera)  # save a picture of the target

                time.sleep(3)  # disable turret for approximate time required to fire

                print 'Missile fired! Estimated ' + str(self.missiles_remaining) + ' missiles remaining.'

                if self.missiles_remaining < 1:
                    raw_input("Ammunition depleted. Awaiting order to continue assault. [ENTER]")
                    self.missiles_remaining = 4
            else:
                print 'Turret trained but not firing because of the --disarm directive.'
        else:
            turret.launcher.ledOff()
        return fired


class Camera():
    def __init__(self, opts):
        self.opts = opts
        self.current_image_viewer = None  # image viewer not yet launched

        self.webcam = cv2.VideoCapture(int(self.opts.camera))  # open a channel to our camera
        if(not self.webcam.isOpened()):  # return error if unable to connect to hardware
            raise ValueError('Error connecting to specified camera')

        #if supported by camera set image width and height to desired values
        img_w, img_h = map(int, self.opts.image_dimensions.split('x'))
        self.resolution_set = self.webcam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,img_w)
        self.resolution_set =  self.resolution_set  and self.webcam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,img_h)


        # initialize classifier with training set of faces
        self.face_filter = cv2.CascadeClassifier(self.opts.haar_file)

        # create a separate thread to grab frames from camera.  This prevents a frame buffer from filling up with old images
        self.camThread = threading.Thread(target=self.grab_frames)
        self.camThread.daemon = True
        self.currentFrameLock = threading.Lock()
        self.new_frame_available = False
        self.camThread.start()

    # turn off camera properly
    def dispose(self):
        if sys.platform == 'linux2' or sys.platform == 'darwin':
            if self.current_image_viewer:
                subprocess.call(['killall', self.current_image_viewer], stdout=FNULL, stderr=FNULL)
        else:
            self.webcam.release()


    # runs to grab latest frames from camera
    def grab_frames(self):
            while(1): # loop until process is shut down
                if not self.webcam.grab():
                    raise ValueError('frame grab failed')
                time.sleep(.015)
                retval, most_recent_frame = self.webcam.retrieve(channel=0)
                if not retval:
                    raise ValueError('frame capture failed')
                self.currentFrameLock.acquire()
                self.current_frame = most_recent_frame
                self.new_frame_available = True
                self.currentFrameLock.release()
                time.sleep(.015)


    # runs facial recognition on our previously captured image and returns
    # (x,y)-distance between target and center (as a fraction of image dimensions)
    def face_detect(self, filename=None):
        def draw_reticule(img, x, y, width, height, color, style="corners"):
            w, h = width, height
            if style == "corners":
                cv2.line(img, (x, y), (x+w/3, y), color, 2)
                cv2.line(img, (x+2*w/3, y), (x+w, y), color, 2)
                cv2.line(img, (x+w, y), (x+w, y+h/3), color, 2)
                cv2.line(img, (x+w, y+2*h/3), (x+w, y+h), color, 2)
                cv2.line(img, (x, y), (x, y+h/3), color, 2)
                cv2.line(img, (x, y+2*h/3), (x, y+h), color, 2)
                cv2.line(img, (x, y+h), (x+w/3, y+h), color, 2)
                cv2.line(img, (x+2*w/3, y+h), (x+w, y+h), color, 2)
            else:
                cv2.rectangle(img, (x, y), (x+w, y+h), color)

        # load image, then resize it to specified size
        while(not self.new_frame_available):
            time.sleep(.001)
        self.currentFrameLock.acquire()
        img = self.current_frame.copy()
        self.new_frame_available = False
        self.currentFrameLock.release()

        img_w, img_h = map(int, self.opts.image_dimensions.split('x'))
        if(not self.resolution_set):
            img = cv2.resize(img, (img_w, img_h))


        #convert to grayscale since haar operates on grayscale images anyways
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # detect faces (might want to make the minNeighbors threshold adjustable)
        faces = self.face_filter.detectMultiScale(img, minNeighbors=4)

        # convert back from grayscale, so that we can draw red targets over a grayscale
        # photo, for an especially ominous effect
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # a bit silly, but works correctly regardless of whether faces is an ndarray or empty tuple
        faces = map(lambda f: f.tolist(), faces)

        if self.opts.verbose:
            print 'faces detected: ' + str(faces)

        # sort by size of face (we use the last face for computing x_adj, y_adj)
        faces.sort(key=lambda face: face[2]*face[3])

        x_adj, y_adj = (0, 0)  # (x,y)-distance from center, as a fraction of image dimensions
        face_y_size = 0  # height of the detected face, used to gauge distance to target
        if len(faces) > 0:
            face_detected = True

            # draw a rectangle around all faces except last face
            for (x, y, w, h) in faces[:-1]:
                draw_reticule(img, x, y, w, h, (0, 0, 60), "box")

            # get last face, draw target, and calculate distance from center
            (x, y, w, h) = faces[-1]
            draw_reticule(img, x, y, w, h, (0, 0, 170), "corners")
            x_adj = ((x + w/2) - img_w/2) / float(img_w)
            y_adj = ((y + h/2) - img_h/2) / float(img_h)
            face_y_size = h / float(img_h)
        else:
            face_detected = False


        #store modified image as class variable so that display() can access it
        self.frame_mod = img
        if filename:    #save to file if desired
            cv2.imwrite(filename, img)

        return face_detected, x_adj, y_adj, face_y_size

    # display the OpenCV-processed images
    def display(self):
            #not tested on Mac, but the openCV libraries should be fairly cross-platform
            cv2.imshow("cameraFeed", self.frame_mod)

            # delay of 2 ms for refreshing screen (time.sleep() doesn't work)
            cv2.waitKey(2)

if __name__ == '__main__':
    if (sys.platform == 'linux2' or sys.platform == 'darwin') and not os.geteuid() == 0:
        sys.exit("Script must be run as root.")

    # command-line options
    parser = OptionParser()
    parser.add_option("-l", "--launcher", dest="launcherID", default="2123",
                      help="specify VendorID of the missile launcher to use. Default: '2123' (dreamcheeky thunder)",
                      metavar="LAUNCHER")
    parser.add_option("-d", "--disarm", action="store_false", dest="armed", default=True,
                      help="track faces but do not fire any missiles")
    parser.add_option("-r", "--reset", action="store_true", dest="reset_only", default=False,
                      help="reset the turret position and exit")
    parser.add_option("--nd", "--no-display", action="store_true", dest="no_display", default=False,
                      help="do not display captured images")
    parser.add_option("-c", "--camera", dest="camera", default='0',
                      help="specify the camera # to use. Default: 0", metavar="NUM")
    parser.add_option("-s", "--size", dest="image_dimensions", default='320x240',
                      help="image dimensions (recommended: 320x240 or 640x480). Default: 320x240",
                      metavar="WIDTHxHEIGHT")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="detailed output, including timing information")
    opts, args = parser.parse_args()
    print opts

    # additional options
    opts = AttributeDict(vars(opts))  # converting opts to an AttributeDict so we can add extra options
    opts.haar_file = 'haarcascade_frontalface_default.xml'

    turret = Turret(opts)
    camera = Camera(opts)


    while (not camera.new_frame_available):
        time.sleep(.001)   #wait for first frame to be captured
    if not opts.reset_only:
        while True:
            try:
                start_time = time.time()
                face_detected, x_adj, y_adj, face_y_size = camera.face_detect()
                detection_time = time.time()

                if not opts.no_display:
                    camera.display()

                if face_detected:
                    if opts.verbose:
                        print "adjusting turret: x=" + str(x_adj) + ", y=" + str(y_adj)
                    turret.adjust(x_adj, y_adj)
                movement_time = time.time()
                camera.new_frame_available = False #force camera to obtain next image after movement has completed

                if opts.verbose:
                    print "total time: " + str(movement_time - start_time)
                    print "detection time: " + str(detection_time - start_time)
                    print "movement time: " + str(movement_time - detection_time)

                turret.ready_aim_fire(x_adj, y_adj, face_y_size, camera) 

            except KeyboardInterrupt:
                turret.dispose()
                camera.dispose()
                break

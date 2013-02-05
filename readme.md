# Sentinel

**Sentinel** is a USB rocket launcher face-tracking solution for Linux and Windows. It will attempt to track faces and continually point the rocket launcher at the clearest face.

Impress your friends! Intimidate your enemies!

## Hardware requirements
- Dream Cheeky brand USB rocket launcher (tested with Thunder model, should also work with Storm)
- small webcam attached to USB rocket launcher, in /dev/video0 (tested with Logitech C270)

## Software requirements (Linux)
- **Python** 2.7, 32-bit
- **libusb** (in Ubuntu/Debian, `apt-get install libusb-dev`)
- **PyUSB** 1.0 (https://github.com/walac/pyusb)
- **NumPy** (in Ubuntu/Debian, `apt-get install python-numpy`)
- **OpenCV** Python bindings (in Ubuntu/Debian, `apt-get install python-opencv`)
- **PIL** (in Ubuntu/Debian, `apt-get install python-imaging`)
- **streamer** (in Ubuntu/Debian, `apt-get install streamer`)

After installing all of the software requirements, you can run Sentinel:
```
> sudo ./sentinel.py
```

## Software requirements (Windows)
- **Python** 2.7, 32-bit
- **libusb** (http://sourceforge.net/projects/libusb-win32/files/)
   - After installing, plug in USB rocket launcher, launch *[libusb path]\bin\inf-wizard.exe*, and create and run an INF driver file for the USB rocket launcher using the wizard
- **PyUSB** 1.0 (https://github.com/walac/pyusb)
- **NumPy** (http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy)
- **OpenCV** Python bindings (http://sourceforge.net/projects/opencvlibrary/files/opencv-win/2.3.1/OpenCV-2.3.1-win-superpack.exe/download)
   - After installing, copy the contents of *[opencv path]\build\python\2.7* (it should contain *cv.py* and *cv2.pyd*) to *c:\Python27\Lib*
- **PIL** (http://www.lfd.uci.edu/~gohlke/pythonlibs/#pil)

After installing all of the software requirements, you can run Sentinel from Python IDLE or from the command line:
```
> C:\Python27\python sentinel.py
```

## Acknowledgements
For Windows photo capture, Sentinel uses the CommandCam utility by Ted Burke, the source code for which can be found at https://github.com/tedburke/CommandCam

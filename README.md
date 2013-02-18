# Sentinel

**Sentinel** is a USB rocket launcher face-tracking solution for Linux and Windows. It will attempt to track faces and continually point the rocket launcher at the clearest face.

Impress your friends! Intimidate your enemies!

## Hardware requirements
- **[Dream Cheeky brand USB rocket launcher](http://www.amazon.com/Dream-Cheeky-908-Electronic-Reference/dp/B004SAYO46)** (tested with the Thunder model, should also work with the Storm model)
- small **webcam** attached to USB rocket launcher (tested with Logitech C270)

## Software requirements (Linux)
If you're on Ubuntu 12.04+ or Debian (tested with Linux Mint Debian), you can simply run the included installation script:
```
> sudo install/install_on_ubuntu_or_debian.sh
```

Otherwise (or if the script doesn't work for you), install the following dependencies:

- **Python** 2.7, 32-bit
- **libusb** 1.0 (in Ubuntu/Debian, `apt-get install libusb-dev`)
- **PyUSB** 1.0 (https://github.com/walac/pyusb)
- **OpenCV** 2.3+ with Python bindings
	- In Ubuntu 12.04+ or latest Debian, `apt-get install python-opencv` will install the correct version
	- In older versions of Ubuntu, you can follow [these instructions](http://jayrambhia.wordpress.com/2012/06/20/install-opencv-2-4-in-ubuntu-12-04-precise-pangolin/) or use [this bash script](https://github.com/jayrambhia/Install-OpenCV/blob/master/Ubuntu/2.4/opencv2_4_3.sh) (tested with 11.10)
	- In ArchLinux, `pacman -S python2-numpy` then `pacman -S opencv 2.4.0_a-4`
- **streamer** (in Ubuntu/Debian, `apt-get install streamer`)

After installing all of the software requirements, you can run Sentinel:
```
> sudo ./sentinel.py
```

## Software requirements (Windows)
- **Python** 2.7, 32-bit
- **libusb-win32** (http://sourceforge.net/projects/libusb-win32/files/)
   - After installing, plug in USB rocket launcher, launch *[libusb path]\bin\inf-wizard.exe*, and create and run an INF driver file for the USB rocket launcher using the wizard
- **PyUSB** 1.0 (https://github.com/walac/pyusb)
- **NumPy** (http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy)
- **OpenCV** Python bindings (http://sourceforge.net/projects/opencvlibrary/files/opencv-win/2.3.1/OpenCV-2.3.1-win-superpack.exe/download)
   - After installing, copy the contents of *[opencv path]\build\python\2.7* (it should contain *cv.py* and *cv2.pyd*) to *C:\Python27\Lib\site-packages*

After installing all of the software requirements, you can run Sentinel from Python IDLE or from the command line:
```
> C:\Python27\python sentinel.py
```

# Installs all dependencies for Sentinel on Ubuntu 12.04+ or Debian (tested on Linux Mint Debian)
#
# If you're running Ubuntu 11.10 or earlier, the version of OpenCV installed by the python-opencv package
# will be too old. You can follow the follow the instructions at
# 	http://jayrambhia.wordpress.com/2012/06/20/install-opencv-2-4-in-ubuntu-12-04-precise-pangolin/
# or run the following script:
# 	https://github.com/jayrambhia/Install-OpenCV/blob/master/Ubuntu/2.4/opencv2_4_3.sh
# to get OpenCV working correctly after running this script.
# (I've tested the opencv2_4_3.sh script with Ubuntu 11.10. Your mileage may vary for even older versions.)
#
# Run as superuser: (sudo ./install_on_ubuntu_or_debian.sh)

apt-get install python-opencv libusb-dev streamer
git clone git://github.com/walac/pyusb.git
pushd pyusb
python setup.py install
popd
rm -rf pyusb


path_append ()  { path_remove $1; export PATH="$PATH:$1"; }
path_prepend () { path_remove $1; export PATH="$1:$PATH"; }
path_remove ()  { export PATH=`echo -n $PATH | awk -v RS=: -v ORS=: '$0 != "'$1'"' | sed 's/:$//'`; }

# install python
brew link gdbm
brew install python

# rearrange PATH to point to homebrewed python first
path_remove('usr/local/bin')
path_prepend('usr/local/bin')

# install libraries
brew install libusb
pip install numpy
brew install opencv

# install pyusb from git
git clone git://github.com/walac/pyusb.git
pushd pyusb
python setup.py install
popd
rm -rf pyusb

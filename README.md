Platter
=======

A simple single-file server with a GUI. It listens on port 10700.

## Screenshot

![Screenshot](https://raw.github.com/Stebalien/platter/screenshots/screenshot.png)

## Features

(i.e. why not just use woof)

* Displays the download progress of connected clients.
* Displays a QRCode
* Bundles multiple files/directories into Zip archives.
* Individual files/archives may be removed at runtime.
* Files/archives may be added at runtime.
* Single instance

## TODO

* Alternative interfaces (CLI, GTK?)
* Daemon mode (systemd)? We already listen for new files on dbus.
* QT Thread safety. Unfortunately, PyQT doesn't work with python threads (well,
  it works but is very buggy).
* Download from the web?
* Drag and drop data?

## Dependencies

* python-qrcode
* python-pyqt5
* qt5-svg
* python-pillow
* python-netifaces

### Optional (to autodetect icon theme)

* python-gobject
* gtk3


## License

This project is under the [GPLv3](http://www.gnu.org/licenses/gpl.html).



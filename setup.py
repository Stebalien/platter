##
#    This file is part of Platter.
#
#    Platter is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Platter is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Platter.  If not, see <http://www.gnu.org/licenses/>.
##

from setuptools import setup, find_packages
setup(
    name = "platter",
    version = "1.2",
    packages = find_packages(),
    install_requires = ["Pillow>=2.3.0", "qrcode", "netifaces"],
    author = "Steven Allen",
    author_email = "steven@stebalien.com",
    description = "A single file server.",
    license = "GPLV3",
    url = "http://stebalien.com",
    entry_points = {
        'gui_scripts': ['platter = platter.qt:main']
    }
)

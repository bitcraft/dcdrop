"""
DCDROP Decode  -  Translate Dreamcast VMU saves
Copyright (C) 2008-2016, Leif Theden

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import print_function

from functools import partial
import base64
import re

from construct import String, Struct, ULInt16, ULInt64, ULInt8

# we are dealing with a small amount of data, a regex works fine.
# tested with planetweb 2.0 browser
vmu_re = re.compile(
    'filename=(?P<filename>.*)&fs=(?P<file_size>\d*)&bl=(?P<blocks>\d*).*&tm=(?P<timestamp>\d*)\r\n\r\n(?P<data>.*)',
    re.DOTALL)

time_re = re.compile('(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d)')

# time is used internally
time_format = Struct(
    'time',
    ULInt64('year'),        # year
    ULInt16('month'),       # month (1-12)
    ULInt16('day'),         # day (1-31)
    ULInt16('hour'),        # hour (0-23)
    ULInt16('minute'),      # minute (0-59)
    ULInt16('second'),      # second (0-59)
    ULInt8('weekday'))      # weekday (0=sunday, 6=saturday)

# VMI file format
# http://mc.pp.se/dc/vms/vmi.html
VMUString = partial(String, encoding='ISO-8859-1', padchar='.', paddir='right')
vmi_format = Struct(
    "vmi",
    ULInt64('checksum'),
    VMUString('description', 32),
    VMUString('copyright', 32),
    time_format,                    # creation time
    ULInt16('version'),             # VMI file version (set to 0)
    ULInt16('file_number'),         # file number (set to 1)
    VMUString('resource_name', 8),  # .VMS resource name (without .VMS)
    VMUString('filename', 12),      # filename on VMS
    # BitStruct('file_mode', BitField('unused', 16), Flag('game'), Flag('protected')),
    ULInt16('unused'),
    ULInt16('unknown'),             # unknown (set to 0)
    ULInt64('file_size'))           # file size in bytes

# VMS file header
# http://mc.pp.se/dc/vms/fileheader.html
# INCOMPLETE
vms_header = Struct(
    'vms',
    VMUString('description1', 16),
    VMUString('description2', 32),
    VMUString('creator', 16),
    ULInt16('num_icons'),
    ULInt16('icon_speed'),
    ULInt16('type'),
    ULInt16('checksum'),
    ULInt64('size'),
    String('padding', 0),
    String('palette', 16))


def generate_translate_table():
    """ Generate translate table for decoding data from the PlanetWeb browser to VMU

    :rtype: str
    """
    import string

    org64 = '=+/0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    vmu64 = '=y/270PlgMerTAXsZIx5+UpoDkFCLcwQJ419WEBihNGSbaYOqzfKH6ndmujt83vVR'

    # 2: string
    translate_table = string.maketrans(org64, vmu64)

    # 3: dict
    # translate_table = org64.maketrans(org64, vmu64)

    return translate_table


class FilenameGenerator(object):
    """
    This class accepts VMU and attempts to generate a useful filename for it

    Currently the following games are supported:
        * Street Fighter III: 3rd Strike
    """

    def xlate(self, data):
        desc = data[:16]
        desc = desc.replace("vs", "v")
        series = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        save_name = None
        for char in series:
            save_name = desc[7:14] + char

        return save_name

    @staticmethod
    def is_this(desc):
        return desc[:6] == "REPLAY"


class PlanetWebTranslator(object):
    """
    This class will read files uploaded from the PlanetWeb browser and save
    them as VMI files
    """

    def __init__(self):
        pass

    def pw_to_vmx(self, data):
        """ Given data returned from PlanetWeb, return data for VMI/VMS saves

        :type data: bytes
        """
        pw_data = self.is_valid_pw_save(data)
        if not pw_data:
            raise Exception

        game_data = base64.b64decode(pw_data['data'])

        vmi = {
            'checksum': self.checksum(pw_data['filename']),
            'description': "desc".ljust(32, ' '),
            'copyright': 'public domain'.ljust(32, ' '),
            'version': 0,
            'file_number': 1,
            'resource_name': 'fuck'.ljust(8, ' '),
            'filename': 'fuck'.ljust(12, ' '),
            'unused': 0,
            'file_size': pw_data['file_size']}

        vmi.update(self.strip_time(pw_data['timestamp']))

        return vmi_format.build(vmi)

    @staticmethod
    def strip_time(timestamp):
        """ Return time info from a timestamp

        :type timestamp: str
        :rtype: dict
        """
        match = time_re.match(timestamp)
        return match.groupdict() if match else None

    @staticmethod
    def checksum(filename):
        """ Generate checksum for the filename

        :type filename: str
        :rtype: str
        """
        return ''.join(chr(ord(a) & ord(b)) for a, b in zip(filename[:4], "SEGA"))

    @staticmethod
    def is_valid_pw_save(data):
        """ Test if data is a valid PlanetWeb VMU save

        :type data: bytes
        :rtype: dict or None
        """
        match = vmu_re.match(data)
        return match.groupdict() if match else None


if __name__ == "__main__":
    test = {
        'checksum': 100,
        'description': "desc",
        'copyright': 'public domain',
        'version': 2,
        'file_number': 1,
        'resource_name': 'fuck',
        'filename': 'fuck',
        'unused': 0,
        'unknown': 0,
        'file_size': 0}

    time = {
        'year': 98,
        'month': 10,
        'day': 10,
        'hour': 8,
        'minute': 1,
        'second': 2,
        'weekday': 3}

    p = PlanetWebTranslator()
    t = time_format.build(time)
    print(t)
    print(time_format.parse(t))

    test['time'] = time

    t = vmi_format.build(test)
    print(vmi_format.parse(t))
    print(generate_translate_table())

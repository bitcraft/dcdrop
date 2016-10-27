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

import base64
import re
import string
import struct
import sys

org64 = "=+/0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
vmu64 = "=y/270PlgMerTAXsZIx5+UpoDkFCLcwQJ419WEBihNGSbaYOqzfKH6ndmujt83vVR"
translate_table = string.maketrans(org64, vmu64)

# we are dealing with a small amount of data, a regex works fine.
# tested with planetweb 2.0 browser
vmu_re = re.compile(
    "filename=(?P<filename>.*)&fs=(?P<filesize>\d*)&bl=(?P<blocks>\d*).*&tm=(?P<timestamp>\d*)\r\n\r\n(?P<data>.*)",
    re.DOTALL)



def decode_pw_save(data):
    """
    Parse raw data from a PlanetWeb browser save.
    Will create two new files (VMI/VMS) from the data.

    Tested with data from PlanetWeb browser 2.0.
    """

    match = vmu_re.match(data)

    if match is None:
        raise ValueError, "Data does not conform to PlanetWeb spec"

    data = match.group("data").translate(translate_table)
    real_data = base64.b64decode(data)

    # build a VMI file
    filename = match.group("filename")

    desc = real_data[:16]

    save_name = None
    if desc[:6] == "REPLAY":
        desc = desc.replace("vs", "v")
        series = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for char in series:
            save_name = desc[7:14] + char
            try:
                fh = open(save_name + ".VMS")
            except:
                break
            if fh.read() == real_data:
                print("DC save is already saved as %s.  Quitting." % save_name)
                return

    else:
        save_name = filename[:8]

    checksum = ''.join(chr(ord(a) & ord(b)) for a, b in zip(filename[:4], "SEGA"))
    copyw = "Public Domain"
    year, month, day, hour, minute, second, weekday = \
        re.match("(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d)", (match.group("timestamp"))).groups()
    ver = 0
    fn = 1
    # vmsname = filename
    mode = 0
    unknown = 0
    filesize = len(real_data)
    vmi_data = struct.pack("<4s32s32shbbbbbbhh8s12shhi",
                           str(checksum), str(desc), str(copyw), int(year), int(month), int(day),
                           int(hour), int(minute), int(second), int(weekday),
                           int(ver), int(fn), str(save_name), str(filename), int(mode), int(unknown), int(filesize))

    print("Saving DC save file: \"%s\": %s.") % (desc.strip(), save_name)

    vmi_file = open("%s.VMI" % save_name, "w")
    vmi_file.write(vmi_data)

    vms_file = open("%s.VMS" % save_name, "w")
    vms_file.write(real_data)


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        decode_pw_save(open(filename).read())

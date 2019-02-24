# rdserialtool
# Copyright (C) 2019 Ryan Finnie
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import struct
import datetime
import logging

CHARGING_UNKNOWN = 0
CHARGING_QC2 = 1
CHARGING_QC3 = 2
CHARGING_APP2_4A = 3
CHARGING_APP2_1A = 4
CHARGING_APP1_0A = 5
CHARGING_APP0_5A = 6
CHARGING_DCP1_5A = 7
CHARGING_SAMSUNG = 8


class DeviceBluetooth:
    dev = None

    def __init__(self, address, port=1):
        import bluetooth
        self._bluetooth = bluetooth
        self.address = address
        self.port = port

    def connect(self):
        logging.debug('CONNECT')
        self.dev = self._bluetooth.BluetoothSocket(self._bluetooth.RFCOMM)
        self.dev.connect((self.address, self.port))

    def close(self):
        if self.dev is None:
            return
        logging.debug('CLOSE')
        self.dev.close()
        self.dev = None

    def send(self, data):
        logging.debug('SEND: {}'.format(repr(data)))
        self.dev.send(data)

    def recv(self):
        data = b''
        while(len(data) < 130):
            data += self.dev.recv(1024)
        logging.debug('RECV: {}'.format(repr(data)))
        return data


class DeviceSerial:
    dev = None

    def __init__(self, device, baudrate=9600):
        import serial
        self._serial = serial
        self.device = device
        self.baudrate = baudrate

    def connect(self):
        logging.debug('CONNECT')
        self.dev = self._serial.Serial()
        self.dev.port = self.device
        self.dev.baudrate = self.baudrate
        self.dev.writeTimeout = 0
        self.dev.open()

    def close(self):
        if self.dev is None:
            return
        logging.debug('CLOSE')
        self.dev.close()
        self.dev = None

    def send(self, data):
        logging.debug('SEND: {}'.format(repr(data)))
        self.dev.write(data)

    def recv(self):
        data = b''
        while(len(data) < 130):
            data += self.dev.read()
        logging.debug('RECV: {}'.format(repr(data)))
        return data


class DataGroup:
    group = 0
    amp_hours = 0
    watt_hours = 0

    def __repr__(self):
        return ('<DataGroup {}: {:0.03f}Ah, {:0.03f}Wh>'.format(
            self.group,
            self.amp_hours,
            self.watt_hours,
        ))

    def __init__(self, group=0):
        self.group = group


class Response:
    def __repr__(self):
        return ('<Response: {} at {}, {:0.02f}V, {:0.03f}A>'.format(
            self.device_type,
            self.collection_time,
            self.volts,
            self.amps,
        ))

    def __init__(self, data=None, collection_time=None, device_type='UM24C'):
        self.device_type = device_type
        if device_type == 'UM25C':
            self.device_multiplier = 10
        else:
            self.device_multiplier = 1

        self._std_defs = {
            'start': (
                'Start bytes', 0, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'volts': (
                'Volts', 2, 2,
                lambda x: x / (100 * self.device_multiplier),
                lambda x: int(x * (100 * self.device_multiplier)),
            ),
            'amps': (
                'Amps', 4, 2,
                lambda x: x / (1000 * self.device_multiplier),
                lambda x: int(x * (1000 * self.device_multiplier)),
            ),
            'watts': (
                'Watts', 6, 4,
                lambda x: x / 1000,
                lambda x: int(x * 1000),
            ),
            'temp_c': (
                'Temperature (Celsius)', 10, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'temp_f': (
                'Temperature (Fahrenheit)', 12, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'data_group_selected': (
                'Currently selected data group', 14, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'data_line_positive_volts': (
                'Positive data line volts', 96, 2,
                lambda x: x / 100,
                lambda x: int(x * 100),
            ),
            'data_line_negative_volts': (
                'Negative data line volts', 98, 2,
                lambda x: x / 100,
                lambda x: int(x * 100),
            ),
            'charging_mode': (
                'Charging mode', 100, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'record_amphours': (
                'Recorded amp-hours', 102, 4,
                lambda x: x / 1000,
                lambda x: int(x * 1000),
            ),
            'record_watthours': (
                'Recorded watt-hours', 106, 4,
                lambda x: x / 1000,
                lambda x: int(x * 1000),
            ),
            'record_threshold': (
                'Recording threshold (Amps)', 110, 2,
                lambda x: x / 100,
                lambda x: int(x * 100),
            ),
            'record_seconds': (
                'Recorded time (Seconds)', 112, 4,
                lambda x: x,
                lambda x: int(x),
            ),
            'recording': (
                'Recording', 116, 2,
                lambda x: bool(x),
                lambda x: int(x),
            ),
            'screen_timeout': (
                'Screen timeout (Minutes)', 118, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'screen_brightness': (
                'Screen brightness', 120, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'resistance': (
                'Resistance (Ohms)', 122, 4,
                lambda x: x / 10,
                lambda x: int(x * 10),
            ),
            'screen_selected': (
                'Currently selected screen', 126, 2,
                lambda x: x,
                lambda x: int(x),
            ),
            'end': (
                'End bytes', 128, 2,
                lambda x: x,
                lambda x: int(x),
            ),
        }

        if collection_time is None:
            collection_time = datetime.datetime.now()
        self.collection_time = collection_time
        for name in self._std_defs:
            setattr(self, name, 0)
        self.data_groups = [DataGroup(x) for x in range(10)]
        self.labels = {x: self._std_defs[x][0] for x in self._std_defs}
        self.labels['data_groups'] = 'Data groups'
        self.labels['collection_time'] = 'Collection time'

        if data:
            self.load(data)

    def dump(self):
        data = bytearray(130)
        for name in self._std_defs:
            pos = self._std_defs[name][1]
            pos_len = self._std_defs[name][2]
            if pos_len == 2:
                pack_format = '>H'
            elif pos_len == 4:
                pack_format = '>L'
            else:
                pack_format = 'B'
            conversion_dump = self._std_defs[name][4]
            data[pos:pos+pos_len] = struct.pack(pack_format, conversion_dump(getattr(self, name)))

        for data_group in self.data_groups:
            if (data_group.group > 9) or (data_group.group < 0):
                continue
            pos = 16 + (data_group.group * 8)
            data[pos:pos+4] = struct.pack('>L', int(data_group.amp_hours * 1000))
            data[pos+4:pos+8] = struct.pack('>L', int(data_group.watt_hours * 1000))
        return bytes(data)

    def load(self, data):
        if len(data) != 130:
            raise ValueError('Invalid data length', data)
        logging.debug('Start: 0x{:02x}{:02x}, end: 0x{:02x}{:02x}'.format(data[0], data[1], data[128], data[129]))
        for name in self._std_defs:
            pos = self._std_defs[name][1]
            pos_len = self._std_defs[name][2]
            if pos_len == 2:
                pack_format = '>H'
            elif pos_len == 4:
                pack_format = '>L'
            else:
                pack_format = 'B'
            conversion_load = self._std_defs[name][3]
            val = conversion_load(struct.unpack(pack_format, data[pos:pos+pos_len])[0])
            setattr(self, name, val)

        self.data_groups = []
        for i in range(10):
            data_group = DataGroup(i)
            pos = 16 + (i * 8)
            data_group.amp_hours = struct.unpack('>L', data[pos:pos+4])[0] / 1000
            data_group.watt_hours = struct.unpack('>L', data[pos+4:pos+8])[0] / 1000
            self.data_groups.append(data_group)
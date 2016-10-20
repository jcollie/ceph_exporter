# -*- mode: python; coding: utf-8 -*-

# Copyright © 2016 by Jeffrey C. Ollie
#
# This file is part of ceph_exporter.
#
# ceph_exporter is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ceph_exporter is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ceph_exporter.  If not, see
# <http://www.gnu.org/licenses/>.

from twisted.logger import Logger

from ...prometheus import Sample
from ...prometheus import Label

from .. import Ceph
from ..metrics import ceph_objects
from ..metrics import ceph_pool
from ..metrics import ceph_storage_bytes

class CephDf(Ceph):
    log = Logger()
    subcommand = ['df']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph_storage_bytes',
               [Label('fsid', self.fsid),
                Label('scope', 'cluster'),
                Label('type', 'used')],
               data['stats']['total_used_bytes'],
               timestamp)
        Sample('ceph_storage_bytes',
               [Label('fsid', self.fsid),
                Label('scope', 'cluster'),
                Label('type', 'available')],
               data['stats']['total_avail_bytes'],
               timestamp)

        for pool in data['pools']:
            Sample('ceph_pool',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name'])],
                   1,
                   timestamp)
            Sample('ceph_storage_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pool'),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name']),
                    Label('type', 'used')],
                   pool['stats']['bytes_used'],
                   timestamp)
            Sample('ceph_objects',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pool'),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name']),
                    Label('type', 'objects')],
                   pool['stats']['objects'],
                   timestamp)

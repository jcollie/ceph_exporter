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

from ..metrics.ceph_epoch import ceph_epoch
from ..metrics.ceph_mds_state import ceph_mds_state
from ..metrics.ceph_mds_laggy_since import ceph_mds_laggy_since

class CephMdsDump(Ceph):
    log = Logger()
    subcommand = ['mds', 'dump']

    # this is changed in Jewel
    def processData(self, result):
        data, timestamp = result

        Sample('ceph_epoch',
               [Label('fsid', self.fsid),
                Label('type', 'mds')],
               data['epoch'],
               timestamp)

        for info in data['info'].values():
            for state in ['up:active', 'up:replay', 'up:rejoin']:
                if state == info['state']:
                    value = 1
                else:
                    value = 0

                Sample('ceph_mds_state',
                       [Label('fsid', self.fsid),
                        Label('gid', '{}'.format(info['gid'])),
                        Label('rank', '{}'.format(info['rank'])),
                        Label('name', info['name']),
                        Label('state', state)],
                       value,
                       timestamp)

            if info['state'] not in ['up:active', 'up:replay', 'up:rejoin']:
                Sample('ceph_mds_state',
                       [Label('fsid', self.fsid),
                        Label('gid', '{}'.format(info['gid'])),
                        Label('rank', '{}'.format(info['rank'])),
                        Label('name', info['name']),
                        Label('state', info['state'])],
                       1,
                       timestamp)

            if 'laggy_since' in info:
                Sample('ceph_mds_laggy_since',
                       [Label('fsid', self.fsid),
                        Label('gid', '{}'.format(info['gid'])),
                        Label('rank', '{}'.format(info['rank'])),
                        Label('name', info['name'])],
                       arrow.get(info['laggy_since']).replace(tzinfo=tzlocal()).float_timestamp,
                       timestamp)
            else:
                Sample('ceph_mds_laggy_since',
                       [Label('fsid', self.fsid),
                        Label('gid', '{}'.format(info['gid'])),
                        Label('rank', '{}'.format(info['rank'])),
                        Label('name', info['name'])],
                       timestamp.float_timestamp,
                       timestamp)

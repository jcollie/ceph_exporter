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

from ...prometheus import Label
from ...prometheus import Metric
from ...prometheus import Sample

from .. import Ceph

from ..metrics.ceph_osd import ceph_osd
from ..metrics.ceph_osd_down import ceph_osd_down
from ..metrics.ceph_osd_in import ceph_osd_in
from ..metrics.ceph_osd_out import ceph_osd_out
from ..metrics.ceph_osd_up import ceph_osd_up
from ..metrics.ceph_pool import ceph_pool
from ..metrics.ceph_pool_min_size import ceph_pool_min_size
from ..metrics.ceph_pool_pg_num import ceph_pool_pg_num
from ..metrics.ceph_pool_pgp_num import ceph_pool_pgp_num
from ..metrics.ceph_pool_size import ceph_pool_size

class CephOsdDump(Ceph):
    log = Logger()
    subcommand = ['osd', 'dump']

    def processData(self, result):
        data, timestamp = result

        for pool in data['pools']:
            Sample('ceph_pool',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool'])),
                    Label('name', pool['pool_name'])],
                   1,
                   timestamp)
            Sample('ceph_pool_size',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool'])),
                    Label('name', pool['pool_name'])],
                   pool['size'],
                   timestamp)
            Sample('ceph_pool_min_size',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool'])),
                    Label('name', pool['pool_name'])],
                   pool['min_size'],
                   timestamp)
            Sample('ceph_pool_pg_num',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool'])),
                    Label('name', pool['pool_name'])],
                   pool['pg_num'],
                   timestamp)
            Sample('ceph_pool_pgp_num',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool'])),
                    Label('name', pool['pool_name'])],
                   pool['pg_placement_num'],
                   timestamp)

        for osd in data['osds']:
            Sample('ceph_osd',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   1,
                   timestamp)
            Sample('ceph_osd_up',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   osd['up'],
                   timestamp)
            Sample('ceph_osd_down',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   1 - osd['up'],
                   timestamp)
            Sample('ceph_osd_in',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   osd['in'],
                   timestamp)
            Sample('ceph_osd_out',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   1 - osd['in'],
                   timestamp)

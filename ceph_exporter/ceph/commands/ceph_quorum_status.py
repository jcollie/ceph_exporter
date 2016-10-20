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
from ..metrics.ceph_mon_count import ceph_mon_count
from ..metrics.ceph_mon_quorum import ceph_mon_quorum

class CephQuorumStatus(Ceph):
    log = Logger()
    # quorum_status returns same info as mds dump plus election epoch
    subcommand = ['quorum_status']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph_mon_count',
               [Label('fsid', self.fsid)],
               len(data['monmap']['mons']),
               timestamp)
        Sample('ceph_mon_quorum',
               [Label('fsid', self.fsid)],
               len(data['quorum']),
               timestamp)
        Sample('ceph_epoch',
               [Label('fsid', self.fsid),
                Label('type', 'mon')],
               data['monmap']['epoch'],
               timestamp)
        Sample('ceph_epoch',
               [Label('fsid', self.fsid),
                Label('type', 'mon_election')],
               data['election_epoch'],
               timestamp)

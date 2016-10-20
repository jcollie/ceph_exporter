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

from ..metrics.ceph_pg_states import ceph_pg_states
from ..metrics.ceph_pgmap_version import ceph_pgmap_version

class CephStatus(Ceph):
    log = Logger()
    subcommand = ['status']

    def processData(self, result):
        data, timestamp = result

        states = self.states.copy()
        for pgs_by_state in data['pgmap']['pgs_by_state']:
            if pgs_by_state['state_name'] not in states:
                self.log.debug('Unknown state "{state:}"', state = pgs_by_state['state_name'])
            states.discard(pgs_by_state['state_name'])
            Sample('ceph_pg_states',
                   [Label('fsid', self.fsid),
                    Label('state', pgs_by_state['state_name'])],
                   pgs_by_state['count'],
                   timestamp)
        for state in states:
            Sample('ceph_pg_states',
                   [Label('fsid', self.fsid),
                    Label('state', state)],
                   0,
                   timestamp)

        Sample('ceph_pgmap_version',
               [Label('fsid', self.fsid)],
               data['pgmap']['version'],
               timestamp)

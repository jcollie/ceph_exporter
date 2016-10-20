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

import arrow
import re
from dateutil.tz import tzlocal

from twisted.logger import Logger

from ...prometheus import Sample
from ...prometheus import Label

from .. import Ceph

from ..metrics.ceph_bytes_recovered import ceph_bytes_recovered
from ..metrics.ceph_keys_recovered import ceph_keys_recovered
from ..metrics.ceph_objects import ceph_objects
from ..metrics.ceph_objects_recovered import ceph_objects_recovered
from ..metrics.ceph_osd import ceph_osd
from ..metrics.ceph_osd_latency_seconds import ceph_osd_latency_seconds
from ..metrics.ceph_osd_number_snap_trimming import ceph_osd_number_snap_trimming
from ..metrics.ceph_osd_snap_trim_queue_length import ceph_osd_snap_trim_queue_length
from ..metrics.ceph_pg import ceph_pg
from ..metrics.ceph_pg_state import ceph_pg_state
from ..metrics.ceph_pg_timestamp import ceph_pg_timestamp
from ..metrics.ceph_read_bytes import ceph_read_bytes
from ..metrics.ceph_read_ops import ceph_read_ops
from ..metrics.ceph_storage_bytes import ceph_storage_bytes
from ..metrics.ceph_write_bytes import ceph_write_bytes
from ..metrics.ceph_write_ops import ceph_write_ops

pgid_re = re.compile(r'\A([a-f0-9]+)\.([a-f0-9]+)\Z', re.IGNORECASE)

def pgid_to_pool(value):
    match = pgid_re.match(value)
    if match:
        return match.group(1)
    return None

class CephPgDump(Ceph):
    log = Logger()
    subcommand = ['pg', 'dump']

    def processData(self, result):
        data, timestamp = result

        for key, stat in [('num_objects', 'objects'),
                          ('num_object_clones', 'clones'),
                          ('num_object_copies', 'copies'),
                          ('num_objects_missing_on_primary', 'missing_on_primary'),
                          ('num_objects_degraded', 'degraded'),
                          ('num_objects_misplaced', 'misplaced'),
                          ('num_objects_unfound', 'unfound'),
                          ('num_objects_dirty', 'dirty')]:

            Sample('ceph_objects',
                   [Label('fsid', self.fsid),
                    Label('scope', 'cluster'),
                    Label('type', stat)],
                   data['pg_stats_sum']['stat_sum'][key],
                   timestamp)

        for direction in ['read', 'write']:
            Sample('ceph_{}_ops'.format(direction),
                   [Label('fsid', self.fsid),
                    Label('scope', 'cluster')],
                   data['pg_stats_sum']['stat_sum']['num_{}'.format(direction)],
                   timestamp)

            Sample('ceph_{}_bytes'.format(direction),
                   [Label('fsid', self.fsid),
                    Label('scope', 'cluster')],
                   data['pg_stats_sum']['stat_sum']['num_{}_kb'.format(direction)] * 1024,
                   timestamp)

        for osd in data['osd_stats']:
            Sample('ceph_osd',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   1,
                   timestamp)
            for key, stat in [('kb_avail', 'available'),
                              ('kb_used', 'used')]:
                Sample('ceph_storage_bytes',
                       [Label('fsid', self.fsid),
                        Label('scope', 'osd'),
                        Label('osd', '{:d}'.format(osd['osd'])),
                        Label('type', stat)],
                       osd[key] * 1024,
                       timestamp)
            Sample('ceph_osd_snap_trim_queue_length',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   osd['snap_trim_queue_len'],
                   timestamp)
            Sample('ceph_osd_number_snap_trimming',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   osd['num_snap_trimming'],
                   timestamp)
            Sample('ceph_osd_latency_seconds',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd'])),
                    Label('type', 'apply')],
                   osd['fs_perf_stat']['apply_latency_ms'] / 1000.0,
                   timestamp)
            Sample('ceph_osd_latency_seconds',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd'])),
                    Label('type', 'commit')],
                   osd['fs_perf_stat']['commit_latency_ms'] / 1000.0,
                   timestamp)

        for pg in data['pg_stats']:
            Sample('ceph_pg',
                   [Label('fsid', self.fsid),
                    Label('pool', pgid_to_pool(pg['pgid'])),
                    Label('pgid', pg['pgid'])],
                   1,
                   timestamp)

            Sample('ceph_storage_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pg'),
                    Label('pool', pgid_to_pool(pg['pgid'])),
                    Label('pgid', pg['pgid']),
                    Label('type', 'used')],
                   pg['stat_sum']['num_bytes'],
                   timestamp)

            for key, stat in [('num_objects', 'objects'),
                              ('num_object_clones', 'clones'),
                              ('num_object_copies', 'copies'),
                              ('num_objects_missing_on_primary', 'missing_on_primary'),
                              ('num_objects_degraded', 'degraded'),
                              ('num_objects_misplaced', 'misplaced'),
                              ('num_objects_unfound', 'unfound'),
                              ('num_objects_dirty', 'dirty')]:

                Sample('ceph_objects',
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid']),
                        Label('type', stat)],
                       pg['stat_sum'][key],
                       timestamp)

            for direction in ['read', 'write']:
                Sample('ceph_{}_ops'.format(direction),
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid'])],
                       pg['stat_sum']['num_{}'.format(direction)],
                       timestamp)

                Sample('ceph_{}_bytes'.format(direction),
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid'])],
                       pg['stat_sum']['num_{}_kb'.format(direction)] * 1024,
                       timestamp)

            for stat in ['objects', 'bytes', 'keys']:
                Sample('ceph_{}_recovered'.format(stat),
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid'])],
                       pg['stat_sum']['num_{}_recovered'.format(stat)],
                       timestamp)

            for key, stat in [('last_fresh', 'last_fresh'),
                              ('last_change', 'last_change'),
                              ('last_active', 'last_active'),
                              ('last_peered', 'last_peered'),
                              ('last_clean', 'last_clean'),
                              ('last_became_active', 'last_became_active'),
                              ('last_became_peered', 'last_became_peered'),
                              ('last_unstale', 'last_unstale'),
                              ('last_undegraded', 'last_undegraded'),
                              ('last_fullsized', 'last_fullsized'),
                              ('last_scrub_stamp', 'last_scrub'),
                              ('last_deep_scrub_stamp', 'last_deep_scrub'),
                              ('last_clean_scrub_stamp', 'last_clean_scrub')]:
                if key in pg:
                    value = arrow.get(pg[key]).replace(tzinfo = tzlocal()).float_timestamp
                    Sample('ceph_pg_timestamp',
                           [Label('fsid', self.fsid),
                            Label('pool', pgid_to_pool(pg['pgid'])),
                            Label('pgid', pg['pgid']),
                            Label('event', stat)],
                           value,
                           timestamp)

            for state in self.states:
                if pg['state'] == state:
                    value = 1
                else:
                    value = 0
                Sample('ceph_pg_state',
                       [Label('fsid', self.fsid),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid']),
                        Label('state', state)],
                       value,
                       timestamp)
            if pg['state'] not in self.states:
                self.log.debug('Unknown state "{state:}"', state = pg['state'])
                Sample('ceph_pg_state',
                       [Label('fsid', self.fsid),
                        Label('pool', pgid_to_pool(pg['pgid'])),
                        Label('pgid', pg['pgid']),
                        Label('state', pg['state'])],
                       1,
                       timestamp)

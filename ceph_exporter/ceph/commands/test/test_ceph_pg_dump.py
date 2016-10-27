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
import inspect
import json
import pkg_resources
import uuid

from twisted.trial.unittest import TestCase

from ....prometheus import metrics
from ....prometheus import Label
from ..ceph_pg_dump import pgid_to_pool
from ..ceph_pg_dump import CephPgDump

class PgidToPoolTest(TestCase):
    def test_pgid_to_pool(self):
        result = pgid_to_pool('8.4c')
        self.assertEqual(result, '8')

class CephPgDumpHammer1Test(TestCase):
    def setUp(self):
        self.fsid = '{}'.format(uuid.uuid4())
        self.timestamp = arrow.now()
        bytes_data = pkg_resources.resource_string(inspect.getmodule(self).__name__, 'data/ceph_pg_dump_hammer_1.json')
        string_data = bytes_data.decode('utf-8')
        self.data = json.loads(string_data)
        self.ceph_pg_dump = CephPgDump(self.fsid, None)
        self.ceph_pg_dump.processData((self.data, self.timestamp))

    def tearDown(self):
        for metric in metrics.values():
            metric.samples = []
        del self.fsid
        del self.timestamp
        del self.data
        del self.ceph_pg_dump

    def test_fsids(self):
        for metric in metrics.values():
            for sample in metric.samples:
                self.assertIn(Label('fsid', self.fsid), sample.labels)

    def test_ceph_objects_1(self):
        self.assertIn('ceph_objects', metrics)

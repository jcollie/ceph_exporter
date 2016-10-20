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

import sys
import configparser
import argparse

from twisted.internet import reactor
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver
from twisted.logger import Logger

from .server import Server
from .ceph.commands.ceph_df import CephDf
from .ceph.commands.ceph_mds_dump import CephMdsDump
from .ceph.commands.ceph_osd_dump import CephOsdDump
from .ceph.commands.ceph_pg_dump import CephPgDump
from .ceph.commands.ceph_quorum_status import CephQuorumStatus
from .ceph.commands.ceph_status import CephStatus

class Main(object):
    log = Logger()

    def __init__(self, options):
        self.options = options

        config = configparser.ConfigParser()
        config.read(self.options.config)

        self.fsid = config['global']['fsid']

        reactor.callWhenRunning(self.start)

    def start(self):
        self.server             = Server(self.options)
        self.ceph_df            = CephDf(self.fsid, self.options)
        self.ceph_mds_dump      = CephMdsDump(self.fsid, self.options)
        self.ceph_osd_dump      = CephOsdDump(self.fsid, self.options)
        self.ceph_pg_dump       = CephPgDump(self.fsid, self.options)
        self.ceph_quorum_status = CephQuorumStatus(self.fsid, self.options)
        self.ceph_status        = CephStatus(self.fsid, self.options)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--config',
                        default='/etc/ceph/ceph.conf',
                        help="Ceph config file location, default is `/etc/ceph/ceph.conf`")
    parser.add_argument('--name',
                        default='client.admin',
                        help="Ceph client name used to authenticate to the Ceph cluster, default is `client.admin`")
    parser.add_argument('--keyring',
                        default='/etc/ceph/ceph.client.admin.keyring',
                        help="Name of the file that contains key for authentication with the Ceph cluster, default is `/etc/ceph/ceph.client.admin.keyring`")
    parser.add_argument('--endpoint',
                        default='tcp:9999',
                        help="Twisted server endpoint specifier, default is `tcp:9192`")
    parser.add_argument('--executable',
                        default='/usr/bin/ceph',
                        help="Path to the Ceph command line client executable, default is `/usr/bin/ceph`")

    options = parser.parse_args()

    output = textFileLogObserver(sys.stderr)
    globalLogBeginner.beginLoggingTo([output])

    m = Main(options)
    reactor.run()

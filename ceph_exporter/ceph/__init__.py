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
import json

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.error import ProcessDone
from twisted.internet.error import ProcessTerminated
from twisted.internet.protocol import ProcessProtocol
from twisted.logger import Logger

from ..prometheus import Label
from ..prometheus import Metric
from ..prometheus import Sample

from .metrics.ceph import ceph
from .metrics.ceph_command_runtime import ceph_command_runtime

class CephJsonProtocol(ProcessProtocol):
    log = Logger()

    def __init__(self, fsid, finished, command):
        self.fsid = fsid
        self.finished = finished
        self.command = command
        self.out_data = []
        self.err_data = []
        self.start_time = None

    def connectionMade(self):
        self.start_time = arrow.now()
        self.transport.closeStdin()

    def outReceived(self, data):
        self.out_data.append(data)

    def errReceived(self, data):
        self.err_data.append(data)

    def inConnectionLost(self):
        pass

    def outConnectionLost(self):
        self.end_time = arrow.now()

    def errConnectionLost(self):
        pass

    def processExited(self, status):
        pass

    def processEnded(self, status):
        if not isinstance(status.value, (ProcessDone, ProcessTerminated)):
            self.log.debug('process ended {r:}', r = status.value)
            self.finished.callback(None)
            return

        if isinstance(status.value, ProcessTerminated):
            self.log.debug('process ended {r:}', r = status.value)
            self.log.debug('{e:}', e = (b''.join(err_data)).decode('utf-8'))
            self.finished.callback(None)
            return

        runtime = self.end_time - self.start_time
        timestamp = self.start_time + (runtime / 2)

        try:
            data = b''.join(self.out_data)
            data = data.decode('utf-8')
            data = json.loads(data)
        except ValueError as e:
            self.log.debug('command: {c:}\noutput: {o:r}', c = self.command, o = self.out_data)
            self.finished.errback(e)
            return

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)
        Sample('ceph_command_runtime',
               [Label('fsid', self.fsid),
                Label('command', ' '.join(self.command))],
               runtime.total_seconds(),
               timestamp)

        self.finished.callback((data, timestamp))

class Ceph(object):
    log = Logger()

    interval = 30.0

    states = set(['activating',
                  'activating+degraded',
                  'activating+degraded+remapped',
                  'activating+remapped',
                  'activating+undersized+degraded',
                  'activating+undersized+degraded+remapped',
                  'active',
                  'active+clean',
                  'active+clean+inconsistent',
                  'active+clean+scrubbing',
                  'active+clean+scrubbing+deep',
                  'active+clean+scrubbing+deep+inconsistent+repair',
                  'active+degraded',
                  'active+degraded+remapped',
                  'active+degraded+remapped+backfilling',
                  'active+recovering+degraded',
                  'active+recovering+degraded+remapped',
                  'active+recovery_wait+degraded',
                  'active+recovery_wait+degraded+remapped',
                  'active+remapped',
                  'active+remapped+backfill_toofull',
                  'active+remapped+backfilling',
                  'active+remapped+wait_backfill',
                  'active+remapped+wait_backfill+backfill_toofull',
                  'active+undersized+degraded',
                  'active+undersized+degraded+remapped',
                  'active+undersized+degraded+remapped+backfill_toofull',
                  'active+undersized+degraded+remapped+backfilling',
                  'active+undersized+degraded+remapped+wait_backfill',
                  'active+undersized+degraded+remapped+wait_backfill+backfill_toofull',
                  'active+undersized+remapped',
                  'creating',
                  'inactive',
                  'peering',
                  'remapped',
                  'remapped+peering',
                  'stale+active+clean',
                  'stale+active+remapped+backfilling'])

    def __init__(self, fsid, options):
        self.fsid = fsid
        self.options = options

        reactor.callWhenRunning(self.getData)

    def buildCommand(self):
        real_command = ['ceph',
                        '--conf', self.options.config,
                        '--keyring', self.options.keyring,
                        '--name', self.options.name] + \
                        self.subcommand + \
                        ['--format', 'json']
        short_command = ['ceph'] + self.subcommand
        #self.log.debug('{c:}', c = command)
        return real_command, short_command

    def getData(self):
        reactor.callLater(self.interval, self.getData)

        real_command, short_command = self.buildCommand()

        finished = Deferred()
        finished.addCallback(self.processData)
        finished.addErrback(self.processError, real_command)

        protocol = CephJsonProtocol(self.fsid, finished, short_command)

        reactor.spawnProcess(protocol,
                             self.options.executable,
                             real_command)

    def processError(self, failure, real_command):
        self.log.failure('command failed: "{real_command:}"',
                         real_command = real_command,
                         failure = failure)

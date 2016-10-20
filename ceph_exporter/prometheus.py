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
import datetime

from twisted.internet import reactor
from twisted.logger import Logger

metrics = {}

def escape(value):
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

class Label(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def fmt(self):
        return '{}="{}"'.format(self.name, escape(self.value))

class Sample(object):
    log = Logger()
    def __init__(self, name, labels, value, timestamp):
        global metrics
        self.labels = labels
        self.value = value
        self.timestamp = timestamp
        if name not in metrics:
            self.log.error('No metric named "{name:}" has been declared!', name = name)
            return
        metrics[name].addSample(self)

    def fmt(self):
        result = ''
        if self.labels:
            result += '{{{:s}}}'.format(','.join(map(lambda l: l.fmt(), self.labels)))
        result += ' {}'.format(self.value)
        if self.timestamp is not None:
            result += ' {:d}'.format(int(round(self.timestamp.float_timestamp * 1000)))
        return result

    def isExpired(self, now):
        return (now - self.timestamp) < datetime.timedelta(seconds = 500)

class Metric(object):
    log = Logger()

    def __init__(self, name, help = None, type = None):
        global metrics

        self.name = name
        self.help = help
        self.type = type
        self.samples = []
        reactor.callLater(30.0, self.expireSamples)

        metrics[self.name] = self

    def expireSamples(self):
        reactor.callLater(30.0, self.expireSamples)

        now = arrow.now()
        self.samples = [sample for sample in self.samples if sample.isExpired(now)]

    def fmt(self):
        result = ''
        if self.help is not None:
            result += '# HELP {} {}\n'.format(self.name, self.help)
        if self.type is not None:
            result += '# TYPE {} {}\n'.format(self.name, self.type)
        for sample in sorted(self.samples, key = lambda s: int(round(s.timestamp.float_timestamp * 1000))):
            result += '{}{}\n'.format(self.name, sample.fmt())
        # prometheus doesn't seem to like it if you repeat yourself
        self.samples = []
        return result

    def addSample(self, sample):
        self.samples.append(sample)

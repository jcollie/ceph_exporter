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

from twisted.internet import reactor
from twisted.logger import Logger
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import endpoints

from .prometheus import metrics

class MetricsPage(Resource):
    log = Logger()
    isLeaf = True

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        global metrics
        request.setHeader(b'Content-Type', 'text/plain; charset=utf-8; version=0.0.4')
        results = []
        metric_names = sorted(metrics.keys())
        for metric_name in metric_names:
            results.append(metrics[metric_name].fmt())
        result = ''.join(results).encode('utf-8')
        return result

class RootPage(Resource):
    log = Logger()
    isLeaf = False

    def render_GET(self, request):
        request.setHeader(b'Content-Type', 'text/plain; charset=utf-8')
        return b'OK\n'

class Server(object):
    def __init__(self, options):
        self.options = options
        self.metrics = MetricsPage()
        self.root = RootPage()
        self.root.putChild(b'metrics', self.metrics)
        self.site = Site(self.root)
        self.site.noisy = False

        self.endpoint = endpoints.serverFromString(reactor, self.options.endpoint)
        self.endpoint.listen(self.site)

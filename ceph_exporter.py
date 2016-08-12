# -*- mode: python; coding: utf-8 -*-

import sys
import json
import datetime
import arrow
import configparser
import argparse

from twisted.internet import reactor
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver
from twisted.logger import Logger
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.defer import Deferred
from twisted.internet.error import ProcessDone
from twisted.internet.error import ProcessTerminated
from twisted.web.server import Site
from twisted.web.server import GzipEncoderFactory
from twisted.web.resource import EncodingResourceWrapper
from twisted.web.resource import Resource
from twisted.internet import endpoints

def escape(value):
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n','\\n')

class Label(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def fmt(self):
        return '{}="{}"'.format(self.name, escape(self.value))

metrics = {}

class Sample(object):
    def __init__(self, name, labels, value, timestamp):
        global metrics
        self.labels = labels
        self.value = value
        self.timestamp = timestamp
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

class CephJsonProtocol(ProcessProtocol):
    log = Logger()

    def __init__(self, finished, command):
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
        pass

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

        timestamp = self.start_time + ((self.end_time - self.start_time) / 2)

        try:
            data = b''.join(self.out_data)
            data = data.decode('utf-8')
            data = json.loads(data)
        except ValueError as e:
            self.log.debug('command: {c:}\noutput: {o:r}', c = self.command, o = data)
            self.finished.errback(e)
            return
        
        self.finished.callback((data, timestamp))

class Ceph(object):
    interval = 30.0

    def __init__(self, fsid, options):
        self.fsid = fsid
        self.options = options

        reactor.callWhenRunning(self.getData)

    def buildCommand(self):
        command = ['ceph',
                   '--conf', self.options.config,
                   '--keyring', self.options.keyring,
                   '--name', self.options.name] + \
                   self.subcommand + \
                   ['--format', 'json']
        self.log.debug('{c:}', c = command)
        return command

    def getData(self):
        reactor.callLater(self.interval, self.getData)

        finished = Deferred()
        finished.addCallback(self.processData)
        finished.addErrback(self.processError)
        command = self.buildCommand()
        protocol = CephJsonProtocol(finished, command)
        reactor.spawnProcess(protocol,
                             self.options.executable,
                             command)

    def processError(self, failure):
        pass
    
class CephMonDump(Ceph):
    log = Logger()
    # quorum_status returns same info as mds dump plus election epoch
    subcommand = ['quorum_status']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)
        
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

class CephMdsDump(Ceph):
    log = Logger()
    subcommand = ['mds', 'dump']

    def processData(self, result):
        data, timestamp = result
        
        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)

        Sample('ceph_epoch',
               [Label('fsid', self.fsid),
                Label('type', 'mds')],
               data['epoch'],
               timestamp)

class CephOsdDump(Ceph):
    log = Logger()
    subcommand = ['osd', 'dump']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)
        
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
            Sample('ceph_osd_in',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   osd['in'],
                   timestamp)

class CephPgDump(Ceph):
    log = Logger()
    subcommand = ['pg', 'dump']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)

        for key, stat in [('num_objects', 'total'),
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
            Sample('ceph_operation_count',
                   [Label('fsid', self.fsid),
                    Label('scope', 'cluster'),
                    Label('type', direction)],
                   data['pg_stats_sum']['stat_sum']['num_{}'.format(direction)],
                   timestamp)

            Sample('ceph_operation_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'cluster'),
                    Label('type', direction)],
                   data['pg_stats_sum']['stat_sum']['num_{}_kb'.format(direction)] * 1024,
                   timestamp)
            
        for osd in data['osd_stats']:
            Sample('ceph_osd',
                   [Label('fsid', self.fsid),
                    Label('osd', '{:d}'.format(osd['osd']))],
                   1,
                   timestamp)
            for key, stat in [('kb_avail', 'available'),
                              ('kb_used', 'used'),
                              ('kb', 'total')]:
                Sample('ceph_bytes',
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
                    Label('pgid', pg['pgid'])],
                   1,
                   timestamp)

            Sample('ceph_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pg'),
                    Label('pgid', pg['pgid']),
                    Label('type', 'used')],
                   pg['stat_sum']['num_bytes'],
                   timestamp)
            
            for key, stat in [('num_objects', 'total'),
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
                        Label('pgid', pg['pgid']),
                        Label('type', stat)],
                       pg['stat_sum'][key],
                       timestamp)
                
            for direction in ['read', 'write']:
                Sample('ceph_operation_count',
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pgid', pg['pgid']),
                        Label('type', direction)],
                       pg['stat_sum']['num_{}'.format(direction)],
                       timestamp)

                Sample('ceph_operation_bytes',
                       [Label('fsid', self.fsid),
                        Label('scope', 'pg'),
                        Label('pgid', pg['pgid']),
                        Label('type', direction)],
                       pg['stat_sum']['num_{}_kb'.format(direction)] * 1024,
                       timestamp)
                
class CephOsdPoolStats(Ceph):
    log = Logger()
    subcommand = ['osd', 'pool', 'stats']
    interval = 5.0

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)
        
        for pool in data:
            Sample('ceph_pool',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool_id'])),
                    Label('name', pool['pool_name'])],
                   1,
                   timestamp)
            
            Sample('ceph_pool_bytes_second',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool_id'])),
                    Label('name', pool['pool_name']),
                    Label('type', 'read')],
                   pool.get('client_io_rate', {}).get('read_bytes_sec', 0),
                   timestamp)
            Sample('ceph_pool_bytes_second',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool_id'])),
                    Label('name', pool['pool_name']),
                    Label('type', 'write')],
                   pool.get('client_io_rate', {}).get('write_bytes_sec', 0),
                   timestamp)
            Sample('ceph_pool_operations_second',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['pool_id'])),
                    Label('name', pool['pool_name'])],
                   pool.get('client_io_rate', {}).get('op_per_sec', 0),
                   timestamp)

class CephDf(Ceph):
    log = Logger()
    subcommand = ['df']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)
        
        Sample('ceph_bytes',
               [Label('fsid', self.fsid),
                Label('scope', 'cluster'),
                Label('type', 'total')],
               data['stats']['total_bytes'],
               timestamp)
        Sample('ceph_bytes',
               [Label('fsid', self.fsid),
                Label('scope', 'cluster'),
                Label('type', 'used')],
               data['stats']['total_used_bytes'],
               timestamp)
        Sample('ceph_bytes',
               [Label('fsid', self.fsid),
                Label('scope', 'cluster'),
                Label('type', 'available')],
               data['stats']['total_avail_bytes'],
               timestamp)

        for pool in data['pools']:
            Sample('ceph_pool',
                   [Label('fsid', self.fsid),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name'])],
                   1,
                   timestamp)
            Sample('ceph_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pool'),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name']),
                    Label('type', 'used')],
                   pool['stats']['bytes_used'],
                   timestamp)
            Sample('ceph_bytes',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pool'),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name']),
                    Label('name', 'maximum_available')],
                   pool['stats']['max_avail'],
                   timestamp)
            Sample('ceph_objects',
                   [Label('fsid', self.fsid),
                    Label('scope', 'pool'),
                    Label('pool', '{:d}'.format(pool['id'])),
                    Label('name', pool['name']),
                    Label('type', 'total')],
                   pool['stats']['objects'],
                   timestamp)

class CephStatus(Ceph):
    log = Logger()
    subcommand = ['status']

    def processData(self, result):
        data, timestamp = result

        Sample('ceph',
               [Label('fsid', self.fsid)],
               1,
               timestamp)

        state_names = set(['activating',
                           'activating+degraded',
                           'active+clean',
                           'active+clean+scrubbing',
                           'active+clean+scrubbing+deep',
                           'active+degraded',
                           'active+recovering+degraded',
                           'active+recovery_wait+degraded',
                           'active+undersized+degraded',
                           'active+undersized+degraded+remapped',
                           'active+undersized+degraded+remapped+backfilling',
                           'active+undersized+degraded+remapped+wait_backfill',
                           'peering',
                           'remapped',
                           'remapped+peering',
                           'stale+active+clean'])
        for pgs_by_state in data['pgmap']['pgs_by_state']:
            if pgs_by_state['state_name'] in state_names:
                state_names.remove(pgs_by_state['state_name'])
            Sample('ceph_pgs_by_state',
                   [Label('fsid', self.fsid),
                    Label('state', pgs_by_state['state_name'])],
                   pgs_by_state['count'],
                   timestamp)
        for state_name in state_names:
            Sample('ceph_pgs_by_state',
                   [Label('fsid', self.fsid),
                    Label('state', state_name)],
                   0,
                   timestamp)
            
        Sample('ceph_pgmap_version',
               [Label('fsid', self.fsid)],
               data['pgmap']['version'],
               timestamp)

class MetricsPage(Resource):
    log = Logger()
    isLeaf = True

    def __init__(self):
        Resource.__init__(self)
        self.metric_exporters = []

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

    def getChild(self, name, request):
        if name == b'':
            return self
        return Resource.getChild(self, name, request)

    def render_GET(self, request):
        request.setHeader(b'Content-Type', 'text/plain; charset=utf-8')
        return b''

class Main(object):
    log = Logger()

    def __init__(self, options):
        self.options = options

        config = configparser.ConfigParser()
        config.read(self.options.config)

        self.fsid = config['global']['fsid']

        reactor.callWhenRunning(self.start)

    def start(self):
        self.metrics = MetricsPage()
        self.root = RootPage()
        self.root.putChild(b'metrics', self.metrics)
        self.site = Site(self.root)
        
        self.endpoint = endpoints.serverFromString(reactor, self.options.endpoint)
        self.endpoint.listen(self.site)

        self.mon = CephMonDump(self.fsid, self.options)
        self.mds = CephMdsDump(self.fsid, self.options)
        self.pg = CephPgDump(self.fsid, self.options)
        self.osd = CephOsdDump(self.fsid, self.options)
        self.ops = CephOsdPoolStats(self.fsid, self.options)
        self.df = CephDf(self.fsid, self.options)
        self.status = CephStatus(self.fsid, self.options)

# Meta-metric, a sample is inserted every time a command is run.
# Useful for Grafana template variables
        
Metric('ceph', None, 'gauge')

# ceph df --format json
# ['stats']['total_bytes'] => ceph_bytes{fsid="$fsid",scope="cluster",type="total"}
# ['stats']['total_used_bytes'] => ceph_bytes{fsid="$fsid",scope="cluster",type="used"}
# ['stats']['total_avail_bytes'] => ceph_bytes{fsid="$fsid",scope="cluster",type="available"}
#
# ceph pg dump --format json
# ['osd_stats'][n]['kb_avail'] => ceph_bytes{fsid="$fsid",scope="osd",osd="$osd",type="available"}
# ['osd_stats'][n]['kb_used'] => ceph_bytes{fsid="$fsid",scope="osd",osd="$osd",type="used"}
# ['osd_stats'][n]['kb'] => ceph_bytes{fsid="$fsid",scope="osd",osd="$osd",type="total"}
# ['pg_stats'][n]['stat_sum']['num_bytes'] => ceph_bytes{fsid="$fsid",scope="pg",pgid="$pgid",type="used"}
#
# ceph df --format json
# ['pools'][n]['stats']['bytes_used'] => ceph_bytes{fsid="$fsid",scope="pool",pool="$id",name="$name",type="used"}
# ['pools'][n]['stats']['max_avail'] => ceph_bytes{fsid="$fsid",scope="pool",pool="$id",name="$name",type="maximim_available"}

Metric('ceph_bytes', None, 'gauge')

# ceph mds dump --format json
# ['epoch'] => ceph_epoch{fsid="$fsid",type="mds"}
#
# ceph quorum_status --format json
# ['monmap']['epoch'] => ceph_epoch{fsid="$fsid",type="mon"}
#
# ceph quorum_status --format json
# ['election_epoch'] => ceph_epoch{fsid="$fsid",type="mon_election"}

Metric('ceph_epoch', None, 'gauge')

# ceph quorum_status --format json
# len(['monmap']['mons']) => ceph_mon_count{fsid="$fsid"}

Metric('ceph_mon_count', None, 'gauge')

# ceph quorum_status --format json
# len(['quorum']) => ceph_mon_quorum{fsid="$fsid"}

Metric('ceph_mon_quorum', None, 'gauge')

# Meta-metric, a sample gets inserted every time an OSD is encountered
# in the output.  Useful for Grafana template variables

Metric('ceph_osd', None, 'gauge')

# ceph osd dump --format json
# ['osds'][n]['in'] => ceph_osd_in{fsid="$fsid",osd="$osd"}

Metric('ceph_osd_in', 'Is the OSD in (1) or out (0)', 'gauge')

# ceph pg dump --format json
# ['osd_stats'][n]['fs_perf_stat']['apply_latency_ms'] => ceph_osd_latency_seconds{fsid="$fsid",osd="$osd",type="apply"}
# ['osd_stats'][n]['fs_perf_stat']['commit_latency_ms'] => ceph_osd_latency_seconds{fsid="$fsid",osd="$osd",type="commit"}

Metric('ceph_osd_latency_seconds', None, 'gauge')

# ceph pg dump --format json
# ['osd_stats'][n]['num_snap_trimming'] => ceph_osd_number_snap_trimming{fsid="$fsid",osd="$osd"}

Metric('ceph_osd_number_snap_trimming', None, 'gauge')

# ceph pg dump --format json
# ['osd_stats'][n]['snap_trim_queue_len'] => ceph_osd_snap_trim_queue_length{fsid="$fsid",osd="$osd"}

Metric('ceph_osd_snap_trim_queue_length', None, 'gauge')

# ceph osd dump --format json
# ['osds'][n]['up'] => ceph_osd_up{fsid="$fsid",osd="$osd"}

Metric('ceph_osd_up', 'Is the OSD up (1) or down (0)', 'gauge')

# Meta-metric, a sample gets inserted every time a placement group is encountered
# in the output.  Useful for Grafana template variables.
#
# ceph pg dump --format json
# ['pg_stats'][n] => ceph_pg{fsid="$fsid",pgid="$pgid")

Metric('ceph_pg', None, 'gauge')

# ceph pg dump --format json
# ['pg_stats_sum']['stat_sum']['num_objects'] => ceph_objects{fsid="$fsid",scope="cluster",type="total")
# ['pg_stats_sum']['stat_sum']['num_object_clones'] => ceph_objects{fsid="$fsid",scope="cluster",type="clones")
# ['pg_stats_sum']['stat_sum']['num_object_copies'] => ceph_objects{fsid="$fsid",scope="cluster",type="copies")
# ['pg_stats_sum']['stat_sum']['num_objects_missing_on_primary'] => ceph_objects{fsid="$fsid",scope="cluster",type="missing_on_primary")
# ['pg_stats_sum']['stat_sum']['num_objects_degraded'] => ceph_objects{fsid="$fsid",scope="cluster",type="degraded")
# ['pg_stats_sum']['stat_sum']['num_objects_misplaced'] => ceph_objects{fsid="$fsid",scope="cluster",type="misplaced")
# ['pg_stats_sum']['stat_sum']['num_objects_unfound'] => ceph_objects{fsid="$fsid",scope="cluster",type="unfound")
# ['pg_stats_sum']['stat_sum']['num_objects_dirty'] => ceph_objects{fsid="$fsid",scope="cluster",type="dirty")
# ['pg_stats'][n]['stat_sum']['num_objects'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="total")
# ['pg_stats'][n]['stat_sum']['num_object_clones'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="clones")
# ['pg_stats'][n]['stat_sum']['num_object_copies'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="copies")
# ['pg_stats'][n]['stat_sum']['num_objects_missing_on_primary'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="missing_on_primary")
# ['pg_stats'][n]['stat_sum']['num_objects_degraded'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="degraded")
# ['pg_stats'][n]['stat_sum']['num_objects_misplaced'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="misplaced")
# ['pg_stats'][n]['stat_sum']['num_objects_unfound'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="unfound")
# ['pg_stats'][n]['stat_sum']['num_objects_dirty'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="dirty")
#
# ceph df --format json
# ['pools'][n]['stats']['objects'] => ceph_objects{fsid="$fsid",scope="pool",pool="$id",name="$name",type="total"}

Metric('ceph_objects', None, 'gauge')

# ceph pg dump --format json
# ['pg_stats_sum']['stat_sum']['num_read_kb'] => ceph_operation_bytes{fsid="$fsid",scope="cluster",type="read")
# ['pg_stats_sum']['stat_sum']['num_write_kb'] => ceph_operation_bytes{fsid="$fsid",scope="cluster",type="write")
# ['pg_stats'][n]['stat_sum']['num_read_kb'] => ceph_operation_bytes{fsid="$fsid",scope="pg",pgid="$pgid",type="read")
# ['pg_stats'][n]['stat_sum']['num_write_kb'] => ceph_operation_bytes{fsid="$fsid",scope="pg",pgid="$pgid",type="write")

Metric('ceph_operation_bytes', None, 'counter')

# ceph pg dump --format json
# ['pg_stats_sum']['stat_sum']['num_read'] => ceph_operation_count{fsid="$fsid",scope="cluster",type="read")
# ['pg_stats_sum']['stat_sum']['num_write'] => ceph_operation_count{fsid="$fsid",scope="cluster",type="write")
# ['pg_stats'][n]['stat_sum']['num_read'] => ceph_operation_count{fsid="$fsid",scope="pg",pgid="$pgid",type="read")
# ['pg_stats'][n]['stat_sum']['num_write'] => ceph_operation_count{fsid="$fsid",scope="pg",pgid="$pgid",type="write")

Metric('ceph_operation_count', None, 'counter')

# ceph status --format json
# ['pgmap']['version'] => ceph_pgmap_version{fsid="$fsid"}

Metric('ceph_pgmap_version', None, 'gauge')

# ceph status --format json
# ['pgmap']['pgs_by_state'][n]['count'] => ceph_pgs_by_state{fsid="$fsid",state="$state_name"}

Metric('ceph_pgs_by_state', None, 'gauge')

Metric('ceph_pool', None, 'gauge')

# ceph osd pool stats --format json
# [n]['client_io_rate']['read_bytes_sec'] >= ceph_pool_bytes_second{fsid="$fsid",pool="$pool_id",name="$pool_name",type="read"}
# [n]['client_io_rate']['write_bytes_sec'] >= ceph_pool_bytes_second{fsid="$fsid",pool="$pool_id",name="$pool_name",type="write"}

Metric('ceph_pool_bytes_second', None, 'gauge')

# ceph osd pool stats --format json
# [n]['client_io_rate']['op_per_sec'] >= ceph_pool_operations_second{fsid="$fsid",pool="$pool_id",name="$pool_name"}

Metric('ceph_pool_operations_second', None, 'gauge')

# ceph osd dump --format json
# ['pools'][n]['pg_num'] => ceph_pool_pg_num{fsid="$fsid",pool="$pool_id",name="$pool_name"}

Metric('ceph_pool_pg_num', None, 'gauge')

# ceph osd dump --format json
# ['pools'][n]['pg_placement_num'] => ceph_pool_pg_num{fsid="$fsid",pool="$pool_id",name="$pool_name"}

Metric('ceph_pool_pgp_num', None, 'gauge')

# ceph osd dump --format json
# ['pools'][n]['size'] => ceph_pool_pg_num{fsid="$fsid",pool="$pool_id",name="$pool_name"}

Metric('ceph_pool_size', None, 'gauge')

parser = argparse.ArgumentParser()

parser.add_argument('--config', default='/etc/ceph/ceph.conf', help="Ceph config file location, default is `/etc/ceph/ceph.conf`")
parser.add_argument('--name', default='client.admin', help="Ceph client name used to authenticate to the Ceph cluster, default is `client.admin`")
parser.add_argument('--keyring', default='/etc/ceph/ceph.client.admin.keyring', help="Name of the file that contains key for authentication with the Ceph cluster, default is `/etc/ceph/ceph.client.admin.keyring`")
parser.add_argument('--endpoint', default='tcp:9999', help="Twisted server endpoint specifier, default is `tcp:9999`")
parser.add_argument('--executable', default='/usr/bin/ceph', help="Path to the Ceph command line client executable, default is `/usr/bin/ceph`")

options = parser.parse_args()

output = textFileLogObserver(sys.stdout)
globalLogBeginner.beginLoggingTo([output])

m = Main(options)
reactor.run()

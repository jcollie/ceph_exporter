# Prometheus Ceph Exporter

Export metrics from your [Ceph](http://ceph.com) clusters to your
[Prometheus](http://prometheus.io) monitoring system.

## Prerequisites

You'll need a working Ceph cluster, and a working Prometheus server.
Setup and installation of those is left as an exercise to the reader.

The server that you run this exporter needs to be configured to access
the Ceph cluster as a client.  If you can run `ceph status` and get a
reasonable response you are good to go. It _does not_ need to be run
on a server that is running other Ceph services, although there is
nothing preventing that.  The server running the exporter service will
also need to be accessible from the Prometheus server.

The exporter service is developed and tested using Python 3.  Running
the service with Python2 is untested.

## Installation

```bash
git clone https://github.com/jcollie/ceph_exporter.git
cd ceph_exporter
virtualenv --python=/usr/bin/python3 /opt/ceph_exporter
/opt/ceph_exporter/bin/pip install --requirement requirements.txt
cp ceph_exporter.py /opt/ceph_exporter/bin
cp ceph_exporter.service /etc/systemd/system
systemctl daemon-reload
systemctl enable ceph_exporter
systemctl start ceph_exporter
```

## Configuration

### Exporter

The Ceph exporter is configured using command line options:

```
usage: ceph_exporter.py [-h] [--config CONFIG] [--name NAME]
                        [--keyring KEYRING] [--endpoint ENDPOINT]
                        [--executable EXECUTABLE]

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Ceph config file location, default is
                        `/etc/ceph/ceph.conf`
  --name NAME           Ceph client name used to authenticate to the Ceph
                        cluster, default is `client.admin`
  --keyring KEYRING     Name of the file that contains key for authentication
                        with the Ceph cluster, default is
                        `/etc/ceph/ceph.client.admin.keyring`
  --endpoint ENDPOINT   Twisted server endpoint specifier, default is
                        `tcp:9999`
  --executable EXECUTABLE
                        Path to the Ceph command line client executable,
                        default is `/usr/bin/ceph`
```

Twisted server endpoint specifiers are described [here](https://twistedmatrix.com/documents/15.5.0/core/howto/endpoints.html#servers).

Multiple Ceph clusters could be monitored by copying the `systemd`
service file to a new name and pointing the exporter to different
configuration files.

### Prometheus

Add a job to your Promethus configuration that looks like the following:

```
scrape_configs:
  - job_name: 'ceph'
    scrape_interval: 30s
    scrape_timeout: 10s
    target_groups:
      - targets:
        - 'localhost:9999'
```

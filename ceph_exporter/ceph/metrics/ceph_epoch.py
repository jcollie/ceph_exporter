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

from ...prometheus import Metric

__all__ = ['ceph_epoch']

# ceph mds dump --format json
# ['epoch'] => ceph_epoch{fsid="$fsid",type="mds"}
#
# ceph quorum_status --format json
# ['monmap']['epoch'] => ceph_epoch{fsid="$fsid",type="mon"}
#
# ceph quorum_status --format json
# ['election_epoch'] => ceph_epoch{fsid="$fsid",type="mon_election"}

ceph_epoch = Metric('ceph_epoch', None, 'gauge')

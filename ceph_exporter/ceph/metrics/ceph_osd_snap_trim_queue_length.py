# -*- mode: python, coding: utf-8 -*-

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

__all__ = ['ceph_osd_snap_trim_queue_length']

# ceph pg dump --format json
# ['osd_stats'][n]['snap_trim_queue_len'] => ceph_osd_snap_trim_queue_length{fsid="$fsid",osd="$osd"}

ceph_osd_snap_trim_queue_length = Metric('ceph_osd_snap_trim_queue_length', None, 'gauge')

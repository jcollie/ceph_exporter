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

__all__ = ['ceph_objects']

# ceph df --format json
# ['pools'][n]['stats']['objects'] => ceph_objects{fsid="$fsid",scope="pool",pool="$id",name="$name",type="objects"}

# ceph pg dump --format json
# ['pg_stats_sum']['stat_sum']['num_objects'] => ceph_objects{fsid="$fsid",scope="cluster",type="objects")
# ['pg_stats_sum']['stat_sum']['num_object_clones'] => ceph_objects{fsid="$fsid",scope="cluster",type="clones")
# ['pg_stats_sum']['stat_sum']['num_object_copies'] => ceph_objects{fsid="$fsid",scope="cluster",type="copies")
# ['pg_stats_sum']['stat_sum']['num_objects_missing_on_primary'] => ceph_objects{fsid="$fsid",scope="cluster",type="missing_on_primary")
# ['pg_stats_sum']['stat_sum']['num_objects_degraded'] => ceph_objects{fsid="$fsid",scope="cluster",type="degraded")
# ['pg_stats_sum']['stat_sum']['num_objects_misplaced'] => ceph_objects{fsid="$fsid",scope="cluster",type="misplaced")
# ['pg_stats_sum']['stat_sum']['num_objects_unfound'] => ceph_objects{fsid="$fsid",scope="cluster",type="unfound")
# ['pg_stats_sum']['stat_sum']['num_objects_dirty'] => ceph_objects{fsid="$fsid",scope="cluster",type="dirty")
# ['pg_stats'][n]['stat_sum']['num_objects'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="objects")
# ['pg_stats'][n]['stat_sum']['num_object_clones'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="clones")
# ['pg_stats'][n]['stat_sum']['num_object_copies'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="copies")
# ['pg_stats'][n]['stat_sum']['num_objects_missing_on_primary'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="missing_on_primary")
# ['pg_stats'][n]['stat_sum']['num_objects_degraded'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="degraded")
# ['pg_stats'][n]['stat_sum']['num_objects_misplaced'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="misplaced")
# ['pg_stats'][n]['stat_sum']['num_objects_unfound'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="unfound")
# ['pg_stats'][n]['stat_sum']['num_objects_dirty'] => ceph_objects{fsid="$fsid",scope="pg",pgid="$pgid",type="dirty")

ceph_objects = Metric('ceph_objects', None, 'gauge')

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

from twisted.trial.unittest import TestCase

from ..prometheus import escape
from ..prometheus import Label

class EscapeTest(TestCase):
    def test_identity(self):
        result = escape('abdc')
        self.assertEqual(result, 'abdc')

    def test_backslash(self):
        result = escape('\\')
        self.assertEqual(result, '\\\\')

    def test_double_quote(self):
        result = escape('"')
        self.assertEqual(result, '\\"')

    def test_newline(self):
        result = escape('\n')
        self.assertEqual(result, '\\n')

class LabelTest(TestCase):
    def test_name(self):
        label = Label('a', 'b')
        self.assertEqual(label.name, 'a')

    def test_value(self):
        label = Label('a', 'b')
        self.assertEqual(label.value, 'b')

    def test_fmt(self):
        label = Label('a', 'b')
        self.assertEqual(label.fmt(), 'a="b"')

    def test_fmt(self):
        label = Label('a', 'b')
        self.assertEqual(label.fmt(), 'a="b"')

    def test_eq_1(self):
        label_1 = Label('a', 'b')
        label_2 = Label('a', 'b')
        self.assertTrue(label_1 == label_2)

    def test_eq_2(self):
        label_1 = Label('a', 'b')
        label_2 = Label('a', 'c')
        self.assertFalse(label_1 == label_2)

    def test_ne_1(self):
        label_1 = Label('a', 'b')
        label_2 = Label('a', 'c')
        self.assertTrue(label_1 != label_2)

    def test_ne_2(self):
        label_1 = Label('a', 'b')
        label_2 = Label('c', 'b')
        self.assertTrue(label_1 != label_2)

    def test_ne_3(self):
        label_1 = Label('a', 'b')
        label_2 = Label('a', 'b')
        self.assertFalse(label_1 != label_2)

    def test_in_1(self):
        self.assertIn(Label('a', 'b'), [Label('a', 'b')])

    def test_in_2(self):
        self.assertNotIn(Label('a', 'c'), [Label('a', 'b')])

    def test_in_3(self):
        self.assertNotIn(Label('c', 'b'), [Label('a', 'b')])

    def test_in_4(self):
        self.assertIn(Label('c', 'b'), [Label('a', 'b'), Label('c', 'b')])

    def test_in_5(self):
        self.assertNotIn(Label('c', 'd'), [Label('a', 'b'), Label('c', 'b')])

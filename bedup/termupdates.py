# bedup - Btrfs deduplication
# Copyright (C) 2012 Gabriel de Perthuis <g2p.code+bedup@gmail.com>
#
# This file is part of bedup.
#
# bedup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# bedup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bedup.  If not, see <http://www.gnu.org/licenses/>.

import collections
import string
import sys

from .time import monotonic_time

_formatter = string.Formatter()

# Yay VT100
CLEAR_LINE = '\r\x1b[K'
TTY_NOWRAP = '\x1b[?7l'
TTY_DOWRAP = '\x1b[?7h'
HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'


def format_duration(seconds):
    sec_format = '%05.2f'
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        sec_format = '%04.1f'
    hours, minutes = divmod(minutes, 60)
    if hours:
        sec_format = '%02d'
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    greatest_unit = (
        not weeks, not days, not hours, not minutes, not seconds, False
    ).index(False)
    rv = ''
    if weeks:
        rv += '%dW' % weeks
    if days:
        rv += '%dD' % days
    if rv:
        rv += ' '
    if greatest_unit <= 2:
        rv += '%02d:' % hours
    if greatest_unit <= 3:
        rv += '%02d:' % minutes
    rv += sec_format % seconds
    return rv


class TermTemplate(object):
    def __init__(self):
        self._template = None
        self._kws = {}
        self._kws_counter = collections.defaultdict(int)
        self._kws_totals = {}
        self._stream = sys.stdout
        self._isatty = self._stream.isatty()

    def update(self, **kwargs):
        self._kws.update(kwargs)
        for key in kwargs:
            self._kws_counter[key] += 1
        self._render(with_newline=False)

    def set_total(self, **kwargs):
        self._kws_totals.update(kwargs)
        self._render(with_newline=False)

    def format(self, template):
        if self._template is not None:
            self._render(with_newline=True)
        else:
            self._initial_time = monotonic_time()
        self._template = tuple(_formatter.parse(template))
        self._time = monotonic_time()
        self._render(with_newline=False)

    def _render(self, with_newline):
        if self._template is not None:
            self._stream.write(CLEAR_LINE + TTY_NOWRAP)
            for (
                literal_text, field_name, format_spec, conversion
            ) in self._template:
                self._stream.write(literal_text)
                if field_name:
                    if format_spec == '':
                        if field_name in ('elapsed', 'elapsed_total'):
                            format_spec = 'time'

                    if format_spec == '':
                        self._stream.write(self._kws.get(field_name, ''))
                    elif format_spec == 'total':
                        if field_name in self._kws_totals:
                            self._stream.write(
                                '%d' % self._kws_totals[field_name])
                        else:
                            self._stream.write('??')
                    elif format_spec == 'time':
                        if field_name == 'elapsed':
                            duration = monotonic_time() - self._time
                        elif field_name == 'elapsed_total':
                            duration = monotonic_time() - self._initial_time
                        else:
                            assert False, field_name
                        self._stream.write(format_duration(duration))
                    elif format_spec == 'truncate-left':
                        # XXX NotImplemented
                        self._stream.write(self._kws.get(field_name, ''))
                    elif format_spec == 'counter':
                        self._stream.write(
                            '%d' % self._kws_counter[field_name])
                    else:
                        assert False, format_spec
            if with_newline:
                self._stream.write('\n')
            else:
                self._stream.flush()
            # Just in case we get an inopportune SIGKILL,
            # write immediately and don't rely on finish: clauses.
            self._stream.write(TTY_DOWRAP)

    def notify(self, message):
        self._stream.write(CLEAR_LINE + message + '\n')
        self._render(with_newline=False)

    def finish(self):
        self._render(with_newline=True)
        self._stream.flush()
        self._stream = None


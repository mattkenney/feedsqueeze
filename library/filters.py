#
# This file is part of Feedsqueeze.
#
# Feedsqueeze is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Feedsqueeze is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Feedsqueeze.  If not, see <http://www.gnu.org/licenses/>.
#
from google.appengine.ext import webapp

import library.shared

register = webapp.template.create_template_register()

def decode_segment(value):
    return library.shared.decode_segment(value)

register.filter(decode_segment)

def encode_segment(value):
    return library.shared.encode_segment(value)

register.filter(encode_segment)

def format_IEEE1541(value):
    return library.shared.format_IEEE1541(value)

register.filter(format_IEEE1541)

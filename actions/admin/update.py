#
# Copyright 2011 Matt Kenney
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
import datetime

from google.appengine.api import taskqueue

import feeds
import library.shared

def action(handler):
    lst = []
    now = datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(60)
    for feed in feeds.Feed.all().filter('accessed > ', cutoff):
        updateUrl = '/admin/' + library.shared.encode_segment(feed.feedUrl) + '/update.html'
        lst.append('queueing ' + updateUrl)
        taskqueue.add(url=updateUrl)

    handler.context['log'] = lst

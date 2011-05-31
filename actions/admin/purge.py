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

from google.appengine.ext import db

import feeds

def action(handler):
    lst = []

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(60)

    count = 0;
    for stat in feeds.Status.all(keys_only=True).filter('created < ', cutoff):
        db.delete(stat)
        count = count + 1
    lst.append('Status purge ' + str(count))

    count = 0;
    for art in feeds.Article.all(keys_only=True).filter('created < ', cutoff):
        db.delete(art)
        count = count + 1
    lst.append('Article purge ' + str(count))

    for sub in feeds.Subscription.all():
        lst.append('recount ' + sub.user.email() + ' feed ' + sub.feedName);
        count = feeds.Status.all().filter('user = ', sub.user).filter('feedUrl = ', sub.feedUrl).filter('read = ', datetime.datetime.max).count()
        sub.counter = count
        sub.put()
        lst.append('count ' + str(count))

    handler.context['log'] = lst

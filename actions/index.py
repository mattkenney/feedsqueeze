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
import urllib

from google.appengine.api import users

import feeds
import library.shared

def action(handler):
    user = users.get_current_user()
    feeds.update_user_maybe(user)
    now = datetime.datetime.utcnow()
    handler.context['now'] = now

    feedFilter = handler.request.get('feed')
    showFilter = handler.request.get('show')

    #LATER: if empty redirect to welcome
    qs = ''
    if feedFilter:
        qs = '?feed=' + urllib.quote_plus(feedFilter)
    if showFilter:
        qs += '&' if qs else '?'
        qs += 'show=' + urllib.quote_plus(showFilter)
    handler.context['qs'] = qs

    if handler.method == 'POST':
        for name in handler.request.arguments():
            if name.startswith('hide.') or name.startswith('next.') or name.startswith('show.') or name.startswith('skip.'):
                read = None
                if name.startswith('hide.') or name.startswith('next.'):
                    read = now
                elif name.startswith('show.'):
                    read = datetime.datetime.max
                stat = feeds.set_status_read(user, name[5:], read)
                if stat and (name.startswith('next.') or name.startswith('skip.')):
                    query = feeds.Status.all().filter('user = ', user).order('articleDate').filter('articleDate > ', stat.articleDate)
                    if showFilter != 'all':
                        query.filter('read = ', datetime.datetime.max)
                    if feedFilter:
                        query.filter('feedName = ', feedFilter)
                    stat = query.get()
                    if stat:
                        path = '/read/' + library.shared.encode_segment(stat.articleUrl) + '/' + qs
                        handler.sendRedirect(path)
                        return True

    subs = feeds.Subscription.all().filter('user = ', user).order('feedName')
    handler.context['feeds'] = [ sub for sub in subs ]

    query = feeds.Status.all().filter('user = ', user).order('-articleDate')
    if not showFilter == 'all':
        query.filter('read = ', datetime.datetime.max)
    if feedFilter:
        query.filter('feedName = ', feedFilter)

    offset = handler.request.get_range('offset', 0)
    handler.context['articles'] = query.fetch(50, offset)

    if offset > 0:
        handler.context['newer'] = qs + ('&' if qs else '?') + 'offset=' + str(offset - 50)
    elif not showFilter == 'all' and len(handler.context['articles']) == 0:
        for sub in handler.context['feeds']:
            if not feedFilter or feedFilter == sub.feedName:
                sub.counter = 0
                sub.put()

    if len(handler.context['articles']) == 50:
        handler.context['older'] = qs + ('&' if qs else '?') + 'offset=' + str(offset + 50)

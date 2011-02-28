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
            if name.startswith('hide.') or name.startswith('next.') or name.startswith('show.'):
                read = datetime.datetime.max if name.startswith('show.') else now
                stat = feeds.set_status_read(user, name[5:], read)
                if stat and name.startswith('next.'):
                    query = feeds.Status.all().filter('user = ', user).order('articleDate').filter('articleDate >= ', stat.articleDate)
                    if not showFilter == all:
                        query.filter('read = ', datetime.datetime.max)
                    if feedFilter:
                        query.filter('feedName = ', feedFilter)
                    query.order('articleDate')
                    stat = query.get()
                    if stat:
                        path = '/read/' + library.shared.encode_segment(stat.articleUrl) + '/' + qs
                        handler.sendRedirect(path)
                        return True

    handler.context['feeds'] = feeds.get_feed_list(user)

    query = feeds.Status.all().filter('user = ', user).order('-articleDate')
    if not showFilter == 'all':
        query.filter('read = ', datetime.datetime.max)
    if feedFilter:
        query.filter('feedName = ', feedFilter)

    offset = handler.request.get_range('offset', 0)
    handler.context['articles'] = query.fetch(50, offset)

    if offset > 0:
        handler.context['newer'] = qs + ('&' if qs else '?') + 'offset=' + str(offset - 50)
    if len(handler.context['articles']) == 50:
        handler.context['older'] = qs + ('&' if qs else '?') + 'offset=' + str(offset + 50)

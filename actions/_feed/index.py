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
import logging
import urllib

from google.appengine.api import users

import feeds
import library.shared

def action(handler):
    sub = None
    user = users.get_current_user()
    feedUrl = handler.context['path_parameters'].get('feed', None)
    if feedUrl:
        sub = feeds.Subscription.all().filter('user = ', user).filter('feedUrl = ', feedUrl).get()
        if not sub:
            handler.sendError(404)
            return True
    if handler.method == 'POST':
        if handler.request.get('cancel'):
            handler.sendRedirect('../')#index.html')
            return True
        feedUrl = handler.request.get('feedUrl').strip()
        feedName = handler.request.get('feedName').strip()
        if not feedUrl:
            handler.context.setdefault('errors', []).append('Url is required')
        elif not feedName:
            handler.context.setdefault('errors', []).append('Name is required')
        else:
            #path = '../'
            if not sub:
                sub = feeds.Subscription()
            #    path = ''
            sub.user = users.get_current_user()
            sub.feedUrl = feedUrl
            sub.feedName = feedName
            sub.useGuid = True if handler.request.get('useGuid') else False
            sub.prefixRemove = handler.request.get('prefixRemove').strip()
            sub.prefixAdd = handler.request.get('prefixAdd').strip()
            sub.suffixRemove = handler.request.get('suffixRemove').strip()
            sub.suffixAdd = handler.request.get('suffixAdd').strip()
            sub.xpath = handler.request.get('xpath').strip()
            sub.extra = ','.join(handler.request.get_all('extra'))
            sub.put()
            feed = feeds.Feed.all().filter('feedUrl = ', feedUrl).get()
            if not feed:
                feed = feeds.Feed()
            feed.feedUrl = feedUrl
            feed.accessed = datetime.datetime.utcnow()
            feed.put()
            handler.sendRedirect('../')#path + library.shared.encode_segment(feedUrl) + '/')
            return True
    elif sub:
        handler.context['parameters']['feedUrl'] = sub.feedUrl
        handler.context['parameters']['feedName'] = sub.feedName
        handler.context['parameters']['useGuid'] = 'Y' if sub.useGuid else ''
        handler.context['parameters']['prefixRemove'] = sub.prefixRemove
        handler.context['parameters']['prefixAdd'] = sub.prefixAdd
        handler.context['parameters']['suffixRemove'] = sub.suffixRemove
        handler.context['parameters']['suffixAdd'] = sub.suffixAdd
        handler.context['parameters']['xpath'] = sub.xpath

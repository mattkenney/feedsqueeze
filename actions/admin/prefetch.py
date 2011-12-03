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

from google.appengine.api import users

import feeds

def action(handler):
    user = users.User(handler.request.get('user'))
    articleDate = datetime.datetime.strptime(handler.request.get('date'), "%Y-%m-%dT%H:%M:%S")
    feedFilter = handler.request.get('feed')
    showFilter = handler.request.get('show')
    query = feeds.Status.all().filter('user = ', user).order('articleDate').filter('articleDate > ', articleDate)
    if not showFilter == 'all':
        query.filter('read = ', datetime.datetime.max)
    if feedFilter:
        query.filter('feedName = ', feedFilter)
    stat = query.get()
    sub = feeds.Subscription.all().filter('user = ', user).filter('feedUrl = ', stat.feedUrl).get() if stat else None
    if sub:
        feeds.get_article_content(stat.articleUrl, stat.articleGuid, sub)

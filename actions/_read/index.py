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
from google.appengine.api import taskqueue
from google.appengine.api import users

import feeds

def action(handler):
    user = users.get_current_user()
    articleUrl = handler.context['path_parameters']['read']
    stat = feeds.Status.all().filter('user = ', user).filter('articleUrl = ', articleUrl).get()
    articleGuid = stat.articleGuid if stat else None
    sub = feeds.Subscription.all().filter('user = ', stat.user).filter('feedUrl = ', stat.feedUrl).get() if stat else None
    handler.context['article'] = stat
    handler.context['content'] = feeds.get_article_content(articleUrl, articleGuid, sub)

    # prefetch the next article
    if stat:
        params = dict()
        params['user'] = user.email()
        params['date'] = stat.articleDate.isoformat()
        feedFilter = handler.request.get('feed')
        if feedFilter:
            params['feed'] = feedFilter
        if handler.request.get('show') == 'all':
            params['show'] = 'all'
        taskqueue.add(url='/admin/prefetch.html', params=params)

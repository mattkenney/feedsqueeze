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
import calendar
import datetime
import logging

import feedparser

import feeds

def action(handler):
    lst = []
    now = datetime.datetime.utcnow()
    feedUrl = handler.context['path_parameters']['admin']
    lst.append('parsing ' + feedUrl)
    parser = feedparser.parse(feedUrl)#, agent='Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)')
    lst.append('status ' + str(parser.status))
#        if parser.status == 500:
#            lst.append(news.escape_xml(parser.data))
    for entry in parser.entries:
        link = entry.get('link', '')
        guid = entry.get('guid', link)
        articleUrl = link
        articleGuid = guid

#            if conf.has_option(section, 'regex') and conf.has_option(section, 'pattern'):
#                regex = conf.get(section, 'regex')
#                if conf.has_option(section, 'regexguid') and conf.getboolean(section, 'regexguid'):
#                    match = re.match(regex, guid)
#                    if match:
#                        articleUrl = match.expand(conf.get(section, 'pattern'))
#                    else:
#                        articleUrl = re.sub(regex, conf.get(section, 'pattern'), link)

        art = feeds.Article.all().filter('articleUrl = ', articleUrl).get()

        if art:
            if handler.request.get('purge'):
                for target in feeds.Article.all().filter('articleUrl = ', articleUrl):
                    logging.info('purging article %s', target.key())
                    target.delete()
            else:
                lst.append('skipping ' + articleUrl)
                continue

        art = feeds.Article()
        art.articleUrl = articleUrl
        art.articleGuid = articleGuid
        art.feedUrl = feedUrl
        art.articleName = entry.get('title', '')
        art.articleDate = now
        if entry.has_key('date_parsed') and entry.date_parsed:
            gmt = calendar.timegm(entry.date_parsed)
#                if conf.has_option(section, 'delta'):
#                    gmt += float(conf.get(section, 'delta'))
            art.articleDate = datetime.datetime.utcfromtimestamp(gmt)
        art.category = entry.get('category', '')
        art.created = now
        lst.append('saving ' + articleUrl)
        art.put()

    handler.context['log'] = lst

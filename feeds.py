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
import cgi
import datetime
import logging
import pprint
import traceback
import urllib
import urlparse
import xml.dom.minidom
from xml.sax.saxutils import escape

import BeautifulSoup
from google.appengine.api import memcache
from google.appengine.ext import db
import xpath

class Feed(db.Expando):
    feedUrl = db.LinkProperty()
    accessed = db.DateTimeProperty()
    updated = db.DateTimeProperty()

class Article(db.Expando):
    articleUrl = db.LinkProperty()
    articleGuid = db.StringProperty()
    feedUrl = db.LinkProperty()
    articleName = db.StringProperty()
    articleDate = db.DateTimeProperty()
    category = db.StringProperty()
    created = db.DateTimeProperty()

class Subscription(db.Expando):
    user = db.UserProperty()
    feedUrl = db.LinkProperty()
    feedName = db.StringProperty()
    useGuid = db.BooleanProperty()
    prefixRemove = db.StringProperty()
    prefixAdd = db.StringProperty()
    suffixRemove = db.StringProperty()
    suffixAdd = db.StringProperty()
    xpath = db.TextProperty()
    extra = db.StringProperty()
    updated = db.DateTimeProperty()
    counter = db.IntegerProperty()

class Status(db.Expando):
    user = db.UserProperty()
    feedName = db.StringProperty()
    feedUrl = db.LinkProperty()
    articleUrl = db.LinkProperty()
    articleGuid = db.StringProperty()
    articleName = db.StringProperty()
    articleDate = db.DateTimeProperty()
    category = db.StringProperty()
    created = db.DateTimeProperty()
    read = db.DateTimeProperty()

def get_article_content(stat):
    result = None

    # optionally modify URL before fetching the article
    url = stat.articleUrl
    sub = Subscription.all().filter('user = ', stat.user).filter('feedUrl = ', stat.feedUrl).get()
    if sub:
        if sub.useGuid:
            url = stat.articleGuid
        if (sub.prefixRemove or sub.prefixAdd) and url.startswith(sub.prefixRemove):
            url = sub.prefixAdd + url[len(sub.prefixRemove):]
        if (sub.suffixRemove or sub.suffixAdd) and url.endswith(sub.suffixRemove):
            url = url[:(len(url) - len(sub.suffixRemove))] + sub.suffixAdd

    try:
        # fetch the article
        f = urllib.urlopen(url)
        raw = f.read()
        url = f.geturl()
        #app engine getparam() does not work, at least in dev, so use cgi.parse_header instead
        #encoding = f.info().getparam('charset')
        #if not encoding:
        #    encoding = 'ISO-8859-1'
        base, params = cgi.parse_header(f.info().getheader('Content-Type'))
        encoding = params.get('charset', 'ISO-8859-1')
        f.close()

        # tag soup parse the article
        src = BeautifulSoup.BeautifulSoup(raw, fromEncoding=encoding, convertEntities='xhtml')

        # make relative URLs absolute so they work in our site
        for attr in [ 'action', 'background', 'cite', 'classid', 'codebase', 'data', 'href', 'longdesc', 'profile', 'src', 'usemap' ]:
            for tag in src.findAll(attrs={attr:True}):
                tag[attr] = urlparse.urljoin(url, tag[attr])

        # sanitize the article markup - remove script, style, and more
        # also convert to xml.dom.minidom so we can use xpath
        doc = soup2dom(src)

        # extract the parts we want
        parts = []
        if sub and sub.xpath:
            for path in sub.xpath.split('\n'):
                parts.extend(xpath.find(path, doc))
        else:
            parts.append(doc.documentElement)

        # remove class and id attributes so they won't conflict with ours
        # this makes the content smaller too
        # we do this after xpath so xpath can use class and id
        for tag in doc.getElementsByTagName('*'):
            if tag.hasAttribute('class'):
                tag.removeAttribute('class')
            if tag.hasAttribute('id'):
                tag.removeAttribute('id')
            if tag.nodeName == 'a' and tag.hasAttribute('href'):
                tag.setAttribute('target', '_blank')

        # convert to string
        result = ''
        for part in parts:
            result += '<div>'
            if part.nodeType == 2:
                result += part.nodeValue
            else:
                result += part.toxml('utf-8')
            result += '</div>'

    except Exception, err:
        logging.error("%s", pprint.pformat(err))
        if result:
            result += '\n'
        else:
            result = ''
        result += '<pre>\n'
        result += escape(url)
        result += '\n\n'
        result += escape(str(err))
        result += '\n</pre>\n<!--\n'
        result += escape(traceback.format_exc())
        result += '\n-->'

    return result

def increment_counter(key, amount, updated):
    obj = db.get(key)
    obj.counter = amount + (obj.counter if obj.counter else 0)
    if updated:
        obj.updated = updated
    obj.put()

def set_status_read(user, articleUrl, read):
    stat = Status.all().filter('user = ', user).filter('articleUrl = ', articleUrl).get()
    if stat:
        oldRead = stat.read
        if read != oldRead:
            stat.read = read
            stat.put()
            sub = Subscription.all().filter('user = ', user).filter('feedUrl = ', stat.feedUrl).get()
            if sub and oldRead == datetime.datetime.max:
                db.run_in_transaction(increment_counter, sub.key(), -1, None)
            elif sub and read == datetime.datetime.max:
                db.run_in_transaction(increment_counter, sub.key(), 1, None)
    return stat

def soup2dom(src, dst=None, doc=None):
    if doc and not dst:
        dst = doc.documentElement
    # elements have contents attribute we need to enumerate
    if hasattr(src, 'contents'):
        tag = src.name.lower()
        # silent element blacklist
        if tag in [ 'head', 'link', 'meta', 'script', 'style' ]:
            return doc
        # element blacklist with placeholder
        if tag in [ 'applet', 'embed', 'frame', 'object' ]:
            if dst:
                dst.appendChild(doc.createTextNode(' [' + tag + '] '))
            return doc
        attrs = dict((x[0].lower(), x[1]) for x in src.attrs)
        if doc:
            # create the element
            if tag == 'iframe':
                # blacklist iframe, but show link
                dst.appendChild(doc.createTextNode(' ['))
                a = doc.createElement('a')
                dst.appendChild(a)
                if 'src' in attrs:
                    a.setAttribute('href', attrs['src'])
                a.appendChild(doc.createTextNode('iframe'))
                dst.appendChild(doc.createTextNode('] '))
                return doc
            # we're going to use this inside another document
            # so we switch [body] to [div]
            if tag == 'body':
                tag = 'div'
            # create the element and descend
            elem = doc.createElement(tag);
            dst.appendChild(elem)
            dst = elem
        elif src.__class__.__name__ != 'BeautifulSoup':
            # when we get the first element create a [div] rooted document to build on
            doc = xml.dom.minidom.getDOMImplementation().createDocument(None, 'div', None)
            dst = doc.documentElement
            if tag == 'iframe':
                return soup2dom(src, dst, doc)
            if tag != 'html':
                elem = doc.createElement(tag)
                dst.appendChild(elem)
                dst = elem
        # we want href first according to Google pagespeed
        if 'href' in attrs:
            dst.setAttribute('href', attrs['href'])
        # then the rest of the attributes
        for key in sorted(attrs.keys()):
            # blacklist style and event handlers
            if key == 'href' or key == 'style' or key.startswith('on'):
                continue
            dst.setAttribute(key, attrs[key])
        # recurse into contents
        for content in src.contents:
            doc = soup2dom(content, dst, doc)
        # put a one space comment into empty elements we don't want minidom to minimize
        # which is any element not listed as empty in HTML5
        if dst and not dst.hasChildNodes() and not tag in [ 'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame', 'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr' ]:
            dst.appendChild(doc.createComment(' '))
    elif dst and src.__class__.__name__ == 'NavigableString':
        # append text; we don't do isinstance because we want to lose comments
        dst.appendChild(doc.createTextNode(src))
    return doc

def update_user(user):
    logging.info('updating articles for user %s' , user)
    now = datetime.datetime.utcnow()
    for sub in Subscription.all().filter('user = ', user).order('feedName'):
        count = 0
        for art in Article.all().filter('feedUrl = ', sub.feedUrl).filter('created > ', sub.updated):
            Status(
                user=user,
                feedName=sub.feedName,
                feedUrl=sub.feedUrl,
                articleUrl=art.articleUrl,
                articleGuid=art.articleGuid,
                articleName=art.articleName,
                articleDate=art.articleDate,
                category=art.category,
                created=art.created,
                read=datetime.datetime.max
                ).put()
            count = count + 1
        db.run_in_transaction(increment_counter, sub.key(), count, now)

def update_user_maybe(user):
    if not memcache.get(user.email()):
        update_user(user)
        memcache.add(user.email(), True, 600)

#!/usr/bin/env python
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
import logging
import mimetypes
import os
import re
import traceback
import urlparse

from google.appengine.dist import use_library

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
use_library('django', '1.2')

from django.conf import settings
settings.configure(INSTALLED_APPS=('app',))

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

import library.shared

class handler(webapp.RequestHandler):
    has_charset = re.compile('''((^text/)|(/ecmascript$)|(/(x-)?javascript$)|((/|\+)xml$))''')

    def get(self):
        if not hasattr(self, 'method'):
            self.method = 'GET'

        # virtual path segments
        virtual_segments = [x for x in self.request.path.split('/') if x]
        if self.request.path.endswith('/'):
            virtual_segments.append('index.html')

        # map virtual path to physical path and parameters
        physical_segments = []
        path_parameters = {}
        path_translated = None
        index = 1
        last = len(virtual_segments) - 1
        while True:
            if index < last:
                path_parameters[virtual_segments[index - 1]] = library.shared.decode_segment(virtual_segments[index])
                physical_segments.append('_' + virtual_segments[index - 1])
            else:
                physical_segments.append(virtual_segments[index - 1])
                if index == last:
                    physical_segments.append(virtual_segments[index])
                    path_translated = os.path.join(os.path.dirname(__file__), 'templates', *physical_segments)
                    if not os.path.isfile(path_translated):
                        path_parameters[virtual_segments[index - 1]] = library.shared.decode_segment(virtual_segments[index])
                        physical_segments.pop()
                        physical_segments.pop()
                        physical_segments.append('_' + virtual_segments[index - 1])
                break
            index = index + 2
        if not path_translated:
            path_translated = os.path.join(os.path.dirname(__file__), 'templates', *physical_segments)

        # directory paths must end with / so that relative paths will work
        if not self.request.path.endswith('/') and (os.path.isdir(path_translated) or ((len(virtual_segments) % 2) == 0 and not os.path.exists(path_translated))):
            # send redirect with the slash
            self.redirect(self.request.path + '/')
            return

        # page relative base template paths
        depth = len(physical_segments)
        base = [ '/'.join(physical_segments[0:i-1]) + '/_base.html' for i in range(0, depth) ]
        base[0:2] = [ '_baseroot.html', '_baseroot.html' ]
#        base[depth - 1] = '../_base.html';
#        for i in range(depth - 2, -1, -1):
#            base[i] = '../' + base[i + 1]

        # see if an action module exists for the page
        module = None
        action_segments = physical_segments[:]
        action_segments.insert(0, 'actions')
        (action_segments[-1], tmp) = os.path.splitext(action_segments[-1])
        action_path = os.path.join(os.path.dirname(__file__), *action_segments) + '.py'
        if os.path.exists(action_path):
            module = __import__('.'.join(action_segments))
            for segment in action_segments[1:]:
                module = getattr(module, segment)

        # action/template context dict
        self.context = {}
        self.context['handler'] = self
        self.context['parameters'] = dict( [ ( key, self.request.get(key) ) for key in self.request.arguments() ] )
        self.context['base'] = base
        self.context['virtual_segments'] = virtual_segments
        self.context['action_path'] = action_path
        self.context['path_parameters'] = path_parameters
        self.context['path_translated'] = path_translated
        #logging.info("context = %s", repr(self.context))

        # call the action method in the action module if it exists
        if module and module.action(self):
            # if the action returns True, then it does not need its template to be rendered
            pass
        elif os.path.exists(path_translated):
            # set the content-type header based on the file extension
            (content_type, encoding) = mimetypes.guess_type(path_translated)
            content_type = content_type if content_type else 'text/html'
            if handler.has_charset.match(content_type):
                content_type = content_type + '; charset=UTF-8';
            self.response.headers['Content-Type'] = content_type
            # render the page
            try:
                self.render(200, path_translated)
            except Exception:
                self.context['exception'] = traceback.format_exc();
                self.sendError(500)
        else:
            self.sendError(404)

    def post(self):
        self.method = 'POST'
        self.get()

    def render(self, status, path):
        self.context['context'] = repr(self.context)
        self.response.set_status(status)
        self.response.out.write(webapp.template.render(path, self.context))

    def sendError(self, status):
        path = os.path.join(os.path.dirname(__file__), 'templates', 'error.html')
        self.context['status_code'] = status
        self.context['status_message'] = webapp.Response.http_status_message(status)
        self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
        self.render(status, path)

    def sendRedirect(self, url):
        path = os.path.join(os.path.dirname(__file__), 'templates', 'redirect.html')
        location = urlparse.urljoin(self.request.url, url)
        self.context['location'] = location
        self.response.headers['Location'] = location
        self.render(302, path)

webapp.template.register_template_library('library.filters')

application = webapp.WSGIApplication([('/.*', handler)], debug=True)
def main():
    webapp.util.run_wsgi_app(application)

if __name__ == '__main__':
    main()

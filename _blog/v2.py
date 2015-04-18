# coding: utf-8
import jinja2
import os
import sys
from datetime import datetime
from time import time
import logging
import re
import codecs
from collections import defaultdict

from creole import CreoleParser, HtmlEmitter
import PyRSS2Gen


logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.DEBUG)

config = {
    'site_name': u'.live',
    'site_url': 'http://qs.github.io',
    'render_dir': '../',
    'source_path': '_data/',
    'date_format': "%d-%m-%Y %H:%M",
    'ctypes': {
        'index': {'name': u"Заметки", 'icon': '', 'url': '{year}/{month}/{day}/{slug}.html'},
        'book': {'name': u"Книги, что я прочитал", 'icon': '', 'url': '{ctype}/{year}/{month}/{slug}.html'},
        'event': {'name': u"События, что я посетил", 'icon': '', 'url': '{ctype}/{year}/{month}/{slug}.html'},
        'guide': {'name': u"Руководства, что я написал", 'icon': '', 'url': '{ctype}/{slug}.html'},
        'spec': {'name': u"Spec pages", 'icon': '', 'url': '{slug}.html'},
    }
}

transl = {u'а': u'a', u'б': u'b', u'в': u'v', u'г': u'g', u'д': u'd', 
          u'е': u'e', u'ё': u'e', u'ж': u'zh', u'з': u'z', u'и': u'i', 
          u'й': u'y', u'к': u'k', u'л': u'l', u'м': u'm', u'н': u'n', 
          u'о': u'o', u'п': u'p', u'р': u'r', u'с': u's', u'т': u't', 
          u'у': u'u', u'ф': u'f', u'х': u'h', u'ц': u'ts', u'ч': u'ch', 
          u'ш': u'sh', u'щ': u'sch', u'ъ': u'', u'ы': u'y', u'ь': u'', 
          u'э': u'e', u'ю': u'yu', u'я': u'ya',}

def gen_slug(title):
    title = re.sub(ur"([^а-яa-z0-9]+)", u'-', title.lower(), re.UNICODE)
    for k,v in transl.items():
        title = title.replace(k, v)
    title = re.sub(ur"(^-|-$)", u'', title)
    return title


class Page:
    def __init__(self, fname, content):
        self.dt, self.ctype, self.slug = fname.split('__')
        self.dt = datetime.fromtimestamp(int(self.dt))
        self.content = content
        self.tags, content = self._separate_tags(content)
        self.title, content = self._separate_title(content)
        self.content_html = self._render_html(content)
        self.url_dict = {
            'slug': self.slug,
            'day': self.dt.day, 
            'month': self.dt.month,
            'year': self.dt.year,
            'ctype': self.ctype,
        }
        self.url = config['ctypes'][self.ctype]['url'].format(**self.url_dict)

    def _separate_tags(self, content):
        tags = re.findall("tags: (.*)\n", content)
        tags = [tag for tag in tags[0].split(", ") if tag] if tags else []
        content = re.sub("tags: (.*)\n", '', content)
        return tags, content

    def _separate_title(self, content):
        title = re.findall("title: (.*)\n", content)[0]
        content = re.sub("title: (.*)\n", '', content)
        return title, content

    def _render_html(self, content):
        document = CreoleParser(content).parse()
        page = HtmlEmitter(document).emit()
        return page


class Staticbl:
    def __init__(self, config):
        self.config = config
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

    def _render_file(self, fname, tpl_file, tvars={}):
        path = config['render_dir'] + fname
        dirpath, fname = os.path.split(path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        with codecs.open(path, 'w', 'utf-8') as outfile:
            tpl = self.jinja_env.get_template('templates/' + tpl_file + '.html')
            tvars['site_name'] = config['site_name']
            html_page = tpl.render(tvars)
            outfile.write(html_page)

    def build(self):
        # pages
        pages = defaultdict(lambda: [])
        tags = defaultdict(lambda: [])
        ctypes = defaultdict(lambda: [])
        for fname in os.listdir(config['source_path']):
            fpath = config['source_path'] + fname
            if os.path.isfile(fpath):
                with codecs.open(fpath, 'r', 'utf-8') as f:
                    page = Page(fname, f.read())
                    for tag in page.tags:
                        tags[tag].append(page)
                    ctypes[page.ctype].append(page)
                    self._render_file(page.url, 'page', {'page': page, 'ctype': page.ctype})
                    pages[page.ctype].append(page)
        # index
        for ctype in pages:
            cpages = sorted(pages[ctype], key=lambda x: x.dt, reverse=True)
            tvars = {
                'pages': cpages, 
                'title': config['ctypes'][ctype]['name'], 
                'ctype': ctype
            }
            self._render_file('{0}.html'.format(ctype), 'index', tvars)
        # tags
        for tag in tags:
            cpages = sorted(tags[tag], key=lambda x: x.dt, reverse=True)
            tvars = {
                'pages': cpages,
                'title': u"Content about '{0}'".format(tag), 
            }
            self._render_file('tag/{0}.html'.format(tag), 'index', tvars)
        tvars = {
            'title': u"List of tags",
            'cnt_tags': sorted([(tag, len(tags[tag])) for tag in tags], key=lambda x: x[1], reverse=True)
        }
        self._render_file('tag.html', 'tag', tvars)

    def post(self, ctype, title):
        slug = gen_slug(title)
        dt = int(time())
        path = config['source_path'] + '{0}__{1}__{2}'.format(dt, ctype, slug)
        with codecs.open(path, 'w', 'utf-8') as f:
            init_tags = 'draft'
            f.write(u"title: {0}\ntags: {1}".format(title, init_tags))
            print 'Post created, for editing try:\nsubl {0}'.format(path)

    def serve(self):
        """ run web-server to test static site """
        import SimpleHTTPServer
        import BaseHTTPServer
        os.chdir(config["render_dir"])
        server_addr = ('localhost', 8000)
        request_handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        httpd = BaseHTTPServer.HTTPServer (server_addr, request_handler)
        httpd.serve_forever()


if __name__ == "__main__":
    action = sys.argv[1]
    logging.info( u'Staticbl: %s' % action )
    st = Staticbl(config)
    if action == 'build':
        st.build()
    if action == 'serve':
        st.serve()
    elif action == 'post':
        ctype, title = sys.argv[2], unicode(sys.argv[3], 'utf-8')
        st.post(ctype, title)
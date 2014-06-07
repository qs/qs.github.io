# coding: utf-8
import jinja2
import os
import sys
from datetime import datetime
import logging
import re
import codecs

from creole import CreoleParser
from creole import HtmlEmitter

logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.DEBUG)

data = """
==== Helloo ====

* ff
* fff

|= |= fff |= ddd |
| s | aaa | fe |
| a | ddd | www |

tpl_file = 'index'
tpl = jinja_environment.get_template('templates/' + tpl_file + '.html')
f = open('page.html', 'w')
html_page = tpl.render({'lol': 'ddddd', 'page': page})
f.write(html_page)
f.close()

"""


settings = {
    'site_name': 'qs.github.io',
    'render_dir': '../',
    'header_links': {
        '/': u'blog',
        '/about/': u'about',
        '/tags/': u'tags',
    }, 
    'source_path': '_data/',
    'date_format': "%d.%m.%Y %H:%M",
}

transl = {u'а': u'a', u'б': u'b', u'в': u'v', u'г': u'g', u'д': u'd', u'е': u'e', u'ё': u'e', u'ж': u'zh', u'з': u'z', u'и': u'i', u'й': u'y', u'к': u'k', u'л': u'l', u'м': u'm', u'н': u'n', u'о': u'o', u'п': u'p', u'р': u'r', u'с': u's', u'т': u't', u'у': u'u', u'ф': u'f', u'х': u'h', u'ц': u'ts', u'ч': u'ch', u'ш': u'sh', u'щ': u'sch', u'ъ': u'', u'ы': u'y', u'ь': u'', u'э': u'e', u'ю': u'yu', u'я': u'ya',}

def gen_slug(title):
    title = re.sub(ur"([^а-я]+)", u'-', title.lower(), re.UNICODE)
    for k,v in transl.items():
        ns = ns.replace(k, v)
    title = re.sub(ur"(^-|-$)", u'', ns)


class Page:
    def __init__(self, src_fname, content):
        self.content = content
        self.path = src_fname.replace('__', '/') + '.html'
        self.fname = src_fname.split('__')[-1]
        self.meta = {'title': u'', 'tags': []}
        self.parse_meta_data()

    def is_blog_page(self):
        if re.match(ur"[0-9]{2}\-[0-9]{2}\-[0-9]{4}/.*", self.path):
            return True
        else:
            return False

    def parse_meta_data(self):
        meta_funcs = {
            'title': lambda x: x,
            'tags': lambda x: x.split(', '),
            'date': lambda x: datetime.strptime(x, settings['date_format']),
        }
        for name, func_val in meta_funcs.items():
            self._set_meta_string(name, func_val)

    def _set_meta_string(self, name, func_val):
        name_str = re.findall(ur"(%s\: .*\n)" % name, self.content)
        logging.debug( u'Meta string (%s) detected: %s' % (name, name_str))
        if name_str:
            name_re = re.search(ur'%s: (.*)\n' % name, name_str[0])
            self.meta[name] = func_val(name_re.group(1))
            self.content = self.content.replace(name_re.group(0), '', 1)

    def render_html(self):
        document = CreoleParser(self.content).parse()
        page = HtmlEmitter(document).emit()
        return page


class Staticbl:
    def __init__(self):
        self.config = None
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

    def _render_file(self, path, tpl_file, tvars={}):
        """ get tvals with generated html-page and template name, 
            makes file in the path"""
        path = settings['render_dir'] + path
        dirpath, fname = os.path.split(path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        with codecs.open(path, 'w', 'utf-8') as outfile:
            tpl = self.jinja_env.get_template('templates/' + tpl_file + '.html')
            tvars['header_links'] = settings['header_links']
            tvars['site_name'] = settings['site_name']
            tvars['date_format'] = settings['date_format']
            html_page = tpl.render(tvars)
            outfile.write(html_page)

    def _render_page(self, content):
        """ generate and return html-page from wiki content and meta-data"""
        pass

    def build(self):
        """ find all _data and generate html files 
            for site to be done"""
        tags = {} # for tag pages
        # posts
        pages = [Page(src_fname=i[:-5], content=codecs.open(settings['source_path'] + i, 'r', 'utf-8').read()) \
                for i in os.listdir(settings['source_path']) \
                if os.path.isfile(settings['source_path'] + i)]
        logging.info( u'Total pages: %s' % len(pages) )
        for p in pages:
            tvars = p.meta
            tvars['content'] = p.render_html()
            logging.debug( u'Generating page: %s ' % p.path )
            self._render_file(p.path, 'page', tvars)
            # also aggreagate tags
            for t in p.meta['tags']:
                if p.is_blog_page():
                    if t in tags:
                        tags[t].append(p)
                    else:
                        tags[t] = [p, ]
        # post list (main)
        logging.debug( u'Generating index page')
        self._render_file('index.html', 'index', {'pages': [p for p in pages if p.is_blog_page()]})
        # tag filters
        for tag, tag_pages in tags.items():
            logging.debug( u'Generating tag page: %s with %s pages' % (tag, len(tag_pages)) )
            self._render_file('tag/%s.html' % tag, 'tag', {'pages': tag_pages, 'tag': tag})
        # rss

    def post(self, title):
        """ create a new file with template content 
            insertin into template normal title, 
            filename is a date__slug-title
            and print command to open it or open"""
        pass

    def serve(self):
        """ run web-server to test static site """
        pass

if __name__ == "__main__":
    action = sys.argv[1]
    logging.info( u'Staticbl: %s' % action )
    st = Staticbl()
    if action == 'build':
        st.build()
    if action == 'serve':
        st.serve()
    elif action == 'post':
        st.post(sys.argv[2])
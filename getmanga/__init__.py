# -*- coding: utf8 -*-
# Copyright (c) 2010-2015, Jamaludin Ahmad
# Released subject to the MIT License.
# Please see http://en.wikipedia.org/wiki/MIT_License

from __future__ import division

import os
import re
import sys

if sys.version_info >= (3, 0, 0):
    from queue import Queue
else:
    from Queue import Queue

from collections import namedtuple
from threading import Semaphore, Thread
from zipfile import ZIP_DEFLATED, ZipFile

import requests
from lxml import html


Chapter = namedtuple('Chapter', 'number name uri volume')
Page = namedtuple('Page', 'name uri')

class MangaException(Exception):
    """Exception class for manga"""
    pass


class GetManga(object):
    def __init__(self, site, title):
        self.concurrency = 4
        self.path = '.'

        self.title = title
        self.manga = SITES[site](title)

    @property
    def chapters(self):
        """Show a list of available chapters"""
        return self.manga.chapters

    @property
    def latest(self):
        """Show last available chapter"""
        return self.manga.chapters[-1]

    def checkExists(self, chapter):
        """Checks if manga chapter has already been downloaded"""
        path = os.path.expanduser(self.path)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except OSError as msg:
                raise MangaException(msg)

        cbz_name = chapter.name + os.path.extsep + 'cbz'
        cbz_file = os.path.join(path, cbz_name)

        if os.path.isfile(cbz_file):
            return True
        else:
            return False

    def numNewChapters(self):
        """Returns the number of new chapters available (past those that have been downloaded)"""
        counter = 0
        for chapter in self.chapters:
            counter += 1
            if self.checkExists(chapter):
                counter = 0
        return counter

    def getNewChapters(self):
        """Downloads all new chapters available (past those that have been downloaded)"""
        newi = 0
        i = 0
        for chapter in self.chapters:
            if self.checkExists(chapter):
                newi = i+1
            i += 1
        for chapter in self.chapters[newi:]:
            self.get(chapter)
        if len(self.chapters[newi:]) == 0:
            sys.stdout.write("No new chapters for {0}.\n".format(self.title))

    def get(self, chapter):
        """Downloads manga chapter as cbz archive"""
        path = os.path.expanduser(self.path)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except OSError as msg:
                raise MangaException(msg)

        cbz_name = chapter.name + os.path.extsep + 'cbz'
        cbz_file = os.path.join(path, cbz_name)

        if os.path.isfile(cbz_file):
            sys.stdout.write("file {0} exist, skipped download\n".format(cbz_name))
            return

        cbz_tmp = '{0}.tmp'.format(cbz_file)

        try:
            cbz = ZipFile(cbz_tmp, mode='w', compression=ZIP_DEFLATED)
        except IOError as msg:
            raise MangaException(msg)

        sys.stdout.write("downloading {0} {1} to {2}\n".format(self.title, chapter.number,cbz_name))

        pages = self.manga.get_pages(chapter.uri)
        #pages = [pages[0]]# debug
        progress(0, len(pages))

        ## debug
        #print()
        ##print(chapter.uri)
        #print(pages[0])
        #print()
        #raise MangaException("Debug bail")

        threads = []
        semaphore = Semaphore(self.concurrency)
        queue = Queue()
        for page in pages:
            thread = Thread(target=self._get_image, args=(semaphore, queue, page))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        try:
            for thread in threads:
                thread.join()
                name, image = queue.get()
                if not name:
                    raise MangaException(image)
                cbz.writestr(name, image)
                progress(len(cbz.filelist), len(pages))
        except Exception as msg:
            cbz.close()
            os.remove(cbz_tmp)
            raise MangaException(msg)
        else:
            cbz.close()
            os.rename(cbz_tmp, cbz_file)

    def _get_image(self, semaphore, queue, page):
        """Downloads page images inside a thread"""
        try:
            semaphore.acquire()
            uri = self.manga.get_image_uri(page.uri)
            # mangahere & mangatown have token as trailing query on it's image url
            query = uri.find('?')
            if query != -1:
                image_ext = uri[:query].split('.')[-1]
            else:
                image_ext = uri.split('.')[-1]

            # if the image extension is weird, just assume it should be jpg
            if image_ext.lower() not in ['png','jpeg','jpg','tif','tiff','pdf','gif','webp','bmp']:
                image_ext = 'jpg'

            # reformat all numbers, e.g. 1->001, 10-> 010 so that they'll be sorted properly
            numrex = re.compile("([0-9]+)")
            new_page_name = re.sub(numrex, lambda x: x.group(1).zfill(3), page.name)

            name = new_page_name + os.path.extsep + image_ext
            image = self.manga.download(uri, page.uri)
        except MangaException as msg:
            queue.put((None, msg))
        else:
            queue.put((name, image))
        finally:
            semaphore.release()


class MangaSite(object):
    site_uri = None
    # all but mangareader and cartoonmad use descending chapter list
    descending_list = True

    _chapters_css = None
    _pages_css = None
    _image_css = None


    _headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'} 

    def __init__(self, title):
        self.input_title = title.strip()
        self.session = requests.Session()

    @property
    def title(self):
        """Returns the right manga title from user input"""
        # combination of alphanumeric and underscore only is the most used format.
        # used by: mangafox, mangastream, mangahere, mangatown

        # all sites EXCEPT senmanga only use lowercase title on their urls.
        self.input_title = self.input_title.lower()
        return re.sub(r'[^a-z0-9]+', '_', re.sub(r'^[^a-z0-9]+|[^a-z0-9]+$', '', self.input_title))

    @property
    def title_uri(self):
        """Returns the index page's url of manga title"""
        # this is the most common url for manga title
        # used by: mangafox, mangastream, mangahere, mangatown, mangalion
        return "{0}/manga/{1}/".format(self.site_uri, self.title)

    @property
    def chapters(self):
        """Returns available chapters"""
        content = self.session.get(self.title_uri, headers=self._headers).text
        doc = html.fromstring(content)
        _chapters = doc.cssselect(self._chapters_css)
        if self.descending_list:
            _chapters = reversed(_chapters)

        chapters = []
        for _chapter in _chapters:
            number = self._get_chapter_number(_chapter)
            location = _chapter.get('href')
            volume = self._get_chapter_volume(location)
            name = self._get_chapter_name(str(number), volume, location)
            uri = self._get_chapter_uri(location)

            if (number != None):
                chapters.append(Chapter(number, name, uri, volume))

        if not chapters:
            raise MangaException("There is no chapter available.")
        return chapters

    def get_pages(self, chapter_uri):
        """Returns a list of available pages of a chapter"""
        content = self.session.get(chapter_uri, headers=self._headers).text
        doc = html.fromstring(content)
        _pages = doc.cssselect(self._pages_css)
        pages = []
        for _page in _pages:
            name = self._get_page_name(_page.text)
            #print("Name: ",name)
            if not name:
                continue
            uri = self._get_page_uri(chapter_uri, name, _page)
            #print("URI: ",uri)
            #print()
            pages.append(Page(name, uri))
        return pages

    def get_image_uri(self, page_uri):
        """Returns uri of image from a chapter page"""
        content = self.session.get(page_uri, headers=self._headers).text
        doc = html.fromstring(content)
        image_uri = doc.cssselect(self._image_css)[0].get('src')
        image_uri = image_uri.strip()
        # use http for mangastream's relative url
        if image_uri.startswith('//'):
            return "http:{0}".format(image_uri)
        elif image_uri.startswith('/'): # fix other relative paths
            return "{0}{1}".format(self.site_uri, image_uri)
        return image_uri

    def download(self, image_uri, page_uri):
        # update the session to list the current page as the referrer
        self.session.headers.update(self._headers)
        self.session.headers.update({'referer': page_uri})
        #print image_uri
        #print self.session.headers
        #raise MangaException("Debug exit")

        content = None
        retry = 0
        while retry < 5:
            try:
                resp = self.session.get(image_uri)
                if str(resp.status_code).startswith('4'):
                    retry = 5
                elif str(resp.status_code).startswith('5'):
                    retry += 1
                elif ('content-length' in resp.headers) and (len(resp.content) != int(resp.headers['content-length'])):
                    retry += 1
                else:
                    retry = 5
                    content = resp.content
            except Exception:
                retry += 1
        if not content:
            raise MangaException("Failed to retrieve {0}".format(image_uri))
        return content

    @staticmethod
    def _get_chapter_number(chapter):
        """Returns chapter's number from a chapter's HtmlElement"""
        # the most common one is getting the last word from a href section.
        # used by: animea, mangafox, mangahere, mangareader, mangatown, mangalion
        return chapter.text.strip().split(' ')[-1]

    def _get_chapter_volume(self, location):
        """Returns chapter's volume number from a chapter's URL"""
        # the most common one is getting a section like /v[0-9.]+/c[0-9]*
        # used by: mangafox, mangahere, mangatown, mangastream
        volume = None
        vrex = re.compile("/(v[0-9.]+)/c[0-9]")
        vsearch = vrex.search(location)
        if vsearch:
            volume = vsearch.group(1)
        return volume

    def _get_chapter_name(self, number, volume, location):
        """Returns the appropriate name for the chapter for achive name"""
        # deal with decimals. we want 6 -> 006 and 2.3 -> 002.3
        try:
            if int(float(number)) == float(number):
                # it's an integer
                numstr = number.zfill(3)
            else:
                decimal = float(number) - int(float(number))
                decstr = str(decimal)[1:]
                numstr = str(int(float(number))).zfill(3) + decstr
        except ValueError:
            numstr = number.zfill(3)

        clean_title = self.title.lower().replace("-","_")
        if (volume == None):
            return "{0}_c{1}".format(clean_title, numstr)
        else:
            # include volume if available
            return "{0}_{1}_c{2}".format(clean_title, volume, numstr)

    def _get_chapter_uri(self, location):
        """Returns absolute url of chapter's page from location"""
        # some sites already use absolute url on their chapter list, some have relative urls.
        if location.startswith('http://'):
            return location
        else:
            return "{0}{1}".format(self.site_uri, location)

    @staticmethod
    def _get_page_name(page_text):
        """Returns page name from text available or None if it's not a valid page"""
        # typical name: page's number, double page (eg. 10-11), or credits
        # normally page listing from each chapter only has it's name in it, but..
        # - mangafox has comment section
        return page_text

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # every sites use different format for their urls, this is a sample.
        # used by: mangahere, mangatown
        return "{0}{1}.html".format(chapter_uri, page_name)


class MangaHere(MangaSite):
    """class for mangahere site"""
    site_uri = "http://www.mangahere.co"

    _chapters_css = "div.detail_list ul li a"
    _pages_css = "section.readpage_top div.go_page select option"
    _image_css = "img#image"


class MangaTown(MangaSite):
    """class for mangatown site"""
    site_uri = "http://www.mangatown.com"

    _chapters_css = "div.chapter_content ul.chapter_list li a"
    _pages_css = "div.manga_read_footer div.page_select select option"
    _image_css = "img#image"


class MangaFox(MangaSite):
    """class for mangafox site"""
    # their slogan should be: "we are not the best, but we are the first"
    site_uri = "http://mangafox.me"

    _chapters_css = "a.tips"
    _pages_css = "#top_bar option"
    _image_css = "img#image"

    @staticmethod
    def _get_page_name(page_text):
        """Returns page name from text available"""
        # mangafox has comments section in it's page listing
        if page_text == 'Comments':
            return None
        return page_text

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # chapter's page already has the first page's name in it.
        return re.sub(r'[0-9]+.html$', "{0}.html".format(page_name), chapter_uri)

class MangaLion(MangaSite):
    """class for mangalion site"""
    site_uri = "http://www.mangalion.com"

    _chapters_css = "ul.basic-list li a.ch-name"
    _pages_css = "div.chapter-title #page_select option"
    _image_css = "div.chapter-container a img"

    @property
    def title(self):
        """Returns the right manga title from user input"""
        self.input_title = self.input_title.lower()
        return re.sub(r'[^a-z0-9]+', '-', self.input_title)

    @staticmethod
    def _get_page_name(page_text):
        """Returns page name from text available or None if it's not a valid page"""
        return re.sub("\s*","",page_text)

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # chapter's page already has the first page's name in it.
        if (page_name == "1"):
            return chapter_uri
        else:
            return chapter_uri + "/" + "{0}".format(page_name)

# NOTE: must enter title as, e.g. "grand blue:3899", where last numbers will be used for the uri
class CartoonMad(MangaSite):
    """class for cartoonmad site"""
    site_uri = "http://www.cartoonmad.com"
    descending_list = False

    _chapters_css = "fieldset[id|=info] td a"
    _pages_css = "tr td center li select option[value]"
    _image_css = "td[align|=center] table td[align|=center] a img[oncontextmenu]"

    @property
    def title_uri(self):
        """Returns the index page's url of manga title"""
        title_id = self.input_title.split(":")[-1].strip()
        return "{0}/comic/{1}.html".format(self.site_uri, title_id)

    @property
    def title(self):
        """Returns the right manga title from user input"""
        self.input_title = self.input_title.lower()
        lhs_title = (":".join(self.input_title.split(":")[0:-1])).strip()
        return re.sub(r'[^a-z0-9]+', '_', lhs_title)

    @staticmethod
    def _get_chapter_number(chapter):
        """Returns chapter's number from a chapter's HtmlElement"""
        # idea: match the last number in the string
        last_num_regex = re.compile('\\b([0-9]+)\\b[^0-9]*$')
        last_num_search = last_num_regex.search(chapter.text.strip())
        if (last_num_search):
            return last_num_search.group(1)
        else:
            return None

    @staticmethod
    def _get_page_name(page_text):
        """Returns page name from text available or None if it's not a valid page"""
        last_num_regex = re.compile('\\b([0-9]+)\\b[^0-9]*$')
        last_num_search = last_num_regex.search(page_text.strip())
        if (last_num_search):
            return last_num_search.group(1)
        else:
            return None

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # chapter's page already has the first page's name in it.
        relative_page_uri = page.get('value')
        return "http://www.cartoonmad.com/comic/{0}".format(relative_page_uri)


class RawMangaUpdate(MangaSite):
    """class for rawmangaupdate site"""
    # site for raw manga
    site_uri = "http://rawmangaupdate.com"

    _chapters_css = "ul.chapters h5 a"
    #_pages_css = "ul.dropdown-menu li a span" # what comes up when you allow javascript
    _pages_css = "div[class|=page-nav] select[id|=page-list] option"
    _image_css = "div[id|=ppp] img"

    @property
    def title(self):
        """Returns the right manga title from user input"""
        self.input_title = self.input_title.lower()
        return re.sub(r'[^a-zA-Z0-9]+', '-', self.input_title)

    @staticmethod
    def _get_chapter_number(chapter):
        """Returns chapter's number from a chapter's HtmlElement"""

        # idea: match the last number in the string
        last_num_regex = re.compile('\\b([0-9]+)\\b[^0-9]*$')
        last_num_search = last_num_regex.search(chapter.text.strip())
        if (last_num_search):
            return last_num_search.group(1)
        else:
            return None

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # chapter's page already has the first page's name in it.
        return chapter_uri + "/" + "{0}".format(page_name)

class SenManga(MangaSite):
    # working until the image scraping bit...

    """class for senmanga site"""
    # site for raw manga
    site_uri = "http://raw.senmanga.com"

    _chapters_css = "div #post tr td a"
    _pages_css = "div select[name|=page] option"
    _image_css = "img[id|=picture]"

    @property
    def title_uri(self):
        """Returns the index page's url of manga title"""
        return "{0}/{1}/".format(self.site_uri, self.title)

    @property
    def title(self):
        """Returns the right manga title from user input"""
        # IMPORTANT: SenManga requires correct capitalization
        return re.sub(r'[^_a-zA-Z0-9]+', '-', self.input_title)

    # override _get_chapter_uri
    def _get_chapter_uri(self, location):
        """Returns absolute url of chapter's page from location"""
        # some sites already use absolute url on their chapter list, some have relative urls.
        this_location = None
        if location.startswith('http://'):
            this_location = location
        else:
            this_location = "{0}{1}".format(self.site_uri, location)
        
        # use the version of the url without page number 1 appended
        if this_location[-2:] == '/1':
            this_location = this_location[:-2]

        return this_location


    @staticmethod
    def _get_chapter_number(chapter):
        """Returns chapter's number from a chapter's HtmlElement"""

        href_regex = re.compile('a href="[^"]*/([0-9]+)/1?"')
        href_search = href_regex.search(html.tostring(chapter))
        if (href_search):
                return href_search.group(1)
        else: 
            # if that fails, match the last number in the string 
            last_num_regex = re.compile('\\b([0-9]+)\\b[^0-9]*$')
            last_num_search = last_num_regex.search(chapter.text.strip())
            if (last_num_search):
                return last_num_search.group(1)
            else:
                return None

    @staticmethod
    def _get_page_name(page_text):
        """Returns page name from text available or None if it's not a valid page"""
        return re.sub("\s*#\s*","",page_text)

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        # chapter's page already has the first page's name in it.
        return chapter_uri + "/" + "{0}".format(page_name)

class MangaStream(MangaSite):
    """class for mangastream site"""
    # a real scanlation group, not distro sites like the others here,
    # currently doesn't utilize _get_page_name and override get_pages instead.
    site_uri = "http://mangastream.com"

    _chapters_css = "td a"
    _pages_css = "div.btn-group ul.dropdown-menu li a"
    _image_css = "img#manga-page"

    def get_pages(self, chapter_uri):
        """Returns a list of available pages of a chapter"""
        content = self.session.get(chapter_uri, headers=self._headers).text
        doc = html.fromstring(content)
        _pages = doc.cssselect(self._pages_css)
        for _page in _pages:
            page_text = _page.text
            if not page_text:
                continue
            if 'Last Page' in page_text:
                last_page = re.search('[0-9]+', page_text).group(0)

        pages = []
        for num in range(1, int(last_page) + 1):
            name = str(num)
            uri = self._get_page_uri(chapter_uri, name, None)
            pages.append(Page(name, uri))
        return pages

    @staticmethod
    def _get_chapter_number(chapter):
        """Returns chapter's number from a chapter's HtmlElement"""
        return chapter.text.split(' - ')[0]

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        return re.sub('[0-9]+$', page_name, chapter_uri)


class MangaAnimea(MangaSite):
    """class for manga animea site"""
    site_uri = "http://manga.animea.net"

    _chapters_css = "ul.chapterlistfull li a"
    _pages_css = "div.float-left select.pageselect option"
    _image_css = "img#scanmr"

    @property
    def title(self):
        """Returns the right manga title from user input"""
        self.input_title = self.input_title.lower()
        return re.sub(r'[^a-z0-9]+', '-', self.input_title)

    @property
    def title_uri(self):
        """Returns the index page's url of manga title"""
        return "{0}/{1}.html".format(self.site_uri, self.title)

    @staticmethod
    def _get_page_uri(chapter_uri, page_name, page):
        """Returns manga image page url"""
        return re.sub(r'.html$', '-page-{0}.html'.format(page_name), chapter_uri)


class MangaReader(MangaSite):
    """class for mangareader site"""
    site_uri = "http://www.mangareader.net"
    descending_list = False

    _chapters_css = "#chapterlist td a"
    _pages_css = "div#selectpage option"
    _image_css = "img#img"

    @property
    def title(self):
        """Returns the right manga title from user input"""
        self.input_title = self.input_title.lower()
        return re.sub(r'[^\-a-z0-9]', '', re.sub(r'[ _]', '-', self.input_title))

    @property
    def title_uri(self):
        """Returns the index page's url of manga title"""
        # some title's page is in the root, others hidden in a random numeric subdirectory,
        # so we need to search the manga list to get the correct url.
        try:
            content = self.session.get("{0}/alphabetical".format(self.site_uri), headers=self._headers).text
            page = re.findall(r'[0-9]+/' + self.title + '.html', content)[0]
            uri = "{0}/{1}".format(self.site_uri, page)
        except IndexError:
            uri = "{0}/{1}".format(self.site_uri, self.title)
        return uri

    @staticmethod
    def _get_page_uri(chapter_uri, page_name='1', page_input=None):
        """Returns manga image page url"""
        # older stuff, the one in numeric subdirectory, typically named "chapter-X.html",
        # while the new stuff only use number.
        if chapter_uri.endswith('.html'):
            page = re.sub(r'\-[0-9]+/', "-{0}/".format(page_name), chapter_uri)
            return "{0}{1}".format(chapter_uri, page)
        else:
            return "{0}/{1}".format(chapter_uri, page_name)


SITES = dict(animea=MangaAnimea,
             mangafox=MangaFox,
             mangalion=MangaLion,
             senmanga=SenManga,
             cartoonmad=CartoonMad,
             rawmangaupdate=RawMangaUpdate,
             mangahere=MangaHere,
             mangareader=MangaReader,
             mangastream=MangaStream,
             mangatown=MangaTown)


def progress(page, total):
    """Display progress bar"""
    try:
        page, total = int(page), int(total)
        marks = int(round(50 * (page / total)))
        spaces = int(round(50 - marks))
    except Exception:
        raise MangaException('Unknown error')

    loader = '[' + ('#' * int(marks)) + ('-' * int(spaces)) + ']'

    sys.stdout.write('%s page %d of %d\r' % (loader, page, total))
    if page == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

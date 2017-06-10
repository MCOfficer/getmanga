# -*- coding: utf8 -*-
# Copyright (c) 2010-2014, Jamaludin Ahmad
# Released subject to the MIT License.
# Please see http://en.wikipedia.org/wiki/MIT_License

import os
import sys
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import pkg_resources

try:
    import argparse
except ImportError:
    sys.exit('You need to have "argparse" module installed to run this script')

from getmanga import SITES, MangaException, GetManga


version = 0 #pkg_resources.require("GetManga")[0].version


def cmdparse():
    """Returns parsed arguments from command line"""
    parser = argparse.ArgumentParser()

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-f', '--file', type=str, help="%(prog)s config file")
    group1.add_argument('-t', '--title', type=str, help="manga title to download")

    parser.add_argument('-s', '--site', choices=SITES.keys(), default='mangahere',
                        help="manga site to download from")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a', '--all', action='store_true', help="download all chapters available")
    group.add_argument('-c', '--chapter', type=str, help="chapter(s) number to download")
    group.add_argument('-n', '--new', type=str, help="download new chapters")
    group.add_argument('-l', '--latest', type=str, help="download latest chapter")
    group.add_argument('--checknew', action='store_true', help="check how many new chapters are available")
    group.add_argument('--list', action='store_true', help="list all available chapters")

    parser.add_argument('-d', '--dir', type=str, default='.', help='download directory')
    parser.add_argument('-v', '--version', action='version',
                        version='{0} {1}'.format(parser.prog, version),
                        help="show program version and exit")

    args = parser.parse_args()
    args.begin = None
    args.end = None

    if (not args.file) and (not args.title):
        sys.exit("{0}: error: must specify either config file or manga title".format(parser.prog))

    if args.file:
        if not os.path.isfile(args.file):
            parser.print_usage()
            sys.exit("{0}: error: config file does not exit".format(parser.prog))
    if args.chapter:
        (args.begin, args.end, args.chapter, chapter_valid) = parseargchapter(args.chapter)
        if (not chapter_valid):
            parser.print_usage()
            sys.exit("{0}: error: invalid chapter interval, the end "
                     "should be bigger than start".format(parser.prog))
    return args

def parseargchapter(arg_chapter):
    arg_begin = None
    arg_end = None
    chapter = arg_chapter.split('-')
    if len(chapter) == 2:
        arg_chapter = None
        arg_begin = chapter[0]
        arg_end = chapter[1] if chapter[1] else None
    if arg_begin and arg_end and (int(arg_begin) > int(arg_end)):
        valid = False
    else:
        valid = True
    return (arg_begin, arg_end, arg_chapter, valid)

def configparse(filepath):
    """Returns parsed config from an ini file"""
    parser = configparser.SafeConfigParser()
    parser.read(filepath)
    config = []
    base_dir = None

    if parser.has_section('GetManga'):
        if parser.has_option('GetManga', 'base_dir'):
            base_dir = parser.get('GetManga', 'base_dir')
            if base_dir[-1] != "/":
                base_dir = base_dir + "/"
    overall_config = {"base_dir":base_dir}
    for section in parser.sections():
        if section != "GetManga":
            # skip the overall config
            title = section
            try:
                this_dir = None
                if parser.has_option(title, 'dir'):
                    this_dir = parser.get(title, 'dir')
                if (base_dir == None) and (this_dir == None):
                    sys.exit("Error: must define either dir or base_dir in config file.")
                config.append((parser.get(title, 'site'), title,
                               this_dir,
                               parser.get(title, 'chapters')))
            except Exception as msg:
                raise MangaException('Config Error: %s' % msg)
    return (overall_config, config)


def main():
    args = cmdparse()

    try:

        if args.file:
            (overall_config, config) = configparse(args.file)
            base_dir = overall_config["base_dir"]
            if (base_dir != None):
                if base_dir[-1] != "/":
                    base_dir = base_dir + "/"
            for (site, title, this_dir, arg_chapter) in config:
                manga = GetManga(site, title)
                if (this_dir == None):
                    if (base_dir == None):
                        sys.exit("Error: must define either dir or base_dir in config file.")
                    else:
                        this_dir = base_dir + manga.manga.title
                manga.path = this_dir
                if arg_chapter.strip().lower() == 'all':
                    for chapter in manga.chapters:
                        manga.get(chapter)
                elif arg_chapter.strip().lower() == 'latest':
                    manga.get(manga.latest)
                elif arg_chapter.strip().lower() == 'new':
                    manga.getNewChapters()
                else:
                    (arg_begin, arg_end, arg_chapter, chapter_valid) = parseargchapter(arg_chapter)
                    if (chapter_valid):
                        downloadChapters(manga, arg_chapter, arg_begin, arg_end)
                    else:
                        print "Error on " + title + ": invalid chapter interval."
        else:
            manga = GetManga(args.site, args.title)
            if args.dir:
                manga.path = args.dir

            if args.all:
                for chapter in manga.chapters:
                    manga.get(chapter)
            elif (args.chapter or args.begin):
                downloadChapters(manga, args.chapter, args.begin, args.end)
            elif args.latest:
                # last chapter
                manga.get(manga.latest)
            elif args.new:
                manga.getNewChapters()
            elif args.list:
                for chapter in manga.chapters:
                    print(chapter.name)
            else:
                numnew = manga.numNewChapters()
                if (numnew == 0):
                    print "No new chapters available"
                elif (numnew == 1):
                    print "1 new chapter available"
                else:
                    print str(numnew) + " new chapters available"

    except MangaException as msg:
        sys.exit(msg)

def downloadChapters(manga, arg_chapter, arg_begin, arg_end):
    try:
        if arg_chapter:
            # single chapter
            # actually, also download decimal chapters (e.g. 12 will download 12.1, 12.2, etc)
            exist = False
            for chapter in manga.chapters:
                if int(float(chapter.number)) == int(float(arg_chapter)):
                    manga.get(chapter)
                    exist = True
            if (not exist):
                print("Chapter doesn't exist.")

        elif arg_begin:
            # download range
            start = None
            stop = None
            for index, chapter in enumerate(manga.chapters):
                # take the floor of chapter numbers.
                # so, if we are asked to download 1-2, include 1.1, 1.2, 1.3, etc.
                if (start == None) and (int(float(chapter.number)) == int(float(arg_begin))):
                    start = index
                if arg_end and int(float(chapter.number)) == int(float(arg_end)):
                    stop = index + 1
            if (stop != None) and ( (arg_end == None) or (stop != None)):
                for chapter in manga.chapters[start:stop]:
                    manga.get(chapter)
            else:
                print("Bad chapter indices provided for " + manga.title)
    except MangaException as msg:
        sys.exit(msg)

if __name__ == '__main__':
    main()

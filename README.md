# getmanga
**Yet another (multi-site) manga downloader.**

getmanga is a program to download manga from an online manga reader
and save it to a .cbz format.

Currently supported sites:

* manga.animea.net
* mangafox.me
* mangahere.cc
* mangareader.net
* mangastream.com
* mangadex.org (partially implemented)
* raw.senmanga.com (日本語)
* rawmangaupdate.com (日本語)
* cartoonmad.com (繁體中文)
* webtoons.com (English, 繁體中文, 简体中文, ภาษาไทย, bahasa Indonesia)

## Usage:
* The simplest way:

  `getmanga -t {title} --latest`

  will download the latest chapter of that title from the default site
  (mangahere.co)

* Or if you want to get from specific site:

  `getmanga -t {title} -s {site}  --latest`

  example: `getmanga 'fairy tail' -s animea --latest`

* Download all chapters of a title:

  `getmanga -t {title} -s {site} --all`

  example: `getmanga one_piece -s mangastream --all`

* Download specific chapter(s) of a title:

  `getmanga -t {title} -s {site} -c {chapter}`

   example:

   * `getmanga bleach -s mangareader -c 300`: download only chapter 300

   * `getmanga bleach -s mangareader -c 300-310`: download chapters
     from 300 until 310

   * `getmanga bleach -s mangareader -c 300-`: download chapters from
     300 until the end

* See what chapters are available without downloading them:

  `getmanga -t {title} -s {site} --list`

* Check to see how many new chapters are available (newer than the newest chapter in the download directory) without downloading them:

  `getmanga -t {title} -s {site} --checknew`

* Download new chapters of a title (everything newer than the newest chapter in the download directory):

  `getmanga -t {title} -s {site} --new`

  example: `getmanga Kingdom -s senmanga --new`

**Special usage for specific sites**
* senmanga requires correct capitalization in manga title

* mangadex and cartoonmad urls have an id number instead of the manga title. So, first find the manga you want to download on mangadex or cartoonmad and then enter the title here as "title:id". This will be parsed so that the manga is named correctly. You can set title to any string you like.

    example: `getmanga -t tsukikage-baby:12772 -s mangadex --latest`

    example: `getmanga -t bleach:1300 -s cartoonmad --latest`

* webtoons.com requires a both a language tag and a page id.  So, first find the manga you want to download on webtoons.com and then enter the title here as "title:lang:id". This will be parsed so that the manga is named correctly.  Language tags: en, zh-hans, zh-hant, th, id

    example: `getmanga -t "ghost teller:th:944" -s webtoons --latest`

**Optional arguments:**

* -d/--dir: to save downloaded chapter to another directory.
* -f/--file: load config file instead of using command arguments.
  (example file included)

**Bash completion:**
To install bash completion, copy getmanga.completion to the relevant directory for your distribution. Most likely this means either
  `cp getmanga.completion /etc/bash-completion.d/`
  or
  `cp getmanga.completion /usr/share/bash-completion/completions/getmanga`

## Credits:
* yudha-gunslinger for [progressbar](http://gunslingerc0de.wordpress.com/2010/08/13/python-command-line-progress-bar/)

## License:

The MIT License:
Copyright (c) 2010-2017 Jamaludin Ahmad <j.ahmad at gmx.net>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


Code modified by wenli:

The MIT License:
Copyright (c) 2017 wenli

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

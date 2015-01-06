# encoding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .subtitles import SubtitlesInfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    unified_strdate,
)


class NRKIE(InfoExtractor):
    _VALID_URL = r'http://(?:www\.)?nrk\.no/(?:video|lyd)/[^/]+/(?P<id>[\dA-F]{16})'

    _TESTS = [
        {
            'url': 'http://www.nrk.no/video/dompap_og_andre_fugler_i_piip_show/D0FA54B5C8B6CE59/emne/piipshow/',
            'md5': 'a6eac35052f3b242bb6bb7f43aed5886',
            'info_dict': {
                'id': '150533',
                'ext': 'flv',
                'title': 'Dompap og andre fugler i Piip-Show',
                'description': 'md5:d9261ba34c43b61c812cb6b0269a5c8f'
            }
        },
        {
            'url': 'http://www.nrk.no/lyd/lyd_av_oppleser_for_blinde/AEFDDD5473BA0198/',
            'md5': '3471f2a51718195164e88f46bf427668',
            'info_dict': {
                'id': '154915',
                'ext': 'flv',
                'title': 'Slik høres internett ut når du er blind',
                'description': 'md5:a621f5cc1bd75c8d5104cb048c6b8568',
            }
        },
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        page = self._download_webpage(url, video_id)

        video_id = self._html_search_regex(r'<div class="nrk-video" data-nrk-id="(\d+)">', page, 'video id')

        data = self._download_json(
            'http://v7.psapi.nrk.no/mediaelement/%s' % video_id, video_id, 'Downloading media JSON')

        if data['usageRights']['isGeoBlocked']:
            raise ExtractorError('NRK har ikke rettig-heter til å vise dette programmet utenfor Norge', expected=True)

        video_url = data['mediaUrl'] + '?hdcore=3.1.1&plugin=aasp-3.1.1.69.124'

        images = data.get('images')
        if images:
            thumbnails = images['webImages']
            thumbnails.sort(key=lambda image: image['pixelWidth'])
            thumbnail = thumbnails[-1]['imageUrl']
        else:
            thumbnail = None

        return {
            'id': video_id,
            'url': video_url,
            'ext': 'flv',
            'title': data['title'],
            'description': data['description'],
            'thumbnail': thumbnail,
        }


class NRKTVIE(SubtitlesInfoExtractor):
    _VALID_URL = r'(?P<baseurl>http://tv\.nrk(?:super)?\.no)/(?:serie/[^/]+|program)/(?P<id>[a-zA-Z]{4}\d{8})'

    _TESTS = [
        {
            'url': 'http://tv.nrk.no/serie/20-spoersmaal-tv/MUHH48000314/23-05-2014',
            'md5': 'adf2c5454fa2bf032f47a9f8fb351342',
            'info_dict': {
                'id': 'MUHH48000314',
                'ext': 'flv',
                'title': '20 spørsmål',
                'description': 'md5:bdea103bc35494c143c6a9acdd84887a',
                'upload_date': '20140523',
                'duration': 1741.52,
            }
        },
        {
            'url': 'http://tv.nrk.no/program/mdfp15000514',
            'md5': '383650ece2b25ecec996ad7b5bb2a384',
            'info_dict': {
                'id': 'mdfp15000514',
                'ext': 'flv',
                'title': 'Kunnskapskanalen: Grunnlovsjubiléet - Stor ståhei for ingenting',
                'description': 'md5:654c12511f035aed1e42bdf5db3b206a',
                'upload_date': '20140524',
                'duration': 4605.0,
            }
        },
    ]

    def _str2seconds(self, t):
        parts = t.split(':')
        try:
            s = float(parts[2])
        except ValueError: # NRK Uses a negative duration for copyright info
            s = 0.0
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + s;

    def _seconds2str(self, s):
        return '%02d:%02d:%02d.%03d' % (s/3600, (s%3600)/60, s%60, (s%1)*1000)

    def _debug_print(self, txt):
        if self._downloader.params.get('verbose', False):
            self.to_screen(u'[debug] %s' % txt)

    def _extract_captions(self, subtitlesurl, video_id, baseurl):
        url = "%s%s" % (baseurl, subtitlesurl)
        self._debug_print(u'%s: Subtitle url: %s' % (video_id, url))
        captions = self._download_xml(url, video_id, 'Downloading subtitles')
        lang = captions.get('lang', 'no')
        ps = captions.findall('./{0}body/{0}div/{0}p'.format('{http://www.w3.org/ns/ttml}'))
        if not len(ps):
            self._debug_print(u'%s: Found no subtitles on subtitle page, something is wrong.')
        srt = ''
        for pos, p in enumerate(ps):
            begin = self._str2seconds(p.get('begin'))
            duration = self._str2seconds(p.get('dur'))
            starttime = self._seconds2str(begin)
            endtime = self._seconds2str(begin + duration)
            linebreak = ''
            text = ''
            for child in p.itertext():
                text = text + linebreak + child;
                linebreak = '\n'
            srt += '%s\r\n%s --> %s\r\n%s\r\n\r\n' % (str(pos), starttime, endtime, text)
        subtitle = {}
        subtitle[lang] = srt
        return subtitle

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        baseurl = mobj.group('baseurl')

        page = self._download_webpage(url, video_id)

        title = self._html_search_meta('title', page, 'title')
        description = self._html_search_meta('description', page, 'description')
        thumbnail = self._html_search_regex(r'data-posterimage="([^"]+)"', page, 'thumbnail', fatal=False)
        upload_date = unified_strdate(self._html_search_meta('rightsfrom', page, 'upload date', fatal=False))
        duration = float_or_none(
            self._html_search_regex(r'data-duration="([^"]+)"', page, 'duration', fatal=False))
        subtitlesurl = self._html_search_regex(
            r'data-subtitlesurl[ ]*=[ ]*"([^"]+)"', page, 'subtitlesurl', fatal=False, default=None)

        subtitle = {}

        if subtitlesurl:
            subtitle = self._extract_captions(subtitlesurl, video_id, baseurl)
        else: self._debug_print("Failed to find subtitles")

        formats = []

        f4m_url = re.search(r'data-media="([^"]+)"', page)
        if f4m_url:
            formats.append({
                'url': f4m_url.group(1) + '?hdcore=3.1.1&plugin=aasp-3.1.1.69.124',
                'format_id': 'f4m',
                'ext': 'flv',
            })

        m3u8_url = re.search(r'data-hls-media="([^"]+)"', page)
        if m3u8_url:
            formats.append({
                'url': m3u8_url.group(1),
                'format_id': 'm3u8',
            })

        if self._downloader.params.get('listsubtitles', False):
            self._list_available_subtitles(video_id, subtitle)
            return

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitle,
        }

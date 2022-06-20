# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import parse_age_limit


class ErtflixIE(InfoExtractor):
    _VALID_URL = r'https?://www\.ertflix\.gr/(?:series|vod)/(?P<id>[a-z]{3}\.\d+)'
    _TEST = {
        'url': 'https://www.ertflix.gr/en/vod/vod.130833-the-incredible-story-of-the-giant-pear-i-apisteyti-istoria-toy-gigantioy-achladioy',
        'info_dict': {
            'id': '130833',
            'displayid' : 'Η απίστευτη ιστορία του γιγάντιου αχλαδιού',
            'ext': 'mp4',
            'title': 'Η απίστευτη ιστορία του γιγάντιου αχλαδιού',
            'description' : 'The incredible story of the giant pear.',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }
    @staticmethod
    def _parse_age_rating(info_dict):
        return parse_age_limit(
            info_dict.get('AgeRating')
            or (info_dict.get('IsAdultContent') and 18)
            or (info_dict.get('IsKidsContent') and 0))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_url = self._search_regex(
            r"url\s*:\s*'(rtmp://[^']+)'",
            webpage, 'video URL')

        video_id = self._search_regex(
            r'mediaid\s*=\s*(\d+)',
            webpage, 'video id', fatal=False)
        
        description = self._og_search_description(webpage)

        title = self._og_search_title(webpage)

        thumbnail = self._og_search_thumbnail(webpage)

        return {
            'id': video_id,
            'url' : video_url,
            'title': title,
            'description': description ,
            'thumbnail' : thumbnail 
        } 

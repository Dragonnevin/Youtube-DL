# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
import json
import time
import calendar


class LivestreamfailsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?livestreamfails\.com/clip/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://livestreamfails.com/clip/139200',
        'md5': '8a03aea1a46e94a05af6410337463102',
        'info_dict': {
            'id': '139200',
            'ext': 'mp4',
            'display_id': 'ConcernedLitigiousSalmonPeteZaroll-O8yo9W2L8OZEKhV2',
            'title': 'Streamer jumps off a trampoline at full speed',
            'creator': 'paradeev1ch',
            'thumbnail': 'https://livestreamfails-image-prod.b-cdn.net/image/3877b1d38db083fa25c82685bbaf645637e575ea.png',
            'timestamp': 1656271785,
            'upload_date': '20220626',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url)

        # https://livestreamfails.com/clip/id uses https://api.livestreamfails.com/clip/ to fetch the video metadata
        # Use the same endpoint here to avoid loading and parsing the provided page (which requires JS)
        api_response = json.loads(self._download_webpage('https://api.livestreamfails.com/clip/' + id, id))

        # Get the input timestamp (test case gives 2022-06-26T19:29:45.515Z)
        timestamp = api_response.get('createdAt')
        if(timestamp):
            # Parse it into a struct_time
            timestamp = time.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Convert the struct_time to a UNIX timestamp while ignoring the local timezone attached by time.strptime()
            timestamp = calendar.timegm(timestamp)

        return {
            'id': id,
            'display_id': api_response.get('sourceId'),  # Twitch ID of clip
            'timestamp': timestamp,
            'url': 'https://livestreamfails-video-prod.b-cdn.net/video/' + api_response.get('videoId'),
            'title': api_response.get('label'),
            'creator': api_response.get('streamer', {}).get('label'),
            'thumbnail': 'https://livestreamfails-image-prod.b-cdn.net/image/' + api_response.get('imageId'),
        }

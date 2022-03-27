# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_HTMLParser,
    compat_urlparse,
    compat_str,
)
from ..utils import (
    ExtractorError,
    determine_ext,
    find_xpath_attr,
    fix_xml_ampersands,
    GeoRestrictedError,
    get_element_by_class,
    int_or_none,
    parse_duration,
    remove_start,
    strip_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
    update_url_query,
    urljoin,
    xpath_text,
)


class RaiBaseIE(InfoExtractor):
    _UUID_RE = r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
    _GEO_COUNTRIES = ['IT']
    _GEO_BYPASS = False

    def _extract_relinker_info(self, relinker_url, video_id):
        if not re.match(r'https?://', relinker_url):
            return {'formats': [{'url': relinker_url}]}

        formats = []
        geoprotection = None
        is_live = None
        duration = None

        for platform in ('mon', 'flash', 'native'):
            relinker = self._download_xml(
                relinker_url, video_id,
                note='Downloading XML metadata for platform %s' % platform,
                transform_source=fix_xml_ampersands,
                query={'output': 45, 'pl': platform},
                headers=self.geo_verification_headers())

            if not geoprotection:
                geoprotection = xpath_text(
                    relinker, './geoprotection', default=None) == 'Y'

            if not is_live:
                is_live = xpath_text(
                    relinker, './is_live', default=None) == 'Y'
            if not duration:
                duration = parse_duration(xpath_text(
                    relinker, './duration', default=None))

            url_elem = find_xpath_attr(relinker, './url', 'type', 'content')
            if url_elem is None:
                continue

            media_url = url_elem.text

            # This does not imply geo restriction (e.g.
            # http://www.raisport.rai.it/dl/raiSport/media/rassegna-stampa-04a9f4bd-b563-40cf-82a6-aad3529cb4a9.html)
            if '/video_no_available.mp4' in media_url:
                continue

            ext = determine_ext(media_url)
            if (ext == 'm3u8' and platform != 'mon') or (ext == 'f4m' and platform != 'flash'):
                continue

            if ext == 'm3u8' or 'format=m3u8' in media_url or platform == 'mon':
                formats.extend(self._extract_m3u8_formats(
                    media_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif ext == 'f4m' or platform == 'flash':
                manifest_url = update_url_query(
                    media_url.replace('manifest#live_hds.f4m', 'manifest.f4m'),
                    {'hdcore': '3.7.0', 'plugin': 'aasp-3.7.0.39.44'})
                formats.extend(self._extract_f4m_formats(
                    manifest_url, video_id, f4m_id='hds', fatal=False))
            else:
                bitrate = int_or_none(xpath_text(relinker, 'bitrate'))
                formats.append({
                    'url': media_url,
                    'tbr': bitrate if bitrate > 0 else None,
                    'format_id': 'http-%d' % bitrate if bitrate > 0 else 'http',
                })

        if not formats and geoprotection is True:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)

        return dict((k, v) for k, v in {
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
        }.items() if v is not None)

    @staticmethod
    def _extract_subtitles(url, video_data):
        STL_EXT = 'stl'
        SRT_EXT = 'srt'
        subtitles = {}
        subtitles_array = video_data.get('subtitlesArray') or []
        for k in ('subtitles', 'subtitlesUrl'):
            subtitles_array.append({'url': video_data.get(k)})
        for subtitle in subtitles_array:
            sub_url = subtitle.get('url')
            if sub_url and isinstance(sub_url, compat_str):
                sub_lang = subtitle.get('language') or 'it'
                sub_url = urljoin(url, sub_url)
                sub_ext = determine_ext(sub_url, SRT_EXT)
                subtitles.setdefault(sub_lang, []).append({
                    'ext': sub_ext,
                    'url': sub_url,
                })
                if STL_EXT == sub_ext:
                    subtitles[sub_lang].append({
                        'ext': SRT_EXT,
                        'url': sub_url[:-len(STL_EXT)] + SRT_EXT,
                    })
        return subtitles


class RaiPlayIE(RaiBaseIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/.+?-(?P<id>%s))\.(?:html|json)' % RaiBaseIE._UUID_RE
    _TESTS = [{
        'url': 'http://www.raiplay.it/video/2014/04/Report-del-07042014-cb27157f-9dd0-4aee-b788-b1f67643a391.html',
        'md5': '8970abf8caf8aef4696e7b1f2adfc696',
        'info_dict': {
            'id': 'cb27157f-9dd0-4aee-b788-b1f67643a391',
            'ext': 'mp4',
            'title': 'Report del 07/04/2014',
            'alt_title': 'St 2013/14 - Espresso nel caffè - 07/04/2014',
            'description': 'md5:d730c168a58f4bb35600fc2f881ec04e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Rai Gulp',
            'duration': 6160,
            'series': 'Report',
            'season': '2013/14',
            'subtitles': {
                'it': 'count:2',
            },
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.raiplay.it/video/2016/11/gazebotraindesi-efebe701-969c-4593-92f3-285f0d1ce750.html?',
        'only_matching': True,
    }, {
        # subtitles at 'subtitlesArray' key (see #27698)
        'url': 'https://www.raiplay.it/video/2020/12/Report---04-01-2021-2e90f1de-8eee-4de4-ac0e-78d21db5b600.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        base, video_id = re.match(self._VALID_URL, url).groups()

        media = self._download_json(
            base + '.json', video_id, 'Downloading video JSON')

        title = media['name']

        video = media['video']

        relinker_info = self._extract_relinker_info(video['content_url'], video_id)
        self._sort_formats(relinker_info['formats'])

        thumbnails = []
        for _, value in media.get('images', {}).items():
            if value:
                thumbnails.append({
                    'url': urljoin(url, value),
                })

        date_published = media.get('date_published')
        time_published = media.get('time_published')
        if date_published and time_published:
            date_published += ' ' + time_published

        subtitles = self._extract_subtitles(url, video)

        program_info = media.get('program_info') or {}
        season = media.get('season')

        info = {
            'id': remove_start(media.get('id'), 'ContentItem-') or video_id,
            'display_id': video_id,
            'title': self._live_title(title) if relinker_info.get(
                'is_live') else title,
            'alt_title': strip_or_none(media.get('subtitle')),
            'description': media.get('description'),
            'uploader': strip_or_none(media.get('channel')),
            'creator': strip_or_none(media.get('editor') or None),
            'duration': parse_duration(video.get('duration')),
            'timestamp': unified_timestamp(date_published),
            'thumbnails': thumbnails,
            'series': program_info.get('name'),
            'season_number': int_or_none(season),
            'season': season if (season and not season.isdigit()) else None,
            'episode': media.get('episode_title'),
            'episode_number': int_or_none(media.get('episode')),
            'subtitles': subtitles,
        }

        info.update(relinker_info)
        return info


class RaiPlayLiveIE(RaiPlayIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/dirette/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'http://www.raiplay.it/dirette/rainews24',
        'info_dict': {
            'id': 'd784ad40-e0ae-4a69-aa76-37519d238a9c',
            'display_id': 'rainews24',
            'ext': 'mp4',
            'title': 're:^Diretta di Rai News 24 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:4d00bcf6dc98b27c6ec480de329d1497',
            'uploader': 'Rai News 24',
            'creator': 'Rai News 24',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }]


class RaiPlayPlaylistIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/programmi/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'http://www.raiplay.it/programmi/nondirloalmiocapo/',
        'info_dict': {
            'id': 'nondirloalmiocapo',
            'title': 'Non dirlo al mio capo',
            'description': 'md5:98ab6b98f7f44c2843fd7d6f045f153b',
        },
        'playlist_mincount': 12,
    }]

    def _real_extract(self, url):
        base, playlist_id = re.match(self._VALID_URL, url).groups()

        program = self._download_json(
            base + '.json', playlist_id, 'Downloading program JSON')

        entries = []
        for b in (program.get('blocks') or []):
            for s in (b.get('sets') or []):
                s_id = s.get('id')
                if not s_id:
                    continue
                medias = self._download_json(
                    '%s/%s.json' % (base, s_id), s_id,
                    'Downloading content set JSON', fatal=False)
                if not medias:
                    continue
                for m in (medias.get('items') or []):
                    path_id = m.get('path_id')
                    if not path_id:
                        continue
                    video_url = urljoin(url, path_id)
                    entries.append(self.url_result(
                        video_url, ie=RaiPlayIE.ie_key(),
                        video_id=RaiPlayIE._match_id(video_url)))

        return self.playlist_result(
            entries, playlist_id, program.get('name'),
            try_get(program, lambda x: x['program_info']['description']))


class RaiIE(RaiBaseIE):
    _VALID_URL = r'https?://[^/]+\.(?:rai\.(?:it|tv)|rainews\.it)/.+?-(?P<id>%s)(?:-.+?)?\.html' % RaiBaseIE._UUID_RE
    _TESTS = [{
        # var uniquename = "ContentItem-..."
        # data-id="ContentItem-..."
        'url': 'http://www.raisport.rai.it/dl/raiSport/media/rassegna-stampa-04a9f4bd-b563-40cf-82a6-aad3529cb4a9.html',
        'info_dict': {
            'id': '04a9f4bd-b563-40cf-82a6-aad3529cb4a9',
            'ext': 'mp4',
            'title': 'TG PRIMO TEMPO',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1758,
            'upload_date': '20140612',
        },
        'skip': 'This content is available only in Italy',
    }, {
        # with ContentItem in many metas
        'url': 'http://www.rainews.it/dl/rainews/media/Weekend-al-cinema-da-Hollywood-arriva-il-thriller-di-Tate-Taylor-La-ragazza-del-treno-1632c009-c843-4836-bb65-80c33084a64b.html',
        'info_dict': {
            'id': '1632c009-c843-4836-bb65-80c33084a64b',
            'ext': 'mp4',
            'title': 'Weekend al cinema, da Hollywood arriva il thriller di Tate Taylor "La ragazza del treno"',
            'description': 'I film in uscita questa settimana.',
            'thumbnail': r're:^https?://.*\.png$',
            'duration': 833,
            'upload_date': '20161103',
        }
    }, {
        # with ContentItem in og:url
        'url': 'http://www.rai.it/dl/RaiTV/programmi/media/ContentItem-efb17665-691c-45d5-a60c-5301333cbb0c.html',
        'md5': '6865dd00cf0bbf5772fdd89d59bd768a',
        'info_dict': {
            'id': 'efb17665-691c-45d5-a60c-5301333cbb0c',
            'ext': 'mp4',
            'title': 'TG1 ore 20:00 del 03/11/2016',
            'description': 'TG1 edizione integrale ore 20:00 del giorno 03/11/2016',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2214,
            'upload_date': '20161103',
        }
    }, {
        # initEdizione('ContentItem-...'
        'url': 'http://www.tg1.rai.it/dl/tg1/2010/edizioni/ContentSet-9b6e0cba-4bef-4aef-8cf0-9f7f665b7dfb-tg1.html?item=undefined',
        'info_dict': {
            'id': 'c2187016-8484-4e3a-8ac8-35e475b07303',
            'ext': 'mp4',
            'title': r're:TG1 ore \d{2}:\d{2} del \d{2}/\d{2}/\d{4}',
            'duration': 2274,
            'upload_date': '20170401',
        },
        'skip': 'Changes daily',
    }, {
        # HLS live stream with ContentItem in og:url
        'url': 'http://www.rainews.it/dl/rainews/live/ContentItem-3156f2f2-dc70-4953-8e2f-70d7489d4ce9.html',
        'info_dict': {
            'id': '3156f2f2-dc70-4953-8e2f-70d7489d4ce9',
            'ext': 'mp4',
            'title': 'La diretta di Rainews24',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # ContentItem in iframe (see #12652) and subtitle at 'subtitlesUrl' key
        'url': 'http://www.presadiretta.rai.it/dl/portali/site/puntata/ContentItem-3ed19d13-26c2-46ff-a551-b10828262f1b.html',
        'info_dict': {
            'id': '1ad6dc64-444a-42a4-9bea-e5419ad2f5fd',
            'ext': 'mp4',
            'title': 'Partiti acchiappavoti - Presa diretta del 13/09/2015',
            'description': 'md5:d291b03407ec505f95f27970c0b025f4',
            'upload_date': '20150913',
            'subtitles': {
                'it': 'count:2',
            },
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Direct MMS URL
        'url': 'http://www.rai.it/dl/RaiTV/programmi/media/ContentItem-b63a4089-ac28-48cf-bca5-9f5b5bc46df5.html',
        'only_matching': True,
    }, {
        'url': 'https://www.rainews.it/tgr/marche/notiziari/video/2019/02/ContentItem-6ba945a2-889c-4a80-bdeb-8489c70a8db9.html',
        'only_matching': True,
    }]

    def _extract_from_content_id(self, content_id, url):
        media = self._download_json(
            'http://www.rai.tv/dl/RaiTV/programmi/media/ContentItem-%s.html?json' % content_id,
            content_id, 'Downloading video JSON')

        title = media['name'].strip()

        media_type = media['type']
        if 'Audio' in media_type:
            relinker_info = {
                'formats': [{
                    'format_id': media.get('formatoAudio'),
                    'url': media['audioUrl'],
                    'ext': media.get('formatoAudio'),
                }]
            }
        elif 'Video' in media_type:
            relinker_info = self._extract_relinker_info(media['mediaUri'], content_id)
        else:
            raise ExtractorError('not a media file')

        self._sort_formats(relinker_info['formats'])

        thumbnails = []
        for image_type in ('image', 'image_medium', 'image_300'):
            thumbnail_url = media.get(image_type)
            if thumbnail_url:
                thumbnails.append({
                    'url': compat_urlparse.urljoin(url, thumbnail_url),
                })

        subtitles = self._extract_subtitles(url, media)

        info = {
            'id': content_id,
            'title': title,
            'description': strip_or_none(media.get('desc')),
            'thumbnails': thumbnails,
            'uploader': media.get('author'),
            'upload_date': unified_strdate(media.get('date')),
            'duration': parse_duration(media.get('length')),
            'subtitles': subtitles,
        }

        info.update(relinker_info)

        return info

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        content_item_id = None

        content_item_url = self._html_search_meta(
            ('og:url', 'og:video', 'og:video:secure_url', 'twitter:url',
             'twitter:player', 'jsonlink'), webpage, default=None)
        if content_item_url:
            content_item_id = self._search_regex(
                r'ContentItem-(%s)' % self._UUID_RE, content_item_url,
                'content item id', default=None)

        if not content_item_id:
            content_item_id = self._search_regex(
                r'''(?x)
                    (?:
                        (?:initEdizione|drawMediaRaiTV)\(|
                        <(?:[^>]+\bdata-id|var\s+uniquename)=|
                        <iframe[^>]+\bsrc=
                    )
                    (["\'])
                    (?:(?!\1).)*\bContentItem-(?P<id>%s)
                ''' % self._UUID_RE,
                webpage, 'content item id', default=None, group='id')

        content_item_ids = set()
        if content_item_id:
            content_item_ids.add(content_item_id)
        if video_id not in content_item_ids:
            content_item_ids.add(video_id)

        for content_item_id in content_item_ids:
            try:
                return self._extract_from_content_id(content_item_id, url)
            except GeoRestrictedError:
                raise
            except ExtractorError:
                pass

        relinker_url = self._proto_relative_url(self._search_regex(
            r'''(?x)
                (?:
                    var\s+videoURL|
                    mediaInfo\.mediaUri
                )\s*=\s*
                ([\'"])
                (?P<url>
                    (?:https?:)?
                    //mediapolis(?:vod)?\.rai\.it/relinker/relinkerServlet\.htm\?
                    (?:(?!\1).)*\bcont=(?:(?!\1).)+)\1
            ''',
            webpage, 'relinker URL', group='url'))

        relinker_info = self._extract_relinker_info(
            urljoin(url, relinker_url), video_id)
        self._sort_formats(relinker_info['formats'])

        title = self._search_regex(
            r'var\s+videoTitolo\s*=\s*([\'"])(?P<title>[^\'"]+)\1',
            webpage, 'title', group='title',
            default=None) or self._og_search_title(webpage)

        info = {
            'id': video_id,
            'title': title,
        }

        info.update(relinker_info)

        return info


class HTMLListAttrsParser(compat_HTMLParser):
    def __init__(self):
        compat_HTMLParser.__init__(self)
        self.items = []
        self._level = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'li' and self._level == 0:
            self.items.append(dict(attrs))
        self._level += 1

    def handle_endtag(self, tag):
        self._level -= 1


class RaiPlayRadioBaseIE(InfoExtractor):
    _BASE = 'https://www.raiplayradio.it'

    def parse_list(self, webpage):
        parser = HTMLListAttrsParser()
        parser.feed(webpage)
        parser.close()
        return parser.items

    def get_playlist_iter(self, url, uid):
        webpage = self._download_webpage(url, uid)
        for attrs in self.parse_list(webpage):
            title = attrs['data-title'].strip()
            audio_url = urljoin(url, attrs['data-mediapolis'])
            entry = {
                'url': audio_url,
                'id': attrs['data-uniquename'].lstrip('ContentItem-'),
                'title': title,
                'ext': 'mp3',
                'language': 'it',
            }
            if 'data-image' in attrs:
                entry['thumbnail'] = urljoin(url, attrs['data-image'])
            yield entry

    def get_playlist(self, *args, **kwargs):
        return list(self.get_playlist_iter(*args, **kwargs))


class RaiPlayRadioIE(RaiPlayRadioBaseIE):
    _VALID_URL = r'%s/audio/.+?-(?P<id>%s)\.html' % (
        RaiPlayRadioBaseIE._BASE, RaiBaseIE._UUID_RE)
    _TEST = {
        'url': 'https://www.raiplayradio.it/audio/2019/07/RADIO3---LEZIONI-DI-MUSICA-36b099ff-4123-4443-9bf9-38e43ef5e025.html',
        'info_dict': {
            'id': '36b099ff-4123-4443-9bf9-38e43ef5e025',
            'ext': 'mp3',
            'title': 'Dal "Chiaro di luna" al  "Clair de lune", '
                     'prima parte con Giovanni Bietti',
            'thumbnail': r're:^https?://.*\.jpg$',
            'language': 'it',
        }
    }

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        list_url = url.replace('.html', '-list.html')
        for entry in self.get_playlist_iter(list_url, audio_id):
            if entry['id'] == audio_id:
                return entry


class RaiPlayRadioPlaylistIE(RaiPlayRadioBaseIE):
    _VALID_URL = r'%s/playlist/.+?-(?P<id>%s)\.html' % (
        RaiPlayRadioBaseIE._BASE, RaiBaseIE._UUID_RE)
    _TEST = {
        'url': 'https://www.raiplayradio.it/playlist/2017/12/Alice-nel-paese-delle-meraviglie-72371d3c-d998-49f3-8860-d168cfdf4966.html',
        'info_dict': {
            'id': '72371d3c-d998-49f3-8860-d168cfdf4966',
            'title': "Alice nel paese delle meraviglie",
            'description': "di Lewis Carrol letto da Aldo Busi",
        },
        'playlist_count': 11,
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_webpage = self._download_webpage(url, playlist_id)
        playlist_title = unescapeHTML(self._html_search_regex(
            r'data-playlist-title="(.+?)"', playlist_webpage, 'title'))
        playlist_creator = self._html_search_meta(
            'nomeProgramma', playlist_webpage)
        playlist_description = get_element_by_class(
            'textDescriptionProgramma', playlist_webpage)

        player_href = self._html_search_regex(
            r'data-player-href="(.+?)"', playlist_webpage, 'href')
        list_url = urljoin(url, player_href)

        entries = self.get_playlist(list_url, playlist_id)
        for index, entry in enumerate(entries, start=1):
            entry.update({
                'track': entry['title'],
                'track_number': index,
                'artist': playlist_creator,
            })
            if playlist_title:
                entry['album'] = playlist_title

        return self.playlist_result(
            entries, playlist_id, playlist_title, playlist_description)

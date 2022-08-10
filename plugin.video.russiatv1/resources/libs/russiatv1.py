# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import requests
from future.utils import python_2_unicode_compatible

__all__ = ['RussiaTvClient', 'RussiaTvError']


class RussiaTvError(Exception):
    pass


@python_2_unicode_compatible
class RussiaTvClient(object):
    _api_url = 'https://api.vgtrk.com/api/v1'

    def __init__(self, channels):

        self._channels = channels
        self._client = requests.Session()

        self._brand_includes = ['id', 'title', 'body', 'titleOrig', 'titleOrig', 'hasManySeries', 'sortBy',
                                'ageRestrictions', 'countFullVideos', 'countVideos', 'seriesIsOver', 'dateRec',
                                'pictures', 'countries', 'tags', 'personTypes', 'productionYearStart', 'anons',
                                'rank']
        self._video_includes = ['id', 'title', 'anons', 'episodeId', 'brandId', 'series', 'duration', 'sources',
                                'pictures', 'episodeTitle', 'dateRec', 'brandTitle', 'videoType']

    def __str__(self):
        return '<RussiaTvClient>'

    def __del__(self):
        self._client.close()

    @staticmethod
    def _extract_json(r):
        try:
            json = r.json()
        except ValueError as err:
            raise RussiaTvError(err)

        if json.get('metadata') is not None \
                and json['metadata'].get('code') is not None \
                and json['metadata']['code'] != 200:
            error_message = json['metadata'].get('errorMessage')
            if error_message is None:
                error_message = json['metadata'].get('errorType')
            raise RussiaTvError(error_message)
        elif json.get('status') is not None \
                and json['status'] != 200:
            raise RussiaTvError(json['errors'])

        return json

    def menu(self, limit=None, offset=None):
        url = self._api_url + '/menu/'

        includes = ['id', 'title', 'tags']

        params = {'channels': self._channels,
                  'offset': offset,
                  'limit': limit,
                  'includes': ':'.join(includes),
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j

    def brands(self, tags, limit, offset, keyword=None):
        url = self._api_url + '/brands/'

        params = {'channels': self._channels,
                  'offset': offset,
                  'limit': limit,
                  'includes': ':'.join(self._brand_includes),
                  'hasFullVideos': 'true',
                  'tags': ':'.join(tags),
                  'search': keyword,
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j

    def brands_search(self, keyword, limit, offset):
        url = self._api_url + '/brands/'

        keyword = keyword.replace('+', ' ')
        keyword = keyword.replace('\\', ' ')
        keyword = keyword.replace('/', ' ')
        keyword = keyword.replace('!', '')
        keyword = keyword.replace(':', '')

        params = {'channels': self._channels,
                  'offset': offset,
                  'limit': limit,
                  'includes': ':'.join(self._brand_includes),
                  'hasFullVideos': 'true',
                  'titleSuggest': keyword,
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j

    def brand_info(self, brand_id):
        url = self._api_url + '/brands/{0}/'.format(brand_id)

        params = {'includes': ':'.join(self._brand_includes),
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j['data']

    def videos(self, brand_id, sort, limit=1, offset=0, video_type=1, includes=None):
        url = self._api_url + '/videos/'

        if includes is None:
            includes = self._video_includes

        params = {'brands': brand_id,
                  # 'channels': self._channels,
                  'limit': limit,
                  'hasEpisode': 1,
                  'hasEpisodes': 1,
                  'offset': offset,
                  'type': video_type,
                  'includes': ':'.join(includes),
                  'sort': sort,
                  'sortOrder': 'asc',
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j

    def video(self, video_id):
        url = self._api_url + '/videos/{0}/'.format(video_id)

        params = {'includes': ':'.join(self._video_includes),
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        return j['data']

    def check_video_access(self, video_id):
        url = 'https://player.vgtrk.com/iframe/datavideo/'
        params = {'id': video_id,
                  'sid': 'russiatv',
                  }

        r = self._client.get(url, params=params)
        j = self._extract_json(r)

        medialist = j['data']['playlist']['medialist']

        for item in medialist:
            if item['id'] == video_id \
                    and item['errors']:
                raise RussiaTvError(item['errors'])

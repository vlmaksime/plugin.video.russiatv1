# -*- coding: utf-8 -*-
# Module: russiatv1
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import requests
import urllib
import re
import random

class RussiaTvApiError(Exception):
    """Custom exception"""
    pass

def sort_by_date(item):
    date = item['dateRec'][6:10] + item['dateRec'][3:5] + item['dateRec'][0:2] + item['dateRec'][12:].replace(':', '')
    return date

class RussiaTv:

    def __init__( self, params = {} ):

        #Settings
        self.video_quality = params.get('video_quality', 0)
        self.default_limit = 20

        vgtrk_dev_url = 'http://vgtrk-data.dev.webdeveloperlab.ru'
        vgtrk_api_url = 'https://api.vgtrk.com/api/v1'

        self._actions = {'main':            {'url': vgtrk_dev_url + '/r1_main.json'},
                         'category_items':  {'url': vgtrk_api_url + '/brands/channels/1/tags/#cat_id'},
                         'videos':          {'url': vgtrk_api_url + '/videos/brands/#brand_id/channels/1'},
                         'brand':           {'url': vgtrk_api_url + '/brands/#brand_id'},
                         'video':           {'url': vgtrk_api_url + '/videos/#video_id'},
                         'episode':         {'url': vgtrk_api_url + '/episodes/#episode_id'},
                         'search':          {'url': vgtrk_api_url + '/brands/channels/1'},
                         }

    def _http_request( self, action, params = {}, url_params=None ):
        action_settings = self._actions.get(action)

        url = action_settings['url']

        if url_params is not None:
            for key, val in url_params.iteritems():
                url = url.replace(key, val)

        headers = {'User-Agent': 'mobile-russitv1-android',
                   'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate',
                   'Connection': 'keep-alive',
                   'Cache-Control': 'no-cache',
                   }

        try:
            r = requests.get(url, params=params, headers=headers)
            r.raise_for_status()
        except requests.ConnectionError as err:
            raise RussiaTvApiError('Connection error')

        return r

    def _extract_json(self, r):
        try:
            json = r.json()
        except ValueError as err:
            raise RussiaTvApiError(err)

        if json['metadata'].get('code') is not None \
          and json['metadata']['code'] != 200:
            raise RussiaTvApiError(json['metadata']['errorMessage'])

        return json

    def get_categories( self ):
        r = self._http_request('main')

        json = self._extract_json(r)

        for category in json['categories']:
            tags = []
            for tag in category['tags']:
                tags.append(str(tag['id']))

            cat = {'title': category['title'],
                   'tags': tags
                   }

            yield(cat)

    def _get_brand_info( self, params ):

        url_params = {'#brand_id': str(params['brand_id'])}

        r = self._http_request('brand', url_params=url_params)
        json = self._extract_json(r)

        return json['data']

    def get_video_list( self, content_type, params ):
        if content_type == 'category':
            video_list = self.browse_category(params)
        elif content_type == 'episodes':
            video_list = self.browse_episodes(params)
        elif content_type == 'search':
            video_list = self.search(params)
        return video_list

    def browse_episodes( self, params ):

        brand_info = self._get_brand_info(params)

        limit = min(brand_info['countVideos'], 9999)
        offset = params.get('offset', 0)
        sort = params['sort']

        url_params = {'#brand_id': str(params['brand_id'])}
        u_params = {'limit': limit,
                    'offset': offset,
                    'type': 1,
                    'sort': sort
                    }

        r = self._http_request('videos', u_params, url_params=url_params)
        json = self._extract_json(r)

        start_num = offset * limit

        result = {'count': len(json['data']),
                  'pages': json['pagination']['pages'],
                  'limit': limit,
                  'title': brand_info['title'],
                  'list':  self._make_episode_list(json, brand_info, sort, start_num)
                  }

        return result

    def _make_episode_list( self, json, brand_info, sort, start_num ):

        episodes = json['data']
        if sort == 'date':
            episodes.sort(key=sort_by_date)

        index = start_num
        for item in episodes:
            index += 1
            yield self._get_episode_info(item, brand_info, index)

    def _get_episode_info(self, item, brand_item, date_episode=0):
        mediatype = 'episode'

        #Defaults
        poster = self._get_image(item['pictures'], u'bq')
        thumb = self._get_image(item['pictures'], u'hdr')
        fanart = thumb

        plot = item['anons']

        aired = ''
        label = ''
        title = ''
        originaltitle = ''
        tvshowtitle = ''
        ratings = []
        properties = {}

        #Titles
        tvshowtitle = brand_item['title']
        if isinstance(tvshowtitle, int):
            tvshowtitle = str(tvshowtitle)
        if tvshowtitle.endswith(u'. Х/ф'):
            tvshowtitle = tvshowtitle[0:-5]

        tvshowtitle_orig = brand_item.get('titleOrig') if brand_item.get('titleOrig') else tvshowtitle
        if isinstance(tvshowtitle_orig, int):
            tvshowtitle_orig = str(tvshowtitle_orig)
        if tvshowtitle_orig.endswith(u'. Х/ф'):
            tvshowtitle_orig = tvshowtitle_orig[0:-5]

        title = item['episodeTitle']
        if type(title) == int:
            title = str(title)

        year = brand_item['productionYearStart']

        #Duration
        duration = item['duration']

        #Cast
#        cast = []
#        for actor in persons.get('actors', []):
#            cast.append({'name': actor['name'],
#                         'thumbnail': actor['cover']})

        #Director
#        director = []
#        for director_ in persons.get('director', []):
#            director.append(director_['name'])

        #Writer
#        writer = []
#        for scenarist in persons.get('scenarist', []):
#            writer.append(scenarist['name'])

        #Country

        country = []
        for _country in brand_item['countries']:
            country.append(_country['title'])

        #Date
        date = '%s.%s.%s' % (item['dateRec'][0:2], item['dateRec'][3:5], item['dateRec'][6:10])
        aired = '%s-%s-%s' % (item['dateRec'][6:10], item['dateRec'][3:5], item['dateRec'][0:2])

        episode = item['series'] if item['series'] != 0 else date_episode
        season = self._get_season(brand_item['title'])

        video_info = {'type':     mediatype,
                      'brand_id': item['brandId'],
                      'episode':  episode,
                      'season':  season,
                      'video_id': item['id'],
                      'title':    tvshowtitle,
                      'originaltitle': tvshowtitle_orig,
                      }

        if episode == 0:
            season = 0

        item_info = {# 'label':  label,
                     #'cast':   cast,
                     #'ratings': ratings,
                     #'properties': properties,
                     'info': {'video': {'date': date,
                                        #'genre': genres,
                                        'country': country,
                                        'year': year,
                                        'sortepisode': episode,
                                        #'sortseason': season,
                                        #'director': director,
                                        'season': season,
                                        'episode': episode,
                                        'tvshowtitle': tvshowtitle,
                                        'plot': plot,
                                        'title': title,
                                        'sorttitle': title,
                                        'duration': duration,
                                        #'writer': writer,
                                        #'premiered': premiered,
                                        'aired': aired,
                                        'mediatype': mediatype,
                                        }
                              },
                     'art': {'poster': poster},
                     'fanart': fanart,
                     'thumb':  thumb,
                    }

        result = {'item_info':  item_info,
                  'video_info': video_info
                  }
        return result

    def _get_season(self, title):
        parts = title.split('-')
        if parts[-1].isdigit():
            result = int(parts[-1])
        else:
            result = 1
        return result

    def browse_category( self, params ):

        url_params = {'#cat_id': params.get('cat_id', '')}

        u_params = {'hasFullVideos': 'true',
                    'limit':  params.get('limit', self.default_limit),
                    'offset': params.get('offset', 0),
                    'sort':   params.get('sort', 'date'),
                    }

        r = self._http_request('category_items', u_params, url_params=url_params)
        json = self._extract_json(r)

        result = {'count': len(json['data']),
                  'pages': json['pagination']['pages'],
                  'list':  self._make_video_list(json)}

        return result

    def search( self, params ):

        keyword = params['keyword'].replace('-', ' ')
        keyword = keyword.replace('+', ' ')
        keyword = keyword.replace('\\', ' ')
        keyword = keyword.replace('/', ' ')
        keyword = keyword.replace('!', '')

        u_params = {'hasFullVideos': 'true',
                    'offset':    params.get('offset', 0),
                    'limit':  params.get('limit', self.default_limit),
                    'sort': params.get('sort', 'date'),
                    'search': keyword,
                    }

        r = self._http_request('search', u_params)
        json = self._extract_json(r)

        items = json.get('items', [])

        result = {'count': len(json['data']),
                  'pages': json['pagination']['pages'],
                  'list':  self._make_video_list(json)}
        return result

    def _make_video_list( self, json ):

        for item in json['data']:
            yield self._get_video_info(item)

    def _get_video_info(self, item):
        mediatype = 'tvshow' if (item['countFullVideos'] > 1) else 'movie'

        picture = item['pictures'][random.randint(0, len(item['pictures'])-1)]
        banner = self._get_image(picture, u'prm')
        poster = self._get_image(picture, u'bq')

        picture = item['pictures'][random.randint(0, len(item['pictures'])-1)]
        thumb = self._get_image(picture, u'hdr')
        fanart = thumb

        title = item['title']
        if isinstance(title, int):
            title = str(title)
        if title.endswith(u'. Х/ф'):
            title = title[0:-5]

        title_orig = item.get('titleOrig') if item.get('titleOrig') else title
        if isinstance(title_orig, int):
            title_orig = str(title_orig)
        if title_orig.endswith(u'. Х/ф'):
            title_orig = title_orig[0:-5]

        country = []
        for _country in item['countries']:
            country.append(_country['title'])

        video_info = {'type':     mediatype,
                      'brand_id': item['id'],
                      'sort':     item['sortBy'],
                      'count':    item['countFullVideos'],
                      'title':    title,
                      'originaltitle': title_orig,
                      }

        item_info = {'label':  title,
                     #'cast':   cast,
                     #'ratings': self._get_rating(item),
                     #'properties': properties,
                     'info': {'video': {'date': '%s.%s.%s' % (item['dateRec'][0:2], item['dateRec'][3:5], item['dateRec'][6:10]),
                                        #'genre': genres,
                                        'country': country,
                                        'year': item.get('productionYearStart'),
                                        'title': title,
                                        'originaltitle': title_orig,
                                        'sorttitle': title,
                                        #'tvshowtitle': title,
                                        'plot': self._remove_html(item['body']),
                                        'mpaa': self._get_mpaa(item['ageRestrictions']),
                                        #'duration': duration,
                                        #'director': director,
                                        #'writer': writer,
                                        'aired': '%s-%s-%s' % (item['dateRec'][6:10], item['dateRec'][3:5], item['dateRec'][0:2]),
                                        'mediatype': mediatype,
                                        }
                              },
                              'art': {'poster': poster,
                                      'banner': banner
                                      },
                              'fanart': fanart,
                              'thumb':  thumb,
                     }

        video_info = {'item_info':  item_info,
                      'video_info': video_info
                      }
        return video_info

    def get_video_url( self, params ):

        brand_info = self._get_brand_info(params)

        if params['type'] == 'movie':
            url_params = {'#brand_id': str(params['brand_id'])}
            u_params = {'limit': brand_info['countFullVideos'],
                        'type': 1,
                        }

            r = self._http_request('videos', u_params, url_params=url_params)
            json = self._extract_json(r)
            if len(json['data']):
                data = json['data'][0]
            else:
                raise RussiaTvApiError('Video not found')

            video_details = self._get_video_info(brand_info)

        elif params['type'] == 'episode':
            url_params = {'#video_id': str(params['video_id'])}

            r = self._http_request('video', url_params=url_params)
            json = self._extract_json(r)
            data = json['data']

            video_details = self._get_episode_info(data, brand_info)
        else:
            raise RussiaTvApiError('Wrong media type')

        item_info = video_details['item_info']
        item_info['path'] = self._get_video_url(data)

        return item_info

    def _get_video_url( self, data ):

        sources = data['sources']

        path = ''
        if (not path or self.video_quality >= 0) and sources['m3u8'].get('auto'):
            path = sources['m3u8']['auto']
        if (not path or self.video_quality >= 1) and sources['mp4'].get('low-wide'):
            path = sources['mp4']['low-wide']
        if (not path or self.video_quality >= 2) and sources['mp4'].get('medium-wide'):
            path = sources['mp4']['medium-wide']
        if (not path or self.video_quality >= 3) and sources['mp4'].get('high-wide'):
            path = sources['mp4']['high-wide']
        if (not path or self.video_quality >= 4) and sources['mp4'].get('hd-wide'):
            path = sources['mp4']['hd-wide']

        return path

    def _get_image(self, pictures, preset):
        url = ''
        if pictures is not None:
            for picture in pictures['sizes']:
                if picture['preset'] == preset :
                    url = picture['url']

        return url

    def _get_mpaa( self, age_restriction ):
        if age_restriction == u'':
            return 'G'
        elif age_restriction == 6:
            return 'PG'
        elif age_restriction == 12:
            return 'PG-13'
        elif age_restriction == 16:
            return 'R'
        elif age_restriction == 18:
            return 'NC-17'
        else:
            return ''

    def _remove_html( self, text ):
        result = text
        result = result.replace(u'&nbsp;',      u' ')
        result = result.replace(u'&pound;',     u'£')
        result = result.replace(u'&euro;',      u'€')
        result = result.replace(u'&para;',      u'¶')
        result = result.replace(u'&sect;',      u'§')
        result = result.replace(u'&copy;',      u'©')
        result = result.replace(u'&reg;',       u'®')
        result = result.replace(u'&trade;',     u'™')
        result = result.replace(u'&deg;',       u'°')
        result = result.replace(u'&plusmn;',    u'±')
        result = result.replace(u'&frac14;',    u'¼')
        result = result.replace(u'&frac12;',    u'½')
        result = result.replace(u'&frac34;',    u'¾')
        result = result.replace(u'&times;',     u'×')
        result = result.replace(u'&divide;',    u'÷')
        result = result.replace(u'&fnof;',      u'ƒ')
        result = result.replace(u'&Alpha;',     u'Α')
        result = result.replace(u'&Beta;',      u'Β')
        result = result.replace(u'&Gamma;',     u'Γ')
        result = result.replace(u'&Delta;',     u'Δ')
        result = result.replace(u'&Epsilon;',   u'Ε')
        result = result.replace(u'&Zeta;',      u'Ζ')
        result = result.replace(u'&Eta;',       u'Η')
        result = result.replace(u'&Theta;',     u'Θ')
        result = result.replace(u'&Iota;',      u'Ι')
        result = result.replace(u'&Kappa;',     u'Κ')
        result = result.replace(u'&Lambda;',    u'Λ')
        result = result.replace(u'&Mu;',        u'Μ')
        result = result.replace(u'&Nu;',        u'Ν')
        result = result.replace(u'&Xi;',        u'Ξ')
        result = result.replace(u'&Omicron;',   u'Ο')
        result = result.replace(u'&Pi;',        u'Π')
        result = result.replace(u'&Rho;',       u'Ρ')
        result = result.replace(u'&Sigma;',     u'Σ')
        result = result.replace(u'&Tau;',       u'Τ')
        result = result.replace(u'&Upsilon;',   u'Υ')
        result = result.replace(u'&Phi;',       u'Φ')
        result = result.replace(u'&Chi;',       u'Χ')
        result = result.replace(u'&Psi;',       u'Ψ')
        result = result.replace(u'&Omega;',     u'Ω')
        result = result.replace(u'&alpha;',     u'α')
        result = result.replace(u'&beta;',      u'β')
        result = result.replace(u'&gamma;',     u'γ')
        result = result.replace(u'&delta;',     u'δ')
        result = result.replace(u'&epsilon;',   u'ε')
        result = result.replace(u'&zeta;',      u'ζ')
        result = result.replace(u'&eta;',       u'η')
        result = result.replace(u'&theta;',     u'θ')
        result = result.replace(u'&iota;',      u'ι')
        result = result.replace(u'&kappa;',     u'κ')
        result = result.replace(u'&lambda;',    u'λ')
        result = result.replace(u'&mu;',        u'μ')
        result = result.replace(u'&nu;',        u'ν')
        result = result.replace(u'&xi;',        u'ξ')
        result = result.replace(u'&omicron;',   u'ο')
        result = result.replace(u'&pi;',        u'π')
        result = result.replace(u'&rho;',       u'ρ')
        result = result.replace(u'&sigmaf;',    u'ς')
        result = result.replace(u'&sigma;',     u'σ')
        result = result.replace(u'&tau;',       u'τ')
        result = result.replace(u'&upsilon;',   u'υ')
        result = result.replace(u'&phi;',       u'φ')
        result = result.replace(u'&chi;',       u'χ')
        result = result.replace(u'&psi;',       u'ψ')
        result = result.replace(u'&omega;',     u'ω')
        result = result.replace(u'&larr;',      u'←')
        result = result.replace(u'&uarr;',      u'↑')
        result = result.replace(u'&rarr;',      u'→')
        result = result.replace(u'&darr;',      u'↓')
        result = result.replace(u'&harr;',      u'↔')
        result = result.replace(u'&spades;',    u'♠')
        result = result.replace(u'&clubs;',     u'♣')
        result = result.replace(u'&hearts;',    u'♥')
        result = result.replace(u'&diams;',     u'♦')
        result = result.replace(u'&quot;',      u'"')
        result = result.replace(u'&amp;',       u'&')
        result = result.replace(u'&lt;',        u'<')
        result = result.replace(u'&gt;',        u'>')
        result = result.replace(u'&hellip;',    u'…')
        result = result.replace(u'&prime;',     u'′')
        result = result.replace(u'&Prime;',     u'″')
        result = result.replace(u'&ndash;',     u'–')
        result = result.replace(u'&mdash;',     u'—')
        result = result.replace(u'&lsquo;',     u'‘')
        result = result.replace(u'&rsquo;',     u'’')
        result = result.replace(u'&sbquo;',     u'‚')
        result = result.replace(u'&ldquo;',     u'“')
        result = result.replace(u'&rdquo;',     u'”')
        result = result.replace(u'&bdquo;',     u'„')
        result = result.replace(u'&laquo;',     u'«')
        result = result.replace(u'&raquo;',     u'»')

        # result = result.replace(u'<br>',    u'\n')

        return re.sub('<[^<]+?>', '', result)

if __name__ == '__main__':
    pass
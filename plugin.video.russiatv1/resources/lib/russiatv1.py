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

class RussiaTv:

    def __init__(self, params=None):
        params = params or {}

        #Settings
        self.video_quality = params.get('video_quality', 0)
        self.default_limit = 20

        vgtrk_dev_url = 'http://storage2.russia1.mobileappdeveloper.ru'
        vgtrk_api_url = 'https://api.vgtrk.com/api/v1'

        self._actions = {'main':            {'url': vgtrk_dev_url + '/public/russia1/r1_main.json'},
                         'category_items':  {'url': vgtrk_api_url + '/brands/channels/1/tags/#cat_id'},
                         'videos':          {'url': vgtrk_api_url + '/videos/brands/#brand_id/channels/1'},
                         'brand':           {'url': vgtrk_api_url + '/brands/#brand_id'},
                         'video':           {'url': vgtrk_api_url + '/videos/#video_id'},
                         'episode':         {'url': vgtrk_api_url + '/episodes/#episode_id'},
                         'search':          {'url': vgtrk_api_url + '/brands/channels/1'},
                         'player':          {'url': 'https://player.vgtrk.com/iframe/datavideo/id/#video_id/sid/russiatv'},
                         }

        self.peoples = {'cast': [u'В ролях: ', u'В главной роли: ', u'В главных ролях:', u'Текст читает: ',
                                 u'Ведущие: ', u'Ведущий: ', u'Ведущая: '],
                        'director': [u'Режиссер: ', u'Режиссеры: ', u'Режиссер-постановщик: '],
                        'writer': [u'Авторы сценария: ', u'Автор сценария: ', u'Сценарий: '],
                        #'credits': [u'Оператор-постановщик: ', u'Художник-постановщик: ', u'Композитор: ',
                        #            u'Продюсеры: ', u'Оригинальный сюжет: ', u'Оператор: ', u'Художник по костюмам: ',
                        #            u'Художник по гриму: ', u'Режиссер монтажа: ', u'Автор идеи: ', u'Главный автор: ', u'Автор: '],
                        }

    def _http_request( self, action, params=None, url_params=None ):
        params = params or {}

        action_settings = self._actions.get(action)

        url = action_settings['url']

        if url_params is not None:
            for key, val in url_params.iteritems():
                url = url.replace(key, str(val))

        headers = {'User-Agent': 'mobile-russitv1-android',
                   'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate',
                   'Connection': 'keep-alive',
                   'Cache-Control': 'no-cache',
                   }

        try:
            r = requests.get(url, params=params, headers=headers)
            r.raise_for_status()
        except requests.ConnectionError:
            raise RussiaTvApiError('Connection error')

        return r

    def _extract_json(self, r):
        try:
            json = r.json()
        except ValueError as err:
            raise RussiaTvApiError(err)

        if json.get('metadata') is not None \
          and json['metadata'].get('code') is not None \
          and json['metadata']['code'] != 200:
            raise RussiaTvApiError(json['metadata']['errorMessage'])
        elif json.get('status') is not None \
          and json['status'] != 200:
            raise RussiaTvApiError(json['errors'])

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

    def _get_brand_data( self, params ):

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

        brand_info = self._get_brand_data(params)

        #limit = min(brand_info['countVideos'], 9999)
        limit = 9999
        offset = int(params.get('offset', '0'))
        sort = params.get('sort', 'date')

        url_params = {'#brand_id': str(params['brand_id'])}
        u_params = {'limit': limit,
                    'offset': offset,
                    #'type': 1,
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
            episodes.sort(key=self.sort_by_date)

        index = start_num
        for item in episodes:
            if item['series'] == 0 \
              and item['videoType'] != 1:
                continue
            
            index += 1
            yield self._get_item_info(brand_info, item, index)

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

        result = {'count': len(json['data']),
                  'pages': json['pagination']['pages'],
                  'list':  self._make_search_list(json, params)}
        return result

    def _make_video_list( self, json ):

        for item in json['data']:
            yield self._get_item_info(item)

    def _make_search_list( self, json, params ):
        full_list = params.get('full_list', True)
        keyword = params['keyword']
        
        for item in json['data']:
            if not full_list \
              and not self._video_have_keyword(item, keyword):
                continue
            
            yield self._get_item_info(item)

    def _get_item_info(self, brand, video=None, date_episode=0):
        if video is not None:
            mediatype = 'episode'
        else:
            mediatype = 'tvshow' if (brand['countFullVideos'] > 1) else 'movie'

        #Titles
        brand_title = self._get_title(brand['title'])
        brand_title_orig = self._get_title(brand.get('titleOrig')) if brand.get('titleOrig') else brand_title

        year = brand['productionYearStart']
        mpaa = self._get_mpaa(brand['ageRestrictions'])
        
        country = []
        for _country in brand['countries']:
            country.append(_country['title'])
        
        body = self._parse_body(brand['body'])

        if mediatype in ['tvshow', 'movie']:
            
            date = '%s.%s.%s' % (brand['dateRec'][0:2], brand['dateRec'][3:5], brand['dateRec'][6:10])
            
            picture = brand['pictures'][random.randint(0, len(brand['pictures'])-1)]
            banner = self._get_image(picture, u'prm')
            poster = self._get_image(picture, u'bq')
    
            picture = brand['pictures'][random.randint(0, len(brand['pictures'])-1)]
            thumb = self._get_image(picture, u'hdr')
            fanart = thumb

            tags = []
            for _tag in brand['tags']:
                tags.append(_tag['title'])

            video_info = {'type': mediatype,
                          'brand_id': brand['id'],
                          'sort': brand['sortBy'],
                          'count': brand['countFullVideos'],
                          'title': brand_title,
                          'have_trailer': brand['countVideos'] > brand['countFullVideos'],
                          'originaltitle': brand_title_orig,
                          }
    
            item_info = {'label': brand_title,
                         'cast': body.get('cast', []),
                         'info': {'video': {'date': date,
                                            'country': country,
                                            'year': year,
                                            'title': brand_title,
                                            'originaltitle': brand_title_orig,
                                            'sorttitle': brand_title,
                                            'plotoutline': brand['anons'],
                                            'plot': body['plot'],
                                            'mpaa': mpaa,
                                            'director': body.get('director', []),
                                            'writer': body.get('writer', []),
                                            'credits': body.get('credits', []),
                                            'mediatype': mediatype,
                                            'tag': tags,
                                            }
                                  },
                         'art': {'poster': poster,
                                 'banner': banner
                                 },
                         'fanart': fanart,
                         'thumb':  thumb,
                         'content_lookup': False,
                         }
        elif mediatype == 'episode':
    
            #Defaults
            poster = self._get_image(video['pictures'], u'bq')
            thumb = self._get_image(video['pictures'], u'hdr')
            fanart = thumb
    
            episode_title = self._get_title(video['episodeTitle'])
    
            #Date
            date = '%s.%s.%s' % (video['dateRec'][0:2], video['dateRec'][3:5], video['dateRec'][6:10])
            aired = '%s-%s-%s' % (video['dateRec'][6:10], video['dateRec'][3:5], video['dateRec'][0:2])
    
            episode = video['series'] if video['series'] != 0 else date_episode
            season = self._get_season(brand['title'])
    
            tags = []
            for _tag in video['tags']:
                tags.append(_tag['title'])

            video_info = {'type': mediatype,
                          'brand_id': video['brandId'],
                          'episode': episode,
                          'season': season,
                          'video_id': video['id'],
                          'title': brand_title,
                          'originaltitle': brand_title_orig,
                          }
    
            if episode == 0:
                season = 0
    
            item_info = {'cast': body.get('cast', []),
                         'info': {'video': {'date': date,
                                            'country': country,
                                            'year': year,
                                            'sortepisode': episode,
                                            'sortseason': season,
                                            'director': body.get('director', []),
                                            'season': season,
                                            'episode': episode,
                                            'tvshowtitle': brand_title,
                                            'plot': video['anons'],
                                            'mpaa': mpaa,
                                            'title': episode_title,
                                            'sorttitle': episode_title,
                                            'duration': video['duration'],
                                            'writer': body.get('writer', []),
                                            'aired': aired,
                                            'mediatype': mediatype,
                                            'tag': tags,
                                            }
                                  },
                         'art': {'poster': poster},
                         'fanart': fanart,
                         'thumb':  thumb,
                         'content_lookup': False,
                        }
            
        video_info = {'item_info':  item_info,
                      'video_info': video_info
                      }

        return video_info

    def get_trailer_url( self, params ):

        brand_info = self._get_brand_data(params)

        url_params = {'#brand_id': str(params['brand_id'])}
        
        for item_type in [3, 2]:
            u_params = {'limit': brand_info['countVideos'],
                        'type': item_type,
                        }
    
            r = self._http_request('videos', u_params, url_params=url_params)
            json = self._extract_json(r)
            if json['data']:
                while json['data']:
                    video = json['data'][random.randint(0, len(json['data'])-1)]
                    if video['series'] == 0 \
                      and video['duration'] <= 600:
                        return self._get_video_url(video)
                    else:
                        json['data'].remove(video)
        
        raise RussiaTvApiError('Trailer not found')

    def get_video_url( self, params ):

        brand_info = self._get_brand_data(params)

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

            video_details = self._get_item_info(brand_info)

        elif params['type'] == 'episode':
            url_params = {'#video_id': str(params['video_id'])}

            r = self._http_request('video', url_params=url_params)
            json = self._extract_json(r)
            data = json['data']

            video_details = self._get_item_info(brand_info, data)
        else:
            raise RussiaTvApiError('Wrong media type')

        self._check_video_access(data['id'])

        item_info = video_details['item_info']
        item_info['path'] = self._get_video_url(data)

        return item_info

    def _check_video_access(self, video_id):
        url_params = {'#video_id': str(video_id)}

        r = self._http_request('player', url_params=url_params)
        json = self._extract_json(r)

        medialist = json['data']['playlist']['medialist']
        
        for item in medialist:
            if item['errors'] and item['id'] == video_id:
                raise RussiaTvApiError(item['errors'].encode('utf-8'))


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
        if not text:
            return text

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

    def _get_title(self, title):
        if title is None:
            return title
        
        if isinstance(title, int):
            title = str(title)

        for str_end in [u'. Х/ф', u' Х/ф']:
            if title.endswith(str_end):
                title = title[0:-len(str_end)]

        return title
        
    def _parse_body(self, text):
        plot = []
        result = {}
                
        _text = text
        removed_strings = [u'\t']
        for string in removed_strings:
            _text = _text.replace(string, '')
        
        main_parts = _text.split(u'\r\n')
        for main_part in main_parts:
            if not main_part:
                continue
            parts = main_part.split(u'<br />')
            for _part in parts:
                part = self._remove_html(_part)
                if not part:
                    continue
                peoples = self._get_peoples(part)
                if peoples is not None:
                    for key, list in peoples.iteritems():
                        if result.get(key) is None:
                            result[key] = list
                        else:
                            for val in list:
                                result[key].append(val)
                elif part.startswith(u'Смотрите также: '):
                    pass 
                elif part.startswith(u'Страница проекта'):
                    pass
                elif part.startswith(u'Официальный сайт проекта'):
                    pass
                else:
                    plot.append(part)
            
        result['plot'] = u'[CR]'.join(plot)
        
        return result

    def _get_peoples(self, string):
        for prop, substrings in self.peoples.iteritems():
            for substring in substrings:
                if string.startswith(substring):
                    peoples = string[len(substring):].split(u', ')
                    list = []
                    for people in peoples:
                        parts = people.split(u' и ')
                        for part in parts:
                            if prop == 'cast':
                                list.append({'name': part})
                            else:
                                list.append(part)
                    return {prop: list}
        return None

    def _video_have_keyword(self, item, keyword):
        title = self._get_title(item['title'])
        originaltitle = self._get_title(item.get('titleOrig')) if item.get('titleOrig') else title

        kw = keyword.decode('utf-8').lower()
    
        result = (title.decode('utf-8').lower().find(kw) >= 0 or originaltitle.decode('utf-8').lower().find(kw) >= 0)
    
        return result
            
    def sort_by_date(self, item):
        date = item['dateRec'][6:10] + item['dateRec'][3:5] + item['dateRec'][0:2] + item['dateRec'][12:].replace(':', '')
        return date

if __name__ == '__main__':
    pass
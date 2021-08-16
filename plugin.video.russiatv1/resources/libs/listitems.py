# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import simplemedia
from future.utils import iteritems

__all__ = ['BrandInfo', 'SeasonInfo', 'VideoInfo', 'EmptyListItem', 'ListItem']

addon = simplemedia.Addon()
_ = addon.initialize_gettext()


class BrandInfo(simplemedia.VideoInfo):
    _path = None
    _trailer = None
    _mediatype = None
    _video_info = None
    brand_id = 0  # type: int
    video_id = 0  # type: int

    def __init__(self, brand_info, for_play=False, atl_names=False):
        self._brand_info = brand_info

        self._for_play = for_play
        self._atl_names = atl_names and not for_play

        self.brand_id = brand_info['id']

        self._body = self._parse_body()

    @property
    def date(self):
        date_rec = self._brand_info['dateRec']
        return '.'.join([date_rec[0:2], date_rec[3:5], date_rec[6:10]])

    @property
    def country(self):
        countries = self._brand_info.get('countries')
        if countries is not None:
            return [country['title'] for country in countries]

    @property
    def year(self):
        release_year = self._brand_info.get('productionYearStart')
        if release_year is not None \
                and release_year:
            return int(release_year)

    @property
    def episode(self):
        if self.mediatype in ['tvshow']:
            return self._brand_info['countFullVideos']

    @property
    def season(self):
        if self.mediatype in ['tvshow', 'season']:
            return 1

    @property
    def rating(self):
        if self.mediatype in ['tvshow', 'movie']:
            return self._brand_info['rank']

    @property
    def cast(self):
        if self._body.get('cast') is not None:
            return self._body['cast']

    @property
    def director(self):
        if self._body.get('director') is not None:
            return self._body['director']

    @property
    def mpaa(self):
        age_restrictions = self._brand_info.get('ageRestrictions')
        if age_restrictions is not None \
                and isinstance(age_restrictions, int):
            return '{0}+'.format(age_restrictions)

    @property
    def plot(self):
        return self._body['plot']

    @property
    def plotoutline(self):
        description = self._brand_info['anons']
        description = addon.remove_html(description)

        return description

    @property
    def title(self):
        if self._atl_names:
            title = self._atl_title()
        else:
            title = self._title()
        return title

    @property
    def original_title(self):
        if self._brand_info['titleOrig']:
            title = self._brand_info['titleOrig']
        else:
            title = self._title()

        return self._get_clear_title(title)

    @property
    def duration(self):
        if self._video_info is not None:
            return self._video_info['duration']

    @property
    def writer(self):
        if self._body.get('writer') is not None:
            return self._body['writer']

    @property
    def tvshowtitle(self):
        if self.mediatype in ['tvshow', 'season', 'episode']:
            if self._brand_info['title']:
                return self._brand_info['title']

    @property
    def status(self):
        if self.mediatype == 'tvshow' \
                and (self._brand_info['hasManySeries'] == 'true'):
            if self._brand_info['seriesIsOver'] == 'true':
                return _('Ended')
            else:
                return _('Continuing')

    @property
    def tag(self):
        tags = self._brand_info.get('tags')
        if tags is not None:
            return [tag['title'] for tag in tags]

    @property
    def path(self):
        return self._path

    @property
    def trailer(self):
        return self._trailer

    @property
    def mediatype(self):
        _mediatype = self._mediatype
        if _mediatype is None:
            video_count = self._brand_info['countFullVideos']
            has_series = (self._brand_info['hasManySeries'] == 'true')
            if video_count > 1 \
                    or has_series:
                _mediatype = 'tvshow'
            else:
                _mediatype = 'movie'

            self._mediatype = _mediatype

        return self._mediatype

    @staticmethod
    def _get_clear_title(title):

        if isinstance(title, int):
            title = str(title)

        for str_end in ['. Х/ф', ' Х/ф']:
            if title.endswith(str_end):
                title = title[0:-len(str_end)]

        return title

    def _title(self):
        return self._get_clear_title(self._brand_info['title'])

    def _atl_title(self):

        title_parts = []
        if self.mediatype == 'movie':
            title_parts.append(self.original_title)
            if self.year is not None:
                title_parts.append('({0})'.format(self.year))

        elif self.mediatype == 'episode':
            title_parts.append(self.tvshowtitle)
            title_parts.append('s%02de%02d' % (self.season, self.episode))
            episode_title = '{0}'.format(self._video_info['episodeTitle'])
            if episode_title:
                title_parts.append(episode_title)
        else:
            title_parts.append(self._title())

        return '.'.join(title_parts)
        return '.'.join(title_parts)

    @staticmethod
    def _get_image(preset, picture_item):
        for picture in picture_item['sizes']:
            if picture['preset'] == preset:
                return picture['url']

    def _parse_body(self):

        plot = []
        result = {}

        _text = self._brand_info['body']
        removed_strings = ['\t']
        for string in removed_strings:
            _text = _text.replace(string, '')

        main_parts = _text.split('\r\n')
        for main_part in main_parts:
            if not main_part:
                continue
            parts = main_part.split('<br />')
            for _part in parts:
                part = addon.remove_html(_part)
                if not part:
                    continue
                peoples = self._get_peoples(part)
                if peoples is not None:
                    for key, items in iteritems(peoples):
                        if result.get(key) is None:
                            result[key] = items
                        else:
                            for val in items:
                                result[key].append(val)
                elif part.startswith('Смотрите также: ') \
                        or part.startswith('Страница проекта') \
                        or part.startswith('Официальный сайт проекта'):
                    pass
                else:
                    plot.append(part)

        result['plot'] = '[CR]'.join(plot)

        return result

    @staticmethod
    def _get_peoples(string):
        peoples = {
            'cast': ['В ролях: ', 'В главной роли: ', 'В главных ролях:', 'Текст читает: ', 'Ведущие: ', 'Ведущий: ',
                     'Ведущая: '],
            'director': ['Режиссер: ', 'Режиссеры: ', 'Режиссер-постановщик: '],
            'writer': ['Авторы сценария: ', 'Автор сценария: ', 'Сценарий: '],
            'other': ['Композитор: ', 'Оператор: '],
        }

        for prop, substrings in iteritems(peoples):
            for substring in substrings:
                if string.startswith(substring):
                    peoples = string[len(substring):].split(', ')
                    items = []
                    for people in peoples:
                        parts = people.split(' и ')
                        for part in parts:
                            items.append(part)
                    return {prop: items}
        return None

    def get_banner(self):
        if len(self._brand_info['pictures']):
            return self._get_image('prm', self._brand_info['pictures'][0])

    def get_poster(self):
        if len(self._brand_info['pictures']):
            return self._get_image('bp', self._brand_info['pictures'][0])

    def get_thumb(self):
        if len(self._brand_info['pictures']) > 1:
            picture_item = self._brand_info['pictures'][1]
        else:
            picture_item = self._brand_info['pictures'][0]

        return self._get_image('hdr', picture_item)

    def get_fanart(self):
        return self.get_thumb()

    def set_path(self, path):
        self._path = path

    def set_trailer(self, trailer):
        self._trailer = trailer

    def set_video_info(self, video_info):
        self._video_info = video_info
        self.video_id = video_info['id']

    @property
    def brand_info(self):
        return self._brand_info

    @property
    def for_play(self):
        return self._for_play


class SeasonInfo(BrandInfo):
    offset = 0

    def __init__(self, brand_info, limit, total_episodes):
        super(SeasonInfo, self).__init__(brand_info, False, False)

        self._mediatype = 'season'

        self.limit = limit
        self.total_episodes = total_episodes

    @property
    def episode(self):
        episode = min(self.limit, (self.offset * self.limit) - self.total_episodes)
        return episode

    @property
    def title(self):
        last_episode = min((self.offset * self.limit) + self.limit, self.total_episodes)
        return '{0} {1}-{2}'.format(_('Episodes'), (self.offset * self.limit) + 1, last_episode)

    def set_offset(self, offset):
        self.offset = offset


class VideoInfo(BrandInfo):
    _episode = None

    def __init__(self, brand_info, video_info, for_play=False, atl_names=False):
        super(VideoInfo, self).__init__(brand_info, for_play, atl_names)

        self._video_info = video_info
        self.video_id = video_info['id']

    @property
    def date(self):
        date_rec = self._video_info['dateRec']
        return '{0}.{1}.{2}'.format(date_rec[0:2], date_rec[3:5], date_rec[6:10])

    @property
    def episode(self):
        if self.mediatype == 'episode':
            if self._video_info['series']:
                episode = self._video_info['series']
            else:
                episode = self._episode
            return episode

    @property
    def season(self):
        if self.mediatype == 'episode' \
                and self.episode is not None:

            parts = self._brand_info['title'].split('-')
            if parts[-1].isdigit():
                season = int(parts[-1])
            else:
                season = 1
            return season

    @property
    def plot(self):
        if self.mediatype == 'episode':
            return self._video_info['anons']
        else:
            return super(VideoInfo, self).plot

    @property
    def plotoutline(self):
        if self.mediatype == 'episode':
            return self._video_info['anons']
        else:
            return super(VideoInfo, self).plotoutline

    @property
    def originaltitle(self):
        if self.mediatype == 'episode':
            return self.title
        else:
            return super(VideoInfo, self).originaltitle

    @property
    def duration(self):
        return self._video_info['duration']

    @property
    def aired(self):
        date_rec = self._video_info['dateRec']
        return '{0}-{1}-{2}'.format(date_rec[6:10], date_rec[3:5], date_rec[0:2])

    @property
    def dateadded(self):
        date_rec = self._video_info['dateRec']
        return '{0}-{1}-{2} {3}'.format(date_rec[6:10], date_rec[3:5], date_rec[0:2], date_rec[11:])

    @property
    def mediatype(self):
        _mediatype = self._mediatype
        if _mediatype is None:
            video_count = self._brand_info['countFullVideos']
            has_series = (self._brand_info['hasManySeries'] == 'true')
            if video_count > 1 \
                    or has_series:
                _mediatype = 'episode'
            else:
                _mediatype = 'movie'

            self._mediatype = _mediatype

        return self._mediatype

    def _title(self):
        if self.mediatype == 'episode':
            if self._video_info['episodeTitle']:
                title = '{0}'.format(self._video_info['episodeTitle'])
            else:
                brand_part = '{0}. '.format(self._video_info['brandTitle'])
                if self._video_info['title'].startswith(brand_part):
                    title = self._video_info['title'][len(brand_part):]
                else:
                    title = '{0} {1}'.format(_('Episode'), self.episode)
        else:
            title = super(VideoInfo, self)._title()

        return title

    def get_thumb(self):
        picture_item = self._video_info['pictures']

        return self._get_image('lw', picture_item)

    def get_fanart(self):
        return super(VideoInfo, self).get_thumb()

    def set_episode(self, episode):
        self._episode = episode


class EmptyListItem(simplemedia.ListItemInfo):
    _url = None
    _path = None
    _info = None

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        return self._url

    def set_url(self, url):
        self._url = url

    def set_path(self, path):
        self._path = path


class ListItem(EmptyListItem):

    def __init__(self, video_info):

        self._info = video_info

        self._brand_info = video_info.brand_info
        self._mediatype = video_info.mediatype
        self._for_play = video_info.for_play

        self.brand_id = video_info.brand_id

    @property
    def label(self):
        return self._info.title

    @property
    def path(self):
        return self._path

    @property
    def is_folder(self):
        return self._mediatype in ['season', 'tvshow']

    @property
    def is_playable(self):
        return self._mediatype in ['movie', 'episode']

    @property
    def properties(self):
        properties = {}

        if self._mediatype == 'tvshow':
            properties['TotalSeasons'] = '{0}'.format(self._info.season)
            properties['TotalEpisodes'] = '{0}'.format(self._info.episode)
            properties['WatchedEpisodes'] = '0'
            properties['UnWatchedEpisodes'] = '{0}'.format(self._info.episode)
            properties['NumEpisodes'] = '{0}'.format(self._info.episode)

        return properties

    @property
    def art(self):
        art = {'banner': self._info.get_banner(),
               }

        if self._mediatype in ['season', 'episode']:
            art['tvshow.poster'] = self._info.get_poster()
        elif self._mediatype in ['tvshow', 'movie']:
            art['poster'] = self._info.get_poster()

        return art

    @property
    def thumb(self):
        if self._mediatype in ['movie', 'tvshow', 'season']:
            return self._info.get_poster()
        elif self._mediatype in ['episode']:
            return self._info.get_thumb()

    @property
    def fanart(self):
        return self._info.get_fanart()

    @property
    def info(self):
        return {'video': self._info.get_info()}

    @property
    def season(self):
        if self._mediatype in ['season', 'episode'] \
                and self._info.season is not None:
            return {'number': self._info.season}

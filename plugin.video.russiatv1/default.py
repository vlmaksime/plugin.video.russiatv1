# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import simplemedia
import xbmc
import xbmcplugin
from simpleplugin import py2_decode

from resources.libs import (RussiaTv, RussiaTvError,
                            BrandInfo, SeasonInfo, VideoInfo,
                            EmptyListItem, ListItem)

plugin = simplemedia.RoutedPlugin()
_ = plugin.initialize_gettext()

BrandInfo.plugin = plugin
EmptyListItem.plugin = plugin


@plugin.route('/')
def root():
    plugin.create_directory(_list_root(), content='', category=plugin.name)


def _list_root():
    try:
        menu_items = _get_menu_items()
    except (simplemedia.WebClientError, RussiaTvError) as e:
        plugin.notify_error(e)
    else:
        for menu_item in menu_items:
            url = plugin.url_for('menu', menu_id=menu_item['id'])
            list_item = {'label': menu_item['title'],
                         'url': url,
                         'icon': menu_item['icon'],
                         'fanart': plugin.fanart,
                         'is_folder': True,
                         'is_playble': False,
                         'content_lookup': False,
                         }
            yield list_item

    url = plugin.url_for('search_history')
    list_item = {'label': _('Search'),
                 'url': url,
                 'icon': plugin.get_image('DefaultAddonsSearch.png'),
                 'fanart': plugin.fanart,
                 'is_folder': True,
                 'is_playble': False,
                 'content_lookup': False,
                 }
    yield list_item


@plugin.route('/menu/<int:menu_id>/')
def menu(menu_id):
    menu_info = _menu_info(menu_id)

    offset = plugin.params.offset or '0'
    offset = int(offset)

    limit = plugin.params.limit
    if not limit:
        limit = plugin.get_setting('limit', False)
    limit = int(limit)
    try:
        brand_result = RussiaTv().brands(menu_info['tags'], limit, offset)
    except (RussiaTvError, simplemedia.WebClientError) as e:
        plugin.notify_error(e)
        plugin.create_directory([], succeeded=False)
    else:
        page_params = {'menu_id': menu_id,
                       }

        pages = _get_pages(page_params, offset, limit, brand_result['pagination']['totalCount'], 'menu')

        category_parts = [menu_info['title'],
                          '{0} {1}'.format(_('Page'), offset + 1),
                          ]

        result = {'items': _list_brands(brand_result['data'], pages),
                  'total_items': len(brand_result['data']),
                  'content': 'movies',
                  'category': ' / '.join(category_parts),
                  'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_UNSORTED, 'label2Mask': '%Y / %O'},
                  'update_listing': (offset > 0),
                  }
        plugin.create_directory(**result)


def _list_brands(brands, pages):
    use_atl_names = _use_atl_names()

    for brand_info in brands:
        item_info = BrandInfo(brand_info, atl_names=use_atl_names)
        if item_info.mediatype == 'movie':
            video_info = _get_movie_video_info(brand_info['id'], brand_info['sortBy'])
            item_info.set_video_info(video_info)

        if brand_info['countVideos'] > brand_info['countFullVideos']:
            trailer_url = _get_trailer_url(brand_info['id'])
            item_info.set_trailer(trailer_url)

        listitem = ListItem(item_info)

        url = _get_listitem_url(item_info, use_atl_names)
        listitem.set_url(url)

        yield listitem.get_item()

    if pages is not None:
        for listitem in _page_items(pages):
            yield listitem


@plugin.route('/brand/<int:brand_id>/videos/')
def brand_videos(brand_id):
    if plugin.params.offset is None:
        brand_seasons(brand_id)
    else:
        brand_episodes(brand_id)


def brand_seasons(brand_id):
    limit = plugin.get_setting('season_limit')
    try:
        api = RussiaTv()
        brand_info = api.brand_info(brand_id)
        videos = api.videos(brand_id, brand_info['sortBy'])
    except (RussiaTvError, simplemedia.WebClientError) as e:
        plugin.notify_error(e)
        plugin.create_directory([], succeeded=False)
    else:
        total_videos = videos['pagination']['totalCount']
        result = {'items': _list_seasons(brand_info, limit, total_videos),
                  'total_items': int(total_videos / limit),
                  'content': 'seasons',
                  'category': brand_info['title'],
                  'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_UNSORTED, 'label2Mask': '%Y / %O'},
                  }
        plugin.create_directory(**result)


def _list_seasons(brand_info, limit, total_episodes):
    use_atl_names = _use_atl_names()

    season_info = SeasonInfo(brand_info, limit, total_episodes)

    offset = 0
    while (offset * limit) + 1 < total_episodes:
        season_info.set_offset(offset)

        listitem = ListItem(season_info)

        url = _get_listitem_url(season_info, use_atl_names)
        listitem.set_url(url)

        offset += 1

        yield listitem.get_item()


def brand_episodes(brand_id):
    offset = plugin.params.offset or '0'
    offset = int(offset)

    limit = plugin.params.limit
    if not limit:
        limit = plugin.get_setting('season_limit', False)
    limit = int(limit)
    try:
        api = RussiaTv()
        brand_info = api.brand_info(brand_id)
        videos = api.videos(brand_id, brand_info['sortBy'], limit, offset)
    except (RussiaTvError, simplemedia.WebClientError) as e:
        plugin.notify_error(e)
        plugin.create_directory([], succeeded=False)
    else:
        category_parts = [brand_info['title'],
                          '{0} {1}-{2}'.format(_('Episodes'), (offset * limit) + 1,
                                               (offset * limit) + len(videos['data']))]

        sort_methods = []
        if _use_atl_names():
            sort_methods.append(xbmcplugin.SORT_METHOD_UNSORTED)
        else:
            sort_methods.append(xbmcplugin.SORT_METHOD_EPISODE)

        result = {'items': _list_episodes(brand_info, videos['data'], offset, limit),
                  'total_items': len(videos['data']),
                  'content': 'episodes',
                  'category': ' / '.join(category_parts),
                  'sort_methods': sort_methods,
                  }
        plugin.create_directory(**result)


def _list_episodes(brand_info, videos, offset, limit):
    use_atl_names = _use_atl_names()

    episode = offset * limit
    for video_item in videos:
        video_info = VideoInfo(brand_info, video_item, atl_names=use_atl_names)
        episode += 1
        video_info.set_episode(episode)

        listitem = ListItem(video_info)

        url = _get_listitem_url(video_info, use_atl_names)
        listitem.set_url(url)

        yield listitem.get_item()


@plugin.mem_cached(180)
def _get_menu_items():
    api = RussiaTv()

    menu_result = api.menu()
    menu_items = menu_result['data']

    if menu_result['pagination']['totalCount'] > menu_result['pagination']['limit']:
        offset = menu_result['pagination']['limit']
        limit = menu_result['pagination']['totalCount'] - offset
        menu_result = api.menu(limit, offset)
        menu_items.extend(menu_result['data'])

    movie_icon = plugin.get_image('DefaultMovies.png')
    tvshow_icon = plugin.get_image('DefaultTVShows.png')

    result = []
    for menu_item in menu_items:
        tags = []
        for tag in menu_item['tags']:
            tags.append(str(tag['id']))

        if menu_item['id'] == 267:
            icon = movie_icon
        else:
            icon = tvshow_icon

        item_info = {'id': menu_item['id'],
                     'title': menu_item['title'],
                     'tags': tags,
                     'icon': icon,
                     }
        result.append(item_info)

    return result


@plugin.route('/videos/<int:video_id>/')
def play_video(video_id):
    is_strm = plugin.params.strm == '1' \
              and plugin.kodi_major_version() >= '18'

    is_trailer = False

    succeeded = True

    try:
        if video_id == 0:
            raise RussiaTvError(_('Video not found'))

        api = RussiaTv()

        api.check_video_access(video_id)

        video_info = api.video(video_id)
        brand_info = api.brand_info(video_info['brandId'])

        video_item = VideoInfo(brand_info, video_info, True)

    except RussiaTvError as e:
        plugin.notify_error(e, True)
        succeeded = False
        listitem = EmptyListItem()
    except simplemedia.WebClientError as e:
        plugin.notify_error(e)
        succeeded = False
        listitem = EmptyListItem()
    else:

        listitem = ListItem(video_item)

        url = plugin.url_for('play_video', video_id=video_id)
        listitem.set_url(url)

        stream_url = _get_video_url(video_info['sources'])

        if not stream_url:
            plugin.notify_error(_('Video not found'))
            succeeded = False
        else:
            listitem.set_path(stream_url)

        is_trailer = (video_info['videoType'] == 3)

    if succeeded \
            and (is_strm or is_trailer):
        listitem.__class__ = EmptyListItem

    plugin.resolve_url(listitem.get_item(), succeeded)


@plugin.route('/search/history/')
def search_history():
    result = {'items': plugin.search_history_items(),
              'content': '',
              'category': ' / '.join([py2_decode(plugin.name), _('Search')]),
              }

    plugin.create_directory(**result)


@plugin.route('/search/remove/<int:index>')
def search_remove(index):
    plugin.search_history_remove(index)


@plugin.route('/search/clear')
def search_clear():
    plugin.search_history_clear()


@plugin.route('/search/')
def search():
    keyword = plugin.params.keyword or ''
    usearch = plugin.params.usearch or ''
    is_usearch = (usearch.lower() == 'true')

    if not keyword:
        keyword = plugin.get_keyboard_text('', _('Search'))

        if keyword \
                and not is_usearch:
            plugin.update_search_history(keyword)
            plugin.create_directory([], succeeded=False)

            url = plugin.url_for('search', keyword=keyword)
            xbmc.executebuiltin('Container.Update("%s")' % url)
            return

    elif keyword is not None:
        offset = plugin.params.offset or '0'
        offset = int(offset)

        limit = plugin.params.limit
        if not limit:
            limit = '9999' if is_usearch else plugin.get_setting('limit', False)
        limit = int(limit)

        try:
            search_result = RussiaTv().brands_search(keyword, limit, offset)
        except (RussiaTvError, simplemedia.WebClientError) as e:
            plugin.notify_error(e)
            plugin.create_directory([], succeeded=False)
        else:
            page_params = {'keyword': keyword,
                           }

            pages = _get_pages(page_params, offset, limit, search_result['pagination']['totalCount'], 'search')

            category_parts = [_('Search'), keyword,
                              '{0} {1}'.format(_('Page'), offset + 1),
                              ]

            result = {'items': _list_brands(search_result['data'], pages),
                      'total_items': len(search_result['data']),
                      'content': 'movies',
                      'category': ' / '.join(category_parts),
                      'sort_methods': {'sortMethod': xbmcplugin.SORT_METHOD_UNSORTED, 'label2Mask': '%Y / %O'},
                      'update_listing': (offset > 0),
                      }
            plugin.create_directory(**result)


def _menu_info(menu_id):
    for menu_item in _get_menu_items():
        if menu_item['id'] == menu_id:
            return menu_item


def _get_pages(page_params, offset, limit, total, action):
    # Parameters for previous page
    if (offset * limit) >= limit:
        prev_offset = offset - 1
        if prev_offset > 0:
            prev_page = {'offset': prev_offset,
                         'limit': limit,
                         }
            prev_page.update(page_params)
        else:
            prev_page = page_params
    else:
        prev_page = None

    # Parameters for next page
    next_offset = offset + 1
    if total > (next_offset * limit):
        next_page = {'offset': next_offset,
                     'limit': limit,
                     }
        next_page.update(page_params)
    else:
        next_page = None

    pages = {'action': action,
             'prev': prev_page,
             'next': next_page,
             }

    return pages


def _use_atl_names():
    return plugin.params.get('atl', '') == '1' \
           or plugin.get_setting('use_atl_names')


def _page_items(pages):
    if pages['prev'] is not None:
        url = plugin.url_for(pages['action'], **pages['prev'])
        listitem = {'label': _('Previous page...'),
                    'fanart': plugin.fanart,
                    'is_folder': True,
                    'url': url,
                    'properties': {'SpecialSort': 'bottom'},
                    'content_lookup': False,
                    }
        yield listitem

    if pages['next'] is not None:
        url = plugin.url_for(pages['action'], **pages['next'])
        listitem = {'label': _('Next page...'),
                    'fanart': plugin.fanart,
                    'is_folder': True,
                    'url': url,
                    'properties': {'SpecialSort': 'bottom'},
                    'content_lookup': False,
                    }
        yield listitem


def _get_listitem_url(item_info, use_atl_names=False):
    ext_dir_params = {}
    ext_item_params = {}
    if use_atl_names:
        ext_dir_params['atl'] = 1
        ext_item_params['strm'] = 1

    if item_info.mediatype in ['movie', 'episode']:
        url = plugin.url_for('play_video', video_id=item_info.video_id,
                             **ext_item_params)
    elif item_info.mediatype == 'tvshow':
        url = plugin.url_for('brand_videos', brand_id=item_info.brand_id, **ext_dir_params)
    elif item_info.mediatype == 'season':
        url = plugin.url_for('brand_videos', brand_id=item_info.brand_id, offset=item_info.offset,
                             limit=item_info.limit, **ext_dir_params)
    else:
        url = None

    return url


@plugin.cached(180)
def _get_trailer_url(brand_id):
    videos = RussiaTv().videos(brand_id, 'date', video_type=3, includes=['id'])
    if videos['pagination']['totalCount'] > 0:
        trailer_url = plugin.url_for('play_video', video_id=videos['data'][0]['id'])
        return trailer_url


@plugin.cached(180)
def _get_movie_video_info(brand_id, order):
    videos = RussiaTv().videos(brand_id, order, includes=['id', 'duration'])
    if videos['data']:
        result = videos['data'][0]
    else:
        result = {'id': 0,
                  'duration': 0
                  }
    return result


def _get_video_url(sources):
    video_quality = plugin.get_setting('video_quality')

    path = ''

    sources_mp4 = sources.get('mp4')

    if sources_mp4 is None:
        return path

    if (not path or video_quality >= 0) and sources_mp4.get('low'):
        path = sources_mp4['low']
    if (not path or video_quality >= 0) and sources_mp4.get('low-wide'):
        path = sources_mp4['low-wide']

    if (not path or video_quality >= 1) and sources_mp4.get('medium'):
        path = sources_mp4['medium']
    if (not path or video_quality >= 1) and sources_mp4.get('medium-wide'):
        path = sources_mp4['medium-wide']

    if (not path or video_quality >= 2) and sources_mp4.get('high-wide'):
        path = sources_mp4['high-wide']
    if (not path or video_quality >= 2) and sources_mp4.get('high'):
        path = sources_mp4['high']

    if (not path or video_quality >= 3) and sources_mp4.get('hd'):
        path = sources_mp4['hd']
    if (not path or video_quality >= 3) and sources_mp4.get('hd-wide'):
        path = sources_mp4['hd-wide']

    if (not path or video_quality >= 4) and sources_mp4.get('fhd'):
        path = sources_mp4['fhd']
    if (not path or video_quality >= 4) and sources_mp4.get('fhd-wide'):
        path = sources_mp4['fhd-wide']

    return path


if __name__ == '__main__':
    plugin.run()

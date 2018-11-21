# -*- coding: utf-8 -*-
# Module: default
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import xbmc
import xbmcgui
import xbmcplugin

from simpleplugin import Plugin, SimplePluginError

from resources.lib.russiatv1 import *

# Create plugin instance
plugin = Plugin()
_ = plugin.initialize_gettext()

def _init_api():
    settings_list = ['video_quality']

    settings = {}
    for id in settings_list:
        settings[id] = plugin.get_setting(id)

    return RussiaTv(settings)

def _show_api_error(err):
    plugin.log_error(err)
    try:
        text = _(str(err))
    except SimplePluginError:
        text = str(err)

    xbmcgui.Dialog().notification(plugin.addon.getAddonInfo('name'), text, xbmcgui.NOTIFICATION_ERROR)

def _show_notification(text):
    xbmcgui.Dialog().notification(plugin.addon.getAddonInfo('name'), text)

def _get_request_params( params ):
    result = {}
    for param in params:
        if param[0] == '_':
            result[param[1:]] = params[param]
    return result

def _remove_param(params, name):
    if params.get(name):
        del params[name]

@plugin.action()
def root():
    return plugin.create_listing(_list_root(), content='files')

def _list_root():

    items = []
    try:
        for category in _get_categories():
            params = {'cat':     'category',
                      '_cat_id': category['cat_id']
                      }
            items.append( {'action': 'list_videos', 'label': category['label'], 'params': params} )
    except RussiaTvApiError as err:
        _show_api_errosr(err)

    items.append({'action': 'search_history', 'label': _('Search'), 'icon': _get_image('DefaultAddonsSearch.png')})

    for item in items:
        params = item.get('params', {})
        url = plugin.get_url(action=item['action'], **params)

        item_icon = item.get('icon')
        if not item_icon:
            item_icon = plugin.icon

        list_item = {'label': item['label'],
                     'url': url,
                     'icon': item_icon,
                     'fanart': plugin.fanart,
                     'content_lookup': False,
                     }
        yield list_item


@plugin.mem_cached(180)
def _get_categories():
    result = []
    categories = _api.get_categories()
    for category in categories:
        cat_info = {'label': category['title'],
                    'cat_id': ':'.join(category['tags'])
                    }
        result.append(cat_info)

    return result

def _get_category_title(cat_id):
    try:
        for category in _get_categories():
            if category['cat_id'] == cat_id:
                return category['label']
    except RussiaTvApiError as err:
        _show_api_error(err)

    return None

def _join(str, parts):
    new_parts = []
    for val in parts:
        if isinstance(val, unicode):
            new_parts.append(val.encode('utf-8'))
        else:
            new_parts.append(val)

    return str.join(new_parts)

#list_videos
@plugin.action()
def list_videos( params ):
    cur_cat  = params['cat']
    cur_offset = int(params.get('_offset', '0'))
    content = _get_category_content(cur_cat)
    usearch = (params.get('usearch') == 'True')

    if usearch:
        params['_limit'] = 9999
    elif params.get('_limit') is None:
        params['_limit'] = plugin.limit

    if not usearch \
      and plugin.use_atl_names \
      and params.get('_atl') is None:
        params['_atl'] = plugin.use_atl_names

    if not usearch\
      and params.get('_sort') is None:
        params['_sort'] = 'date'

    update_listing = (params.get('update_listing')=='True')
    if update_listing:
        del params['update_listing']
    else:
        update_listing = (cur_offset > 0)

    dir_params = {}
    dir_params.update(params)
    del dir_params['action']
    if cur_offset > 0:
        del dir_params['_offset']

    try:
        video_list = _get_video_list(cur_cat, _get_request_params(params))
        succeeded = True
    except RussiaTvApiError as err:
        _show_api_error(err)
        succeeded = False
        return

    category_title = []
    if cur_cat in ['category', 'search']:
        category_title.append('%s %d / %d' % (_('Page'), (cur_offset + 1), video_list['pages']))

        if cur_cat == 'category':
            title = _get_category_title(params.get('_cat_id', ''))
        elif cur_cat == 'search':
            title = _('Search')

        if title is not None:
            category_title.append(title)

    elif  cur_cat == 'episodes':
        category_title.append(video_list.get('title'))
    category = _join(' / ', category_title)

    if succeeded:
        listing = _make_video_list(video_list, params, dir_params)
    else:
        listing = []

    sort_methods = _get_sort_methods(cur_cat, params.get('_sort', ''))

    return plugin.create_listing(listing, content=content, succeeded=succeeded, update_listing=update_listing, category=category, sort_methods=sort_methods)

def _get_category_content( cat ):
    if cat == 'episodes':
        content = 'episodes'
    elif cat in ['category', 'search']:
        content = 'movies'
    else:
        content = 'files'

    return content

def _get_sort_methods( cat, sort='' ):
    sort_methods = []

    if cat == 'episodes' \
      and not plugin.use_atl_names:
        if sort == 'date':
            sort_methods.append(xbmcplugin.SORT_METHOD_DATE)
        else:
            sort_methods.append(xbmcplugin.SORT_METHOD_EPISODE)
    elif cat == 'search':
        sort_methods.append({'sortMethod': xbmcplugin.SORT_METHOD_UNSORTED, 'label2Mask': '%Y'})
        sort_methods.append(xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        sort_methods.append({'sortMethod': xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE, 'label2Mask': '%Y'})
    elif cat == 'category':
        sort_methods.append({'sortMethod': xbmcplugin.SORT_METHOD_UNSORTED, 'label2Mask': '%Y'})
    else:
        sort_methods.append(xbmcplugin.SORT_METHOD_UNSORTED)

    return sort_methods

def _get_video_list( cat, params ):
    video_list = _api.get_video_list(cat, params)

    return video_list

def _make_video_list( video_list, params={}, dir_params = {} ):
    cur_cat = params.get('cat', '')
    keyword = params.get('_keyword', '')
    cur_offset = int(params.get('_offset', '0'))
    use_atl_names = (str(params.get('_atl','')) == 'True')

    count = video_list['count']
    total_pages = video_list.get('pages', 0)
    if params.get('_limit') is None \
     and video_list.get('limit') is not None:
        params['_limit'] = video_list['limit']

    search = (cur_cat == 'search')
    usearch = (params.get('usearch') == 'True')

    use_filters  = not usearch and (cur_cat in ['category'])
    use_pages    = not usearch and total_pages

    if use_filters:
        filters = get_filters()
        if params.get('_cat_id', '') != '':
            yield _make_filter_item('sort', params, dir_params, filters)

    if video_list['count']:
        for video_item in video_list['list']:
            yield _make_item(video_item, search, use_atl_names)

    elif not usearch:
        item_info = {'label': _make_colour_label('red', '[%s]' % _('Empty')),
                     'is_folder': False,
                     'is_playable': False,
                     'url': ''}
        yield item_info

    if use_pages:
        if cur_offset > 0:
            if cur_offset == 1:
                del params['_offset']
            else:
                params['_offset'] = cur_offset - 1
            url = plugin.get_url(**params)
            item_info = {'label': _('Previous page...'),
                         'url':   url}
            yield item_info

        if (cur_offset + 1) < total_pages:
            params['_offset'] = cur_offset + 1
            url = plugin.get_url(**params)
            item_info = {'label': _('Next page...'),
                         'url':   url}
            yield item_info

def _make_filter_item( filter, params, dir_params, filters ):
    cur_value = params.get('_%s' % filter, '')

    filter_title = _get_filter_title(filter)
    url = plugin.get_url(action='select_filer', filter = filter, **dir_params)
    label = _make_category_label('yellowgreen', filter_title, _get_filter_name(filters[filter], cur_value))
    list_item = {'label': label,
                 'is_folder':   False,
                 'is_playable': False,
                 'url': url,
                 'icon': _get_filter_icon(filter),
                 'fanart': plugin.fanart,
                 'content_lookup': False,
                 }

    return list_item

def _get_filter_title( filter ):
    result = ''
    if filter =='sort': result = _('Sort')

    return result

def _get_filter_icon( filter ):
    image = ''
    if filter =='sort': image = _get_image('DefaultMovieTitle.png')

    if not image:
        image = plugin.icon

    return image

def _make_item( video_item, search, use_atl_names=False ):
        label_list = []

        video_type = video_item['video_info']['type']

        item_info = video_item['item_info']
        video_info = video_item['video_info']

        if video_type == 'movie':
            is_folder = False
            is_playable = True

            url_params = {'_type': video_type,
                          '_brand_id': video_info['brand_id'],
                          }
            url = plugin.get_url(action='play', **url_params)

            if use_atl_names:
                title = item_info['info']['video']['originaltitle']
            else:
                title = item_info['info']['video']['title']

            label_list.append(title)

            if use_atl_names \
              and isinstance(item_info['info']['video']['year'], int):
                label_list.append(' (%d)' % item_info['info']['video']['year'])

            if use_atl_names or search:
                del item_info['info']['video']['title']

        elif video_type == 'tvshow':
            is_folder = True
            is_playable = False

            url_params = {'_brand_id': video_info['brand_id'],
                          '_sort': video_info['sort'],
                          }
            if use_atl_names:
                url_params['_atl'] = use_atl_names

            url = plugin.get_url(action='list_videos', cat='episodes', **url_params)

            if use_atl_names:
                title = item_info['info']['video']['originaltitle']
            else:
                title = item_info['info']['video']['title']
            label_list.append(title)

            if use_atl_names \
              and isinstance(item_info['info']['video']['year'], int):
                label_list.append(' (%d)' % item_info['info']['video']['year'])

        elif video_type == 'episode':
            is_folder = False
            is_playable = True

            url_params = {'_type': video_type,
                          '_brand_id': video_info['brand_id'],
                          '_video_id': video_info['video_id'],
                          }
            url = plugin.get_url(action='play', **url_params)

            if use_atl_names:
                title = video_info['originaltitle']
                if video_info['season'] != 0:
                    season_string = '-%d' % video_info['season']
                    if title.endswith(season_string):
                        title = title[0:-len(season_string)]
                label_list.append(title)
                label_list.append('.s%02de%02d' % (video_info['season'], video_info['episode']))
                if item_info['info']['video']['title']:
                    label_list.append('.%s' % (item_info['info']['video']['title']))
            else:
                if not item_info['info']['video']['title']:
                    item_info['info']['video']['title'] = '%s %d' % (_('Episode').decode('utf-8'), video_info['episode'])
                label_list.append(item_info['info']['video']['title'])

            if use_atl_names:
                del item_info['info']['video']['title']

        item_info['label'] = _join('', label_list)
        item_info['url'] = url
        item_info['is_playable'] = is_playable
        item_info['is_folder'] = is_folder

        if video_info.get('have_trailer') \
          and video_info['have_trailer']:
            url_params = {'_type': video_type,
                          '_brand_id': video_info['brand_id'],
                          }
            trailer_url = plugin.get_url(action='trailer', **url_params)
            item_info['info']['video']['trailer'] = trailer_url

        _backward_capatibility(item_info)

        return item_info

def _backward_capatibility( item_info ):
    major_version = xbmc.getInfoLabel('System.BuildVersion')[:2]

    cast = []
    castandrole = []
    for _cast in item_info.get('cast',[]):
        cast.append(_cast['name'])
        castandrole.append((_cast['name']))
    item_info['info']['video']['cast'] = cast
    item_info['info']['video']['castandrole'] = castandrole

    if major_version < '18':
        for fields in ['genre', 'writer', 'director', 'country', 'credits']:
            item_info['info']['video'][fields] = _join(' / ', item_info['info']['video'].get(fields,[]))

    if major_version < '15':
        item_info['info']['video']['duration'] = (item_info['info']['video'].get('duration', 0) / 60)

def _make_category_label( color, title, category ):
    label_parts = []
    label_parts.append('[COLOR=%s][B]' % color)
    label_parts.append(title)
    label_parts.append(':[/B] ')
    label_parts.append(category)
    label_parts.append('[/COLOR]')
    return _join('', label_parts)

def _make_colour_label( color, title ):
    label_parts = []
    label_parts.append('[COLOR=%s][B]' % color)
    label_parts.append(title)
    label_parts.append('[/B][/COLOR]')
    return _join('', label_parts)

def _get_image( image ):
    return image if xbmc.skinHasImage(image) else plugin.icon

def get_filters():
    sort = []
    sort.append({'name': _('By release date'),
                 'value': 'date'
                 })
    sort.append({'name': _('By alphabet'),
                 'value': 'alpha'
                 })

    result = {'sort': sort,
              }
    return result

def _get_filter_name( list, value ):
    for item in list:
        if item['value'] == value:
            return item['name']

@plugin.action()
def search( params ):

    keyword  = params.get('keyword', '')
    usearch  = (params.get('usearch') == 'True')

    new_search = (keyword == '')
    succeeded = False

    if not keyword:
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(_('Search'))
        kbd.doModal()
        if kbd.isConfirmed():
            keyword = kbd.getText()

    if keyword \
      and new_search \
      and not usearch:
        with plugin.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])
            history.insert(0, {'keyword': keyword.decode('utf-8')})
            if len(history) > plugin.history_length:
                history.pop(-1)
            storage['history'] = history

        params['keyword'] = keyword
        url = plugin.get_url(**params)
        xbmc.executebuiltin('Container.Update("%s")' % url)
        return

    if keyword:
        succeeded = True
        params['action'] = 'list_videos'
        params['cat'] = 'search'
        params['_keyword'] = keyword
        params['_full_list'] = not usearch
        return list_videos(params)

@plugin.action()
def search_history():

    with plugin.get_storage('__history__.pcl') as storage:
        history = storage.get('history', [])

        if len(history) > plugin.history_length:
            history[plugin.history_length - len(history):] = []
            storage['history'] = history

    listing = []
    listing.append({'label': _('New Search...'),
                    'url': plugin.get_url(action='search'),
                    'icon': _get_image('DefaultAddonsSearch.png'),
                    'fanart': plugin.fanart})

    for item in history:
        listing.append({'label': item['keyword'],
                        'url': plugin.get_url(action='search', keyword=item['keyword'].encode('utf-8')),
                        'icon': plugin.icon,
                        'fanart': plugin.fanart})

    return plugin.create_listing(listing, content='files')

@plugin.action()
def select_filer( params ):
    filter = params['filter']
    filter_name = filter
    filter_title = _get_filter_title(filter)
    filter_key = '_%s' % filter

    list = get_filters()[filter]

    titles = []
    for list_item in list:
        titles.append(list_item['name'])

    ret = xbmcgui.Dialog().select(filter_title, titles)
    if ret >= 0:
        filter_value = list[ret]['value']
        if not filter_value and params.get(filter_key):
            del params[filter_key]
        else:
            params[filter_key] = filter_value

        del params['action']
        del params['filter']

        _remove_param(params, '_offset')

        url = plugin.get_url(action='list_videos', update_listing=True, **params)
        xbmc.executebuiltin('Container.Update("%s")' % url)

@plugin.action()
def play( params ):

    u_params = _get_request_params( params )

    try:
        item = _api.get_video_url( u_params )
        succeeded = True
        if u_params['type'] == 'episode' \
           and not item['info']['video']['title']:
            item['info']['video']['title'] = '%s %d' % (_('Episode').decode('utf-8'), item['info']['video']['episode'])
    except RussiaTvApiError as err:
        _show_api_error(err)
        item = None
        succeeded = False

    return plugin.resolve_url(play_item=item, succeeded=succeeded)

@plugin.action()
def trailer( params ):

    u_params = _get_request_params( params )
    try:
        path = _api.get_trailer_url( u_params )
        succeeded = True
    except RussiaTvApiError as err:
        _show_api_error(err)
        path = ""
        succeeded = False

    return plugin.resolve_url(path=path, succeeded=succeeded)

if __name__ == '__main__':
    _api = _init_api()
    plugin.run()
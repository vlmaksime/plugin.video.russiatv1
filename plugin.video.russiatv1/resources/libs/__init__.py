# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import simplemedia
import xbmc
import os

from .listitems import BrandInfo, SeasonInfo, VideoInfo, EmptyListItem, ListItem
from .russiatv1 import RussiaTvClient, RussiaTvError

__all__ = ['RussiaTv', 'RussiaTvError',
           'BrandInfo', 'SeasonInfo', 'VideoInfo', 'EmptyListItem', 'ListItem']

addon = simplemedia.Addon()


class RussiaTv(RussiaTvClient):

    def __init__(self):
        params = {'channels': 1,
                  }

        super(RussiaTv, self).__init__(**params)

        headers = self._client.headers
        if addon.kodi_major_version() >= '17':
            headers['User-Agent'] = xbmc.getUserAgent()

        cookie_file = os.path.join(addon.profile_dir, 'russiatv.cookies')

        self._client = simplemedia.WebClient(headers, cookie_file)

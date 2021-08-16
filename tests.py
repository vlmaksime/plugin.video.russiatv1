# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import imp
import os
import shutil
import sys
import unittest

import mock
import simplemedia
import simpleplugin
import xbmcaddon
import xbmc

cwd = os.path.dirname(os.path.abspath(__file__))

addon_name = 'plugin.video.russiatv1'
sm_name = 'script.module.simplemedia'

temp_dir = os.path.join(cwd, 'addon_data')

if not os.path.exists(temp_dir):
    os.mkdir(temp_dir)

sm_dir = simplemedia.where()
sm_config_dir = os.path.join(temp_dir, sm_name)
xbmcaddon.init_addon(sm_dir, sm_config_dir)

addon_dir = os.path.join(cwd, addon_name)
addon_config_dir = os.path.join(temp_dir, addon_name)
xbmcaddon.init_addon(addon_dir, addon_config_dir, True)

# Import our module being tested
sys.path.append(addon_dir)


def run_script():
    imp.load_source('__main__', os.path.join(addon_dir, 'default.py'))


def setUpModule():
    # Prepare search history
    addon = simpleplugin.Addon()
    with addon.get_storage('__history__.pcl') as storage:
        history = ['Вести', 'Доктор Рихтер']
        storage['history'] = history


def tearDownModule():
    print('Removing temporary directory: {0}'.format(temp_dir))
    shutil.rmtree(temp_dir, True)


class PluginActionsTestCase(unittest.TestCase):

    def setUp(self):
        print("Running test: {0}".format(self.id().split('.')[-1]))

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/'.format(addon_name), '1', ''])
    def test_01_root():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/menu/265/'.format(addon_name), '2', '?offset=20&limit=10'])
    def test_02_menu_serialy():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/menu/267/'.format(addon_name), '3', ''])
    def test_03_menu_kino():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/brand/9361/videos/'.format(addon_name), '4', ''])
    def test_04_brand_seasons():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/brand/9361/videos/'.format(addon_name), '5',
                                          '?limit=100&offset=0'])
    def test_05_brand_episodes():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/videos/1988947/'.format(addon_name), '6', ''])
    def test_06_play_movie():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/videos/2248791/'.format(addon_name), '7', ''])
    def test_07_play_episode():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/videos/2221459/'.format(addon_name), '8', ''])
    def test_08_play_trailer():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/menu/267/'.format(addon_name), '9', '?atl=1'])
    def test_09_menu_kino_atl():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/brand/9361/videos/'.format(addon_name), '10',
                                          '?limit=100&offset=0&atl=1'])
    def test_10_brand_episodes_atl():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/search/'.format(addon_name), '11', ''])
    def test_11_search_keyboard():
        xbmc.Keyboard.strings.append('Ми-ми-мишки')
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/search/'.format(addon_name), '12', '?keyword=Тайны следствия'])
    def tes1t_12_search_keyword():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/search/history/'.format(addon_name), '13', ''])
    def test_13_search_history():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/search/remove/0'.format(addon_name), '14', ''])
    def test_14_search_remove():
        run_script()

    @staticmethod
    @mock.patch('simpleplugin.sys.argv', ['plugin://{0}/search/clear'.format(addon_name), '15', ''])
    def test_15_search_clear():
        run_script()


if __name__ == '__main__':
    unittest.main()

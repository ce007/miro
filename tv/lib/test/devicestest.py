# Miro - an RSS based video player application
# Copyright (C) 2010, 2011
# Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.

import os
try:
    import simplejson as json
except ImportError:
    import json

import sqlite3

from miro.gtcache import gettext as _
from miro.plat.utils import PlatformFilenameType
from miro.test.framework import MiroTestCase
from miro.test import mock

from miro import devices
from miro import item
from miro import storedatabase

class DeviceManagerTest(MiroTestCase):
    def build_config_file(self, filename, data):
        fn = os.path.join(self.tempdir, filename)
        fp = open(fn, "w")
        fp.write(data)
        fp.close()

    def test_empty(self):
        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, "*.py"))
        self.assertRaises(KeyError, dm.get_device, "py")
        self.assertRaises(KeyError, dm.get_device_by_id, 0, 0)

    def test_parsing(self):
        self.build_config_file(
            "foo.py",
            """from miro.gtcache import gettext as _
from miro.devices import DeviceInfo, MultipleDeviceInfo
defaults = {
    "audio_conversion": "mp3",
    "container_types": "isom mp3".split(),
    "audio_types": "mp3 aac".split(),
    "video_types": ["h264"],
    "mount_instructions": _("Mount Instructions\\nOver multiple lines"),
    "video_path": u"Video",
    "audio_path": u"Audio",
    }
target1 = DeviceInfo("Target1",
                     vendor_id=0x890a,
                     product_id=0xbcde,
                     device_name="Bar",
                     video_conversion="mp4",
                     **defaults)
target2 = DeviceInfo('Target2',
                     video_conversion="mp4")
target3 = DeviceInfo('Target3',
                     video_conversion="mp4")
multiple = MultipleDeviceInfo('Foo', [target2, target3],
                              vendor_id=0x1234,
                              product_id=0x4567,
                              **defaults)
devices = [target1, multiple]
""")

        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, "*.py"))

        # a single device
        device = dm.get_device("Bar")
        self.assertEqual(repr(device),
                         "<DeviceInfo 'Target1' 'Bar' 890a bcde>")
        # this comes from the section name
        self.assertEqual(device.name, "Target1")
        # this comes from the default
        self.assertEqual(device.audio_conversion, "mp3")
        # this comes from the section
        self.assertEqual(device.device_name, 'Bar')
        self.assertEqual(device.video_conversion, "mp4")
        self.assertEqual(device.audio_path, 'Audio')
        self.assertTrue(isinstance(device.audio_path, PlatformFilenameType))
        self.assertEqual(device.video_path, 'Video')
        self.assertTrue(isinstance(device.video_path, PlatformFilenameType))
        # these are a special case
        self.assertFalse(device.has_multiple_devices)
        self.assertEqual(device.mount_instructions,
                         _('Mount Instructions\nOver multiple lines'))
        self.assertEqual(device.container_types, ['mp3', 'isom'])
        self.assertEqual(device.audio_types, ['mp3', 'aac'])
        self.assertEqual(device.video_types, ['h264'])

        # both devices have the same ID
        device = dm.get_device_by_id(0x1234, 0x4567)
        self.assertTrue(device.has_multiple_devices)
        self.assertEquals(device.name, 'Foo')
        self.assertEquals(device.device_name, 'Foo')
        self.assertEquals(device.vendor_id, 0x1234)
        self.assertEquals(device.product_id, 0x4567)
        self.assertEqual(device.mount_instructions,
                         _('Mount Instructions\nOver multiple lines'))

        single = device.get_device('Target2')
        self.assertFalse(single.has_multiple_devices)
        self.assertEqual(single.name, 'Target2')

    def test_invalid_device(self):
        self.build_config_file(
            "foo.py",
            """from miro.devices import DeviceInfo
target1 = DeviceInfo("Target1")
devices = [target1]
""")
        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, "*.py"))
        self.assertRaises(KeyError, dm.get_device, "Target1")
        self.assertRaises(KeyError, dm.get_device_by_id, 0, 0)

    def test_generic_device(self):
        self.build_config_file(
            "foo.py",
            """from miro.devices import DeviceInfo
target1 = DeviceInfo("Target1",
                     device_name='Foo*',
                     vendor_id=0x1234,
                     product_id=None,
                     video_conversion="hero",
                     audio_conversion="mp3",
                     container_types="isom mp3".split(),
                     audio_types="mp3 aac".split(),
                     video_types=["h264"],
                     mount_instructions=u"",
                     video_path=u"Video",
                     audio_path=u"Audio")
devices = [target1]
""")
        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, '*.py'))
        device = dm.get_device('Foo Bar')
        self.assertEqual(device.name, "Target1")
        device = dm.get_device_by_id(0x1234, 0x4567)
        self.assertEqual(device.name, "Target1")

    def test_multiple_device_gets_data_from_first_child(self):
        """
        If a MultipleDeviceInfo object is created without all the appropriate
        data, it will grab it from its first child.
        """
        self.build_config_file(
            "foo.py",
            """from miro.devices import DeviceInfo, MultipleDeviceInfo
defaults = {
    "audio_conversion": "mp3",
    "container_types": "mp3 isom".split(),
    "audio_types": "mp3 aac".split(),
    "video_types": ["h264"],
    "mount_instructions": "Mount Instructions\\nOver multiple lines",
    "video_path": u"Video",
    "audio_path": u"Audio",
    }
target1 = DeviceInfo("Target1",
                     vendor_id=0x890a,
                     product_id=0xbcde,
                     video_conversion="mp4",
                     **defaults)
target2 = DeviceInfo("Target2")
multiple = MultipleDeviceInfo('Foo', [target1, target2])
devices = [multiple]
""")
        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, '*.py'))
        device = dm.get_device('Foo')
        self.assertTrue(device.has_multiple_devices)
        self.assertEqual(device.video_conversion, "mp4")

    def test_multiple_device_info_single(self):
        """
        If a MultipleDeviceInfo has only one child, get_device() should just
        return the single child.
        """
        self.build_config_file(
            "foo.py",
            """from miro.devices import DeviceInfo, MultipleDeviceInfo
defaults = {
    "audio_conversion": "mp3",
    "container_types": "mp3 isom".split(),
    "audio_types": "mp3 aac".split(),
    "video_types": ["h264"],
    "mount_instructions": "Mount Instructions\\nOver multiple lines",
    "video_path": u"Video",
    "audio_path": u"Audio",
    }
target1 = DeviceInfo("Target1",
                     vendor_id=0x890a,
                     product_id=0xbcde,
                     video_conversion="mp4",
                     **defaults)
multiple = MultipleDeviceInfo('Foo', [target1])
devices = [multiple]
""")
        dm = devices.DeviceManager()
        dm.load_devices(os.path.join(self.tempdir, '*.py'))
        device = dm.get_device('Foo')
        self.assertFalse(device.has_multiple_devices)
        self.assertEqual(device.name, "Target1")
        self.assertEqual(device.device_name, "Foo")

class DeviceHelperTest(MiroTestCase):

    def test_load_database(self):
        data = {u'a': 2,
                u'b': {u'c': [5, 6]}}
        os.makedirs(os.path.join(self.tempdir, '.miro'))
        with open(os.path.join(self.tempdir, '.miro', 'json'), 'w') as f:
            json.dump(data, f)

        ddb = devices.load_database(self.tempdir)
        self.assertEqual(dict(ddb), data)
        self.assertEqual(len(ddb.get_callbacks('changed')), 1)

    def test_load_database_missing(self):
        ddb = devices.load_database(self.tempdir)
        self.assertEqual(dict(ddb), {})
        self.assertEqual(len(ddb.get_callbacks('changed')), 1)

    def test_load_database_error(self):
        os.makedirs(os.path.join(self.tempdir, '.miro'))
        with open(os.path.join(self.tempdir, '.miro', 'json'), 'w') as f:
            f.write('NOT JSON DATA')

        ddb = devices.load_database(self.tempdir)
        self.assertEqual(dict(ddb), {})
        self.assertEqual(len(ddb.get_callbacks('changed')), 1)


    def test_write_database(self):
        data = {u'a': 2,
                u'b': {u'c': [5, 6]}}
        devices.write_database(data, self.tempdir)
        with open(os.path.join(self.tempdir, '.miro', 'json')) as f:
            new_data = json.load(f)
        self.assertEqual(data, new_data)

class GlobSetTest(MiroTestCase):

    def test_globset_regular_match(self):
        gs = devices.GlobSet('abc')
        self.assertTrue('a' in gs)
        self.assertTrue('A' in gs)
        self.assertTrue('b' in gs)
        self.assertTrue('c' in gs)
        self.assertFalse('d' in gs)
        self.assertFalse('aa' in gs)

    def test_globset_glob_match(self):
        gs = devices.GlobSet(['a*', 'b*'])
        self.assertTrue('a' in gs)
        self.assertTrue('AB' in gs)
        self.assertTrue('b' in gs)
        self.assertTrue('ba' in gs)
        self.assertFalse('c' in gs)

    def test_globset_both_match(self):
        gs = devices.GlobSet(['a', 'b*'])
        self.assertTrue('a' in gs)
        self.assertTrue('b' in gs)
        self.assertTrue('ba' in gs)
        self.assertFalse('ab' in gs)
        self.assertFalse('c' in gs)

    def test_globset_and(self):
        gs = devices.GlobSet(['a', 'b*'])
        self.assertTrue(gs & set('a'))
        self.assertTrue(gs & set('b'))
        self.assertTrue(gs & set('bc'))
        self.assertTrue(gs & set(['bc', 'c']))
        self.assertFalse(gs & set('cd'))

    def test_globset_and_plain(self):
        gs = devices.GlobSet('ab')
        self.assertTrue(gs & set('a'))
        self.assertTrue(gs & set('b'))
        self.assertTrue(gs & set('ab'))
        self.assertTrue(gs & set('bc'))
        self.assertFalse(gs & set('cd'))

class DeviceDatabaseTest(MiroTestCase):
    "Test sqlite databases on devices."""
    def setUp(self):
        MiroTestCase.setUp(self)
        self.device = mock.Mock()
        self.device.database = devices.DeviceDatabase()
        self.device.database[u'audio'] = {}
        self.device.mount = self.tempdir
        self.device.id = 123
        self.device.name = 'Device'
        self.device.size = 1024000
        os.makedirs(os.path.join(self.device.mount, '.miro'))

    def open_database(self):
        sqlite_db = devices.load_sqlite_database(self.device.mount,
                                                 self.device.database,
                                                 self.device.size)
        metadata_manager = devices.make_metadata_manager(self.device.mount,
                                                         sqlite_db,
                                                         self.device.id)
        self.device.sqlite_database = sqlite_db
        self.device.metadata_manager = metadata_manager

    def make_device_items(self, *filenames):
        for filename in filenames:
            filename = unicode(filename)
            devices.create_item_for_file(self.device, filename, u'audio')

    def test_open(self):
        self.open_database()
        self.assertEquals(self.device.sqlite_database.__class__,
                          storedatabase.LiveStorage)
        self.assertEquals(self.device.sqlite_database.error_handler.__class__,
                          storedatabase.DeviceLiveStorageErrorHandler)

    def test_reload(self):
        self.open_database()
        self.make_device_items('foo.mp3', 'bar.mp3')
        # close, then reopen the database
        self.device.sqlite_database.finish_transaction()
        self.open_database()
        # test that the database is still intact by checking the
        # metadata_status table
        cursor = self.device.sqlite_database.cursor
        cursor.execute("SELECT path FROM metadata_status")
        paths = [r[0] for r in cursor.fetchall()]
        self.assertSameSet(paths, ['foo.mp3', 'bar.mp3'])

    @mock.patch('miro.dialogs.MessageBoxDialog.run_blocking')
    def test_load_error(self, mock_dialog_run):
        # Test an error loading the device database
        def mock_get_last_id():
            if not self.faked_get_last_id_error:
                self.faked_get_last_id_error = True
                raise sqlite3.DatabaseError("Error")
            else:
                return 0
        self.faked_get_last_id_error = False
        self.patch_function('miro.storedatabase.LiveStorage._get_last_id',
                            mock_get_last_id)
        self.open_database()
        # check that we displayed an error dialog
        mock_dialog_run.assert_called_once_with()
        # check that our corrupt database logic ran
        dir_contents = os.listdir(os.path.join(self.device.mount, '.miro'))
        self.assert_('corrupt_database' in dir_contents)

    def test_upgrade_error(self):
        self.open_database()
        self.make_device_items('foo.mp3', 'bar.mp3')
        devices.write_database(self.device.database, self.device.mount)
        # Force our upgrade code to run and throw an exception.
        os.remove(os.path.join(self.device.mount, '.miro', 'sqlite'))
        mock_do_import = mock.Mock()
        method = ('miro.devicedatabaseupgrade.'
                  '_do_import_old_items.convert_old_item')
        patcher = mock.patch(method, mock_do_import)
        mock_do_import.side_effect = sqlite3.DatabaseError("Error")
        self.device.database.created_new = False
        with patcher:
            self.open_database()
        # check that we created a new sqlite database and added new metadata
        # status rows for the device items
        cursor = self.device.sqlite_database.cursor
        cursor.execute("SELECT path FROM metadata_status")
        paths = [r[0] for r in cursor.fetchall()]
        self.assertSameSet(paths, ['foo.mp3', 'bar.mp3'])

    def test_save_error(self):
        # FIXME: what should we do if we have an error saving to the device?
        pass

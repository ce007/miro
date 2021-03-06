# Miro - an RSS based video player application
# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010, 2011
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

"""miro.widgetstate - The state of Widgets frontend UI objects.
See WidgetState design doc in wiki for details.
"""

from miro.database import DDBObject, ObjectNotFoundError

STANDARD_VIEW = 0
LIST_VIEW = 1
# skip over 2 since that's used in the frontend for CUSTOM_VIEW
ALBUM_VIEW = 3

class DisplayState(DDBObject):
    """Properties that are shared across all TableViews for a Display, or only
    used by one (ListView or ItemView)
    """
    def setup_new(self, display):
        self.type = display[0]
        self.id_ = display[1]
        # shared properties
        self.shuffle = None
        self.repeat = None
        self.selected_view = None
        self.selection = None
        self.last_played_item_id = None
        self.active_filters = None
        self.sort_state = None

class ViewState(DDBObject):
    """Properties that need to be stored for each TableView
    """
    def setup_new(self, key):
        self.display_type = key[0]
        self.display_id = key[1]
        self.view_type = key[2]
        self.scroll_position = None
        self.columns_enabled = None
        self.column_widths = None

class GlobalState(DDBObject):
    """Properties that apply globally"""

    @classmethod
    def get_singleton(cls):
        try:
            return cls.make_view().get_singleton()
        except ObjectNotFoundError:
            return cls()

    def setup_new(self):
        self.item_details_expanded = {
                ALBUM_VIEW: False,
                LIST_VIEW: True,
                STANDARD_VIEW: False,
        }
        self.guide_sidebar_expanded = True
        self.tabs_width = 200

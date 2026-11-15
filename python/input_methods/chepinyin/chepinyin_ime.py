#! python3
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from cinbase import LoadCinTable
from cinbase.service import CinBaseTextService, makeTableHolders

CinTable, RCinTable, HCinTable = makeTableHolders()


class ChePinyinTextService(CinBaseTextService):
    """漢語拼音輸入法 (PIME) — thin binding over the shared cinbase body."""

    imeDirName = "chepinyin"
    maxCharLength = 7  # 輸入法最大編碼字元數量
    cinFileList = ["thpinyin.json", "pinyin.json", "roman.json"]

    CinTable = CinTable
    RCinTable = RCinTable
    HCinTable = HCinTable

    def checkConfigChangeState(self):
        if self.cfg.selCinType == 0 or self.cfg.selCinType == 1 or self.cfg.selCinType == 2:
            if not self.useEndKey or not self.endKeyList:
                self.endKeyList = ["1", "2", "3", "4", "5"]
                self.useEndKey = True
        else:
            self.useEndKey = False

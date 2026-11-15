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

from keycodes import *  # for VK_XXX constants

from cinbase.service import CinBaseTextService, makeTableHolders

CinTable, RCinTable, HCinTable = makeTableHolders()


class CheDayiTextService(CinBaseTextService):
    """大易輸入法 (PIME) — thin binding over the shared cinbase body."""

    imeDirName = "chedayi"
    maxCharLength = 4  # 輸入法最大編碼字元數量
    cinFileList = ["thdayi.json", "dayi4.json", "dayi3.json"]

    CinTable = CinTable
    RCinTable = RCinTable
    HCinTable = HCinTable

    def initServiceState(self):
        self.useDayiSymbols = True
        self.selDayiSymbolCharType = 0

    def preKeyDown(self, keyEvent):
        if self.cfg.selCinType == 0 or self.cfg.selCinType == 1:
            self.maxCharLength = 4
        elif self.cfg.selCinType == 2:
            self.maxCharLength = 3

        charCode = keyEvent.charCode
        keyCode = keyEvent.keyCode
        charStr = chr(charCode)

        # 大易符號 ---------------------------------------------------------
        self.DayiSymbolChar = "=" if self.selDayiSymbolCharType == 0 else "'"
        self.DayiSymbolString = "＝" if self.selDayiSymbolCharType == 0 else "號"

        if self.langMode == 1 and not self.showmenu:
            if len(self.compositionChar) == 0 and not self.phrasemode and charStr == self.DayiSymbolChar and not keyEvent.isKeyDown(VK_CONTROL):
                self.compositionChar += charStr
                self.dayisymbolsmode = True
                if self.compositionBufferMode:
                    self.cinbase.setCompositionBufferString(self, self.DayiSymbolString, 0)
                else:
                    self.setCompositionString(self.DayiSymbolString)
            elif self.dayisymbolsmode and self.isShowCandidates:
                self.canUseSelKey = True
            elif len(self.compositionChar) >= 1 and self.dayisymbolsmode:
                if self.dsymbols.isInCharDef(self.compositionChar[1:] + charStr):
                    self.compositionChar += charStr
                    self.canUseSelKey = False
                    self.dsymbols.getCharDef(self.compositionChar[1:])
                elif keyCode == VK_SPACE or keyCode == VK_RETURN or keyCode == VK_ESCAPE:
                    self.dayisymbolsmode = False
                    self.cinbase.resetComposition(self)

        if not self.directShowCand:
            self.autoShowCandWhenMaxChar = True

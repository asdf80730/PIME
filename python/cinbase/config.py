#! python3
# Copyright (C) 2016 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
#
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

import json
import os
import time

from pimepaths import appdata
import shutil

DEF_FONT_SIZE = 12
DEF_FONT_NAME = 'MingLiu'
# LOGFONT 重量：400 = FW_NORMAL，即選字視窗字型建立時已帶的粗細 (issue #854)
DEF_FONT_WEIGHT = 400
DEF_LEAD_IN_KEY = '`'

SWITCH_LANG_WITH_BOTH_SHIFT = 0
SWITCH_LANG_WITH_LEFT_SHIFT = 1
SWITCH_LANG_WITH_RIGHT_SHIFT = 2

# 選字鍵列 (issue #463/#539)：索引 0 是歷來的預設 1-based 列，
# 索引 1 是 0-based 列，讓嘸蝦米这类要用 0-9 的碼表能選到第十個候選字。
selKeys=(
    "1234567890",
    "0123456789"
)

class CinBaseConfig:

    def __init__(self):
        self.candPerRow = 3
        self.defaultEnglish = False
        self.defaultFullSpace = False
        self.disableOnStartup = False
        self.switchLangWithShift = True
        self.switchLangWithWhichShift = SWITCH_LANG_WITH_BOTH_SHIFT
        self.outputSmallLetterWithShift = False
        self.shiftLetterSwitchToEnglish = False
        # Shift+空白鍵切換全形/半形 (issue #844)，與新酷音同名設定
        self.enableShiftSpace = True
        self.switchPageWithSpace = False
        self.outputSimpChinese = False
        self.enableSwitchTCSC = True
        self.messageDurationTime = 3
        self.hidePromptMessages = True
        self.autoClearCompositionChar = False
        self.playSoundWhenNonCand = False
        self.directShowCand = False
        self.directCommitSymbol = False
        self.fontSize = DEF_FONT_SIZE
        # 選字及訊息視窗的字型 (issue #582)
        self.candFontName = DEF_FONT_NAME
        # 選字及訊息視窗的字型粗細 (issue #854)：LOGFONT 重量 1-900
        self.candFontWeight = DEF_FONT_WEIGHT
        # 組字/選字視窗顏色 (issue #902)：0 表示跟隨系統調色盤
        self.candTextColor = 0
        self.windowBackgroundColor = 0
        self.selKeyColor = 0
        # 多功能前導字元 (issue #525)
        self.leadInKey = DEF_LEAD_IN_KEY
        # 按住 Ctrl + 符號鍵輸入特殊符號 (issue #826)
        self.enableCtrlSymbols = True
        self.selCinType = 0
        self.ignorePrivateUseArea = True
        self.selKeyType = 0
        self.candPerPage = 9
        self.cursorCandList = True
        self.fullShapeSymbols = False
        self.directOutFSymbols = False
        self.directOutMSymbols = True
        self.easySymbolsWithShift = False
        self.showPhrase = False
        self.sortByPhrase = True
        self.supportWildcard = True
        self.compositionBufferMode = False
        self.autoMoveCursorInBrackets = False
        self.selWildcardType = 0
        self.imeReverseLookup = False
        self.homophoneQuery = False
        self.selHCinType = 0
        self.userExtendTable = False
        self.reLoadTable = False
        self.priorityExtendTable = False
        self.selRCinType = 0
        self.candMaxItems = 100
        self.messageDurationTime = 3
        self.keyboardType = 0
        self.selDayiSymbolCharType = 0
        self.intelligentSelect = True
        self.intelligentSelectRecent = True
        self.intelligentSelectContext = True

        self.ignoreSaveList = ["ignoreSaveList", "curdir", "cinFileList", "selCinFile", "imeDirName", "_version", "_lastUpdateTime"]
        self.curdir = os.path.abspath(os.path.dirname(__file__))
        self.cinFileList = []
        self.selCinFile = ""
        self.imeDirName = ""

        # version: last modified time of (config.json, symbols.dat, swkb.dat, fsymbols.dat, flangs.dat, userphrase.dat)
        self._version = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self._lastUpdateTime = 0.0

    def getConfigDir(self):
        config_dir = os.path.join(appdata(), "PIME", self.imeDirName)
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def getConfigFile(self, name="config.json"):
        return os.path.join(self.getConfigDir(), name)

    def getSelKeys(self):
        # 選字鍵列的單一來源：索引超出時退回預設的 1-based 列
        try:
            index = int(self.selKeyType)
        except (ValueError, TypeError):
            index = 0
        if index < 0 or index >= len(selKeys):
            index = 0
        return selKeys[index]

    def getLastTime(self):
        return self._lastTime

    def load(self):
        # Layer 1: apply shipped defaults so new keys reach all users regardless of
        # whether they already have an APPDATA config from a previous install.
        default_config = os.path.join(self.getDefaultConfigDir(), "config.json")
        try:
            if os.path.exists(default_config) and os.stat(default_config).st_size > 0:
                with open(default_config, "r") as f:
                    self.__dict__.update(json.load(f))
        except Exception:
            pass

        # Layer 2: overlay with the user's personal config (APPDATA or legacy home-dir path).
        filename = self.getConfigFile()
        try:
            if not os.path.exists(filename) or os.stat(filename).st_size == 0:
                filename = os.path.join(os.path.expanduser("~"), "PIME", self.imeDirName, "config.json")

                if not os.path.exists(filename) or os.stat(filename).st_size == 0:
                    filename = None
                else:
                    src_dir = os.path.join(os.path.expanduser("~"), "PIME", self.imeDirName)
                    dst_dir = self.getConfigDir()
                    self.copytree(src_dir, dst_dir)
                    filename = self.getConfigFile()

            if filename:
                with open(filename, "r") as f:
                    self.__dict__.update(json.load(f))
        except Exception:
            self.save()
        self.sanitize()
        self.update()

    def sanitize(self):
        def _to_int(val, default, min_val=None, max_val=None):
            try:
                i = int(val)
                if min_val is not None and i < min_val:
                    return default
                if max_val is not None and i > max_val:
                    return default
                return i
            except (ValueError, TypeError):
                return default

        self.candPerPage = _to_int(getattr(self, "candPerPage", 9), 9, min_val=1, max_val=10)
        self.candPerRow = _to_int(getattr(self, "candPerRow", 1), 1, min_val=1, max_val=10)
        self.fontSize = _to_int(getattr(self, "fontSize", DEF_FONT_SIZE), DEF_FONT_SIZE, min_val=6, max_val=200)
        self.candMaxItems = _to_int(getattr(self, "candMaxItems", 100), 100, min_val=10, max_val=10000)
        self.messageDurationTime = _to_int(getattr(self, "messageDurationTime", 3), 3, min_val=1)

        # 選字鍵列索引 (issue #463/#539)
        self.selKeyType = _to_int(getattr(self, "selKeyType", 0), 0, min_val=0, max_val=len(selKeys) - 1)

        # 選字視窗字型 (issue #582)：空白或非法值退回內定字型
        font_name = getattr(self, "candFontName", DEF_FONT_NAME)
        if not isinstance(font_name, str) or not font_name.strip():
            self.candFontName = DEF_FONT_NAME
        else:
            self.candFontName = font_name.strip()

        # 選字視窗字型粗細 (issue #854)：只收 1-900，非法值退回 FW_NORMAL
        self.candFontWeight = _to_int(getattr(self, "candFontWeight", DEF_FONT_WEIGHT),
                                      DEF_FONT_WEIGHT, min_val=1, max_val=900)

        # 組字/選字視窗顏色 (issue #902)：0 表示跟隨系統調色盤；非法值退回 0
        def _to_color(val, default=0):
            if isinstance(val, bool):
                return default
            if isinstance(val, int):
                return val if 0 <= val <= 0xFFFFFF else default
            if isinstance(val, str):
                try:
                    i = int(val.strip(), 0)
                except ValueError:
                    return default
                return i if 0 <= i <= 0xFFFFFF else default
            return default

        self.candTextColor = _to_color(getattr(self, "candTextColor", 0), 0)
        self.windowBackgroundColor = _to_color(getattr(self, "windowBackgroundColor", 0), 0)
        self.selKeyColor = _to_color(getattr(self, "selKeyColor", 0), 0)

        # 多功能前導字元 (issue #525)：只取第一個字元，非法值退回 `
        # 設定頁的數字欄位會存成整數，這裡一併還原成數字字元
        lead_in_key = getattr(self, "leadInKey", DEF_LEAD_IN_KEY)
        if isinstance(lead_in_key, bool):
            lead_in_key = ""
        elif isinstance(lead_in_key, int):
            lead_in_key = str(lead_in_key)
        if not isinstance(lead_in_key, str) or not lead_in_key:
            self.leadInKey = DEF_LEAD_IN_KEY
        else:
            self.leadInKey = lead_in_key[0]

        # 按住 Ctrl 的符號鍵擷取 (issue #826)
        if not isinstance(getattr(self, "enableCtrlSymbols", True), bool):
            self.enableCtrlSymbols = True

    def toJson(self):
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_") and not key in self.ignoreSaveList}

    def save(self):
        filename = self.getConfigFile()
        try:
            with open(filename, "w") as f:
                json.dump(self.toJson(), f, sort_keys=True, indent=4)
            self.update()
        except Exception:
            pass # FIXME: handle I/O errors?

    def getDataDir(self):
        return os.path.join(os.path.dirname(__file__), "data")

    def getCinDir(self):
        return os.path.join(os.path.dirname(__file__), "cin")

    def getJsonDir(self):
        return os.path.join(os.path.dirname(__file__), "json")

    def getDefaultConfigDir(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, "input_methods", self.imeDirName, "config"))

    def findFile(self, dirs, name):
        for dirname in dirs:
            path = os.path.join(dirname, name)
            if os.path.exists(path):
                return path
        return None

    def copytree(slef, src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)

    # check if the config files are changed and relaod as needed
    def update(self):
        # avoid checking mtime of files too frequently
        if (time.time() - self._lastUpdateTime) < 3.0:
            return

        try:
            configTime = os.path.getmtime(self.getConfigFile())
        except Exception:
            configTime = 0.0

        datadirs = (self.getConfigDir(), self.getDataDir())
        symbolsTime = 0.0
        symbolsFile = self.findFile(datadirs, "symbols.dat")
        if symbolsFile:
            try:
                symbolsTime = os.path.getmtime(symbolsFile)
            except Exception:
                pass

        ezSymbolsTime = 0.0
        ezSymbolsFile = self.findFile(datadirs, "swkb.dat")
        if ezSymbolsFile:
            try:
                ezSymbolsTime = os.path.getmtime(ezSymbolsFile)
            except Exception:
                pass

        fsymbolsTime = 0.0
        fsymbolsFile = self.findFile(datadirs, "fsymbols.dat")
        if fsymbolsFile:
            try:
                fsymbolsTime = os.path.getmtime(fsymbolsFile)
            except Exception:
                pass

        flangsTime = 0.0
        flangsFile = self.findFile(datadirs, "flangs.dat")
        if flangsFile:
            try:
                flangsTime = os.path.getmtime(flangsFile)
            except Exception:
                pass

        userphraseTime = 0.0
        userphraseFile = self.findFile(datadirs, "userphrase.dat")
        if userphraseFile:
            try:
                userphraseTime = os.path.getmtime(userphraseFile)
            except Exception:
                pass

        extendtableFile = self.findFile(datadirs, "extendtable.dat")
        if extendtableFile:
            try:
                os.path.getmtime(extendtableFile)
            except Exception:
                pass

        lastConfigTime = self._version[0]
        self._version = (configTime, symbolsTime, ezSymbolsTime, fsymbolsTime, flangsTime, userphraseTime)

        # the main config file is changed, reload it
        if lastConfigTime != configTime:
            if not hasattr(self, "_in_update"): # avoid recursion
                self._in_update = True  # avoid recursion since update() will be called by load
                self.load()
                del self._in_update

        self._lastUpdateTime = time.time()

    def getVersion(self):
        return self._version

    def isConfigChanged(self, currentVersion):
        return currentVersion[0] != self._version[0]

    # isFullReloadNeeded() checks whether you need to delete the
    # existing chewing context and create a new one.
    # This is often caused by change of data files, such as
    # symbols.dat and swkb.dat files.
    def isFullReloadNeeded(self, currentVersion):
        return currentVersion[1:] != self._version[1:]


# globally shared config object
# load configurations from a user-specific config file
# 類別本身先另存一個名字，讓測試能建立獨立實例（類別會被單例遮蔽）
CinBaseConfigClass = CinBaseConfig
CinBaseConfig = CinBaseConfig()

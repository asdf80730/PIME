#! python3
# Copyright (C) 2015 - 2016 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
#
# Architecture and design by asdf80730.
# Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next):
# the hooks return their partial reply and the dispatcher merges them.
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

# keyboard modifiers used by TSF (from msctf.h of Windows SDK)
TF_MOD_ALT                       = 0x0001
TF_MOD_CONTROL                   = 0x0002
TF_MOD_SHIFT                     = 0x0004
TF_MOD_RALT                      = 0x0008
TF_MOD_RCONTROL                  = 0x0010
TF_MOD_RSHIFT                    = 0x0020
TF_MOD_LALT                      = 0x0040
TF_MOD_LCONTROL                  = 0x0080
TF_MOD_LSHIFT                    = 0x0100
TF_MOD_ON_KEYUP                  = 0x0200
TF_MOD_IGNORE_ALL_MODIFIER       = 0x0400

# command type parameter of TextService.onCommand
COMMAND_LEFT_CLICK  = 0
COMMAND_RIGHT_CLICK = 1
COMMAND_MENU        = 2

class KeyEvent:
    def __init__(self, msg):
        self.charCode = msg["charCode"]
        self.keyCode = msg["keyCode"]
        self.repeatCount = msg["repeatCount"]
        self.scanCode = msg["scanCode"]
        self.isExtended = msg["isExtended"]
        self.keyStates = msg["keyStates"]

    def isKeyDown(self, code):
        return (self.keyStates[code] & (1 << 7)) != 0

    def isKeyToggled(self, code):
        return (self.keyStates[code] & 1) != 0

    def isChar(self):
        return (self.charCode != 0)

    def isPrintableChar(self):
        return self.charCode > 0x1f and self.charCode != 0x7f

    def isSymbols(self):
        return self.charCode in [0x3d, 0x5b, 0x5c, 0x5d, 0x27]


class TextService:
    def __init__(self, client):
        self.client = client
        self.isActivated = False

        self.keyboardOpen = False
        self.showCandidates = False

        # per-request merge table: the setter methods below drop their field
        # into it and handleRequest() drains it after dispatching the hook.
        # Not part of the interface; observe the reply through the return
        # value of handleRequest() (or of a hook called directly).
        self.currentReply = {}
        self.compositionString = ""
        self.commitString = ""
        self.candidateList = []
        self.compositionCursor = 0
        self.candidateCursor = 0

    def updateStatus(self, msg):
        pass

    # This should be implemented in the derived class
    def checkConfigChange(self):
        pass

    @staticmethod
    def _mergePartial(reply, result):
        """Fold one hook result into the reply.

        A dict is a partial reply and merges in call order; any other value
        is the hook's own ``return`` value (or None for a no-op hook).
        """
        if isinstance(result, dict):
            reply.update(result)
            return None
        return result

    def handleRequest(self, msg):  # msg is a json object
        method = msg.get("method", None)
        seqNum = msg.get("seqNum", 0)
        success = True  # if the method is successfully handled
        ret = None  # the return value of the method, if any
        reply = {}  # the reply, merged from hook partials in call order

        if self.isActivated:
            # check if configurations are changed
            self._mergePartial(reply, self.checkConfigChange())

        self._mergePartial(reply, self.updateStatus(msg))
        if method == "filterKeyDown":
            keyEvent = KeyEvent(msg)
            ret = self._mergePartial(reply, self.filterKeyDown(keyEvent))
        elif method == "onKeyDown":
            keyEvent = KeyEvent(msg)
            ret = self._mergePartial(reply, self.onKeyDown(keyEvent))
        elif method == "filterKeyUp":
            keyEvent = KeyEvent(msg)
            ret = self._mergePartial(reply, self.filterKeyUp(keyEvent))
        elif method == "onKeyUp":
            keyEvent = KeyEvent(msg)
            ret = self._mergePartial(reply, self.onKeyUp(keyEvent))
        elif method == "onPreservedKey":
            guid = msg["guid"].lower()
            ret = self._mergePartial(reply, self.onPreservedKey(guid))
        elif method == "onCommand":
            commandId = msg["id"]
            commandType = msg["type"]
            self._mergePartial(reply, self.onCommand(commandId, commandType))
        elif method == "onMenu":
            buttonId = msg["id"]
            ret = self._mergePartial(reply, self.onMenu(buttonId))
        elif method == "onCompartmentChanged":
            guid = msg["guid"].lower()
            self._mergePartial(reply, self.onCompartmentChanged(guid))
        elif method == "onKeyboardStatusChanged":
            opened = msg["opened"]
            self._mergePartial(reply, self.onKeyboardStatusChanged(opened))
        elif method == "onCompositionTerminated":
            forced = msg["forced"]
            self._mergePartial(reply, self.onCompositionTerminated(forced))
        elif method == "onActivate":
            self.isActivated = True
            self.keyboardOpen = msg["isKeyboardOpen"]
            self._mergePartial(reply, self.onActivate())
        elif method == "onDeactivate":
            self._mergePartial(reply, self.onDeactivate())
            self.isActivated = False
        else:
            success = False

        # drain the setter merge table, then the fixed trailing fields
        reply.update(self.currentReply)
        self.currentReply = {}
        if ret is not None:
            reply["return"] = ret
        reply["success"] = success
        reply["seqNum"] = seqNum  # reply with sequence number added
        return reply

    # methods that should be implemented by derived classes
    def onActivate(self):
        pass

    def onDeactivate(self):
        pass

    def filterKeyDown(self, keyEvent):
        return False

    def onKeyDown(self, keyEvent):
        return False

    def filterKeyUp(self, keyEvent):
        return False

    def onKeyUp(self, keyEvent):
        return False

    def onPreservedKey(self, guid):
        # print("onPreservedKey", guid)
        return False

    def onCommand(self, commandId, commandType):
        pass

    def onMenu(self, buttonId):
        return None

    def onCompartmentChanged(self, guid):
        pass

    def onCompositionTerminated(self, forced):
        self.commitString = ""
        self.compositionString = ""

    def onKeyboardStatusChanged(self, opened):
        pass

    # public methods that should not be touched

    # language bar buttons
    """
    allowed arguments:
    @icon: full path to a *.ico file
    @commandId: an integer ID which will be passed to onCommand()
        when the button is clicked.
    @text: text on the button (optional)
    @tooltip: (optional)
    @type: "button", "menu", "toggle" (optional, button is the default)
    @enable: if the button is enabled (optional)
    @toggled: is the button toggled, only valid if type is "toggle" (optional)
    """
    def addButton(self, button_id, **kwargs):
        buttons = self.currentReply.setdefault("addButton", [])
        info = kwargs
        info["id"] = button_id
        buttons.append(info)
        return {"addButton": buttons}

    def removeButton(self, button_id):
        buttons = self.currentReply.setdefault("removeButton", [])
        buttons.append(button_id)
        return {"removeButton": buttons}

    """
    See addButton() for allowed arguments.
    """
    def changeButton(self, button_id, **kwargs):
        buttons = self.currentReply.setdefault("changeButton", [])
        info = kwargs
        info["id"] = button_id
        buttons.append(info)
        return {"changeButton": buttons}

    # preserved keys
    def addPreservedKey(self, keyCode, modifiers, guid):
        keys = self.currentReply.setdefault("addPreservedKey", [])
        keys.append({
            "keyCode" : keyCode,
            "modifiers": modifiers,
            "guid": guid.lower()})
        return {"addPreservedKey": keys}

    def removePreservedKey(self, guid):
        keys = self.currentReply.setdefault("removePreservedKey", [])
        keys.append(guid.lower())
        return {"removePreservedKey": keys}

    # composition string
    def setCompositionString(self, s):
        self.compositionString = s
        self.currentReply["compositionString"] = s
        return {"compositionString": s}

    def setCompositionCursor(self, pos):
        self.compositionCursor = pos
        self.currentReply["compositionCursor"] = pos
        return {"compositionCursor": pos}

    def setCommitString(self, s):
        self.commitString = s
        self.currentReply["commitString"] = s
        return {"commitString": s}

    def setCandidateList(self, cand):
        self.candidateList = cand
        self.currentReply["candidateList"] = cand
        return {"candidateList": cand}

    def setCandidateCursor(self, pos):
        self.candidateCursor = pos
        self.currentReply["candidateCursor"] = pos
        return {"candidateCursor": pos}

    def setShowCandidates(self, show):
        self.showCandidates = show
        self.currentReply["showCandidates"] = show
        return {"showCandidates": show}

    def setSelKeys(self, keys):
        self.currentReply["setSelKeys"] = keys
        return {"setSelKeys": keys}

    def setKeyboardOpen(self, opened):
        self.currentReply["openKeyboard"] = opened
        return {"openKeyboard": opened}

    '''
    Valid arguments:
    candFontName, cadFontSize, candPerRow, candUseCursor
    '''
    def customizeUI(self, **kwargs):
        data = self.currentReply.setdefault("customizeUI", {})
        data.update(kwargs)
        return {"customizeUI": data}

    def isComposing(self):
        return (self.compositionString != "" or self.showCandidates)

    '''
    Ask libIME to show a tooltip-like transient message to the user
    @message is the message to show.
    @duration is in seconds. After the specified duration, the message will be hidden.
    The currently shown message, if there is any, will be replaced by calling this method.
    '''
    def showMessage(self, message, duration=3):
        info = {
            "message": message,
            "duration": duration
        }
        self.currentReply["showMessage"] = info
        return {"showMessage": info}

    def hideMessage(self):
        self.currentReply["hideMessage"] = True
        return {"hideMessage": True}

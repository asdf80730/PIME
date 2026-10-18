#! python3
# Copyright (C) 2015 - 2016 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
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

import os
import threading
import json
import importlib
import logging

logger = logging.getLogger(__name__)

class TextServiceInfo:
    def __init__(self):
        self.dirName = ""
        self.name = ""
        self.moduleName = ""
        self.serviceName = ""
        self.guid = ""
        self.textServiceClass = None
        self.modulePrefix = ""
        self.modulPrefix = ""
        self.configTool = ""

    def loadFromJson(self, jsonFile):
        dirName = os.path.dirname(jsonFile)
        self.dirName = os.path.basename(dirName)
        self.modulePrefix = "input_methods.%s" % self.dirName
        self.modulPrefix = self.modulePrefix
        # Read the moduleName(xxx.py) & serviceName(class name) from JSON
        jsonData = None
        try:
            with open(jsonFile, encoding="UTF-8") as dataFile:
                jsonData = json.load(dataFile)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load JSON from %s: %s", jsonFile, e)
            return

        if isinstance(jsonData, dict):
            self.name = jsonData.get("name", "")
            # text service module
            moduleName = jsonData.get("moduleName", "")
            serviceName = jsonData.get("serviceName", "")
            # Validate that moduleName and serviceName are valid Python identifiers
            # and stay strictly within the input_methods package hierarchy
            if isinstance(moduleName, str) and moduleName.isidentifier():
                self.moduleName = "%s.%s" % (self.modulePrefix, moduleName)
            if isinstance(serviceName, str) and serviceName.isidentifier():
                self.serviceName = serviceName
            self.guid = str(jsonData.get("guid", "")).lower()
            self.configTool = jsonData.get("configTool", "")

    def createInstance(self, client):
        if not self.moduleName or not self.serviceName or not self.guid:
            return None
        if not self.textServiceClass: # constructor is not yet imported
            try:
                mod = importlib.import_module(self.moduleName)
                self.textServiceClass = getattr(mod, self.serviceName, None)
            except Exception as e:
                logger.error("Failed to import module %s: %s", self.moduleName, e)
                return None
            if not self.textServiceClass:
                return None
        return self.textServiceClass(client) # create a new instance for this text service


class TextServiceManager:
    def __init__(self):
        self.__lock = threading.Lock()
        self.services = {}
        self.enumerateServices()

    def enumerateServices(self):
        # To enumerate currently installed Input Method
        currentDir = os.path.dirname(os.path.abspath(__file__))
        input_methods_dir = os.path.join(currentDir, "input_methods")
        if not os.path.isdir(input_methods_dir):
            return
        for subdir in os.listdir(input_methods_dir):
            subpath = os.path.join(input_methods_dir, subdir)
            if not os.path.isdir(subpath):
                continue
            filename = os.path.join(subpath, "ime.json")
            if os.path.exists(filename):
                info = TextServiceInfo()
                info.loadFromJson(filename)
                if info.guid and info.moduleName and info.serviceName:
                    self.services[info.guid] = info

    def createService(self, client, guid):
        guid = guid.lower()
        if guid in self.services:
            info = self.services[guid]
            return info.createInstance(client)
        return None


textServiceMgr = TextServiceManager()

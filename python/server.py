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

"""PIME python backend: the stdin/stdout IPC server that hosts the text services.

Log policy (#445). Every message written by this process goes through one
size-bounded rotating handler, so the log folder holds at most
``LOG_BACKUP_COUNT + 1`` = 4 files and ``LOG_MAX_BYTES`` = 1000000 bytes each,
4000000 bytes in total; the numbered backups ``python_backend.log.1`` ..
``python_backend.log.3`` are rewritten from the oldest on every rollover. The
rime user directory has its own bounded retention pass, documented in
``input_methods/rime/librime.py``.
"""

import json
import logging
import logging.handlers
import sys
import traceback
import os

if __name__ == "__main__":
    sys.path.append('python3')

sys.path.append(os.path.dirname(__file__))    


from serviceManager import TextServiceManager


# Size bound for the backend's own log, see the module docstring.
LOG_MAX_BYTES = 1000000
LOG_BACKUP_COUNT = 3


def append_error_log(message):
    try:
        log_dir = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), "PIME", "Logs")
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "python_backend.log"),
            mode="a",
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        # Match the old writer exactly: one newline per message, no more.
        handler.terminator = ""
        line = message if message.endswith("\n") else message + "\n"
        try:
            handler.handle(logging.LogRecord(
                "PIME", logging.WARNING, __file__, 0, line, None, None))
        finally:
            handler.close()
    except Exception:
        pass


class Client(object):
    def __init__(self, server):
        self.server = server
        self.service = None

    def init(self, msg):
        self.guid = msg["id"]
        self.isWindows8Above = msg["isWindows8Above"]
        self.isMetroApp = msg["isMetroApp"]
        self.isUiLess = msg["isUiLess"]
        self.isConsole = msg["isConsole"]
        # create the text service
        self.service = self.server.createService(self, self.guid)
        return (self.service is not None)

    def handleRequest(self, msg): # msg is a json object
        method = msg.get("method")
        seqNum = msg.get("seqNum", 0)
        # print("handle message: ", str(id(self)), method, seqNum)
        service = self.service
        if service:
            # let the text service handle the message
            reply = service.handleRequest(msg)
        else:  # the text service is not yet initialized
            reply = {"seqNum": seqNum}
            success = False
            if method == "init": # initialize the text service
                success = self.init(msg)
            reply["success"] = success
        # print(reply)
        return reply


class Server(object):
    """IPC backend server managing client sessions and text service dispatching."""

    def __init__(self, base_dir: str):
        """Initializes the server and loads text services from base_dir/input_methods.

        Args:
            base_dir: The base package directory on sys.path containing the
                'input_methods' package. Cannot be None.
        """
        self.clients = {}
        self.serviceMgr = TextServiceManager()
        try:
            self.serviceMgr.load(base_dir)
        except Exception as e:
            append_error_log(f"ERROR: Failed to load text services from {base_dir}: {e}\n{traceback.format_exc()}")

    def createService(self, client, guid):
        """Creates a text service instance for the client associated with guid."""
        return self.serviceMgr.createService(client, guid)

    def run(self):
        """Runs the main request/reply loop reading from stdin and writing to stdout."""
        while True:
            line = ""
            client_id = ""
            msg = None
            client = None
            try:
                line = input().strip()
                if not line:
                    continue
                # parse PIME requests (one request per line):
                # request format: "<client_id>|<JSON string>\n"
                # response format: "PIME_MSG|<client_id>|<JSON string>\n"
                parts = line.split('|', maxsplit=1)
                if len(parts) != 2:
                    print("ERROR: malformed request:", line, file=sys.stderr)
                    append_error_log("ERROR: malformed request: {0}\n".format(line))
                    continue
                client_id, msg_text = parts
                msg = json.loads(msg_text)
                client = self.clients.get(client_id)
                if not client:
                    # create a Client instance for the client
                    client = Client(self)
                    self.clients[client_id] = client
                    print("new client:", client_id, file=sys.stderr)
                if msg.get("method") == "close":  # special handling for closing a client
                    self.remove_client(client_id)
                    reply_dict = {"success": True}
                    if "seqNum" in msg:
                        reply_dict["seqNum"] = msg["seqNum"]
                    reply_line = '|'.join(["PIME_MSG", client_id, json.dumps(reply_dict)])
                    print(reply_line, flush=True)
                else:
                    ret = client.handleRequest(msg)
                    # Send the response to the client via stdout
                    # one response per line in the format "PIME_MSG|<client_id>|<json reply>"
                    reply_line = '|'.join(["PIME_MSG", client_id, json.dumps(ret, ensure_ascii=False)])
                    print(reply_line, flush=True)
            except EOFError:
                # stop the server
                break
            except Exception as e:
                print("ERROR:", e, line, file=sys.stderr)
                # print the exception traceback for ease of debugging
                traceback.print_exc()
                append_error_log("ERROR: {0}\nREQUEST: {1}\n{2}\n".format(e, line, traceback.format_exc()))
                
                if client and client.service:
                    client.service.currentReply = {}
                
                # generate an output containing {success: False} to prevent the client from being blocked
                reply_dict = {"success": False}
                if isinstance(msg, dict) and "seqNum" in msg:
                    reply_dict["seqNum"] = msg["seqNum"]
                reply_line = '|'.join(["PIME_MSG", client_id, json.dumps(reply_dict)])
                print(reply_line, flush=True)
                # Keep the backend alive after one bad request; tearing down an
                # active TSF session can destabilize the foreground application.
                continue

    def remove_client(self, client_id):
        """Cleans up and removes an active client session by its ID."""
        print("client disconnected:", client_id, file=sys.stderr)
        try:
            del self.clients[client_id]
        except KeyError:
            pass


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server = Server(current_dir)
    server.run()


if __name__ == "__main__":
    main()

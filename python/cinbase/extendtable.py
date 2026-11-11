from __future__ import print_function
from __future__ import unicode_literals

import re

class extendtable(object):

    # TODO check the possiblility if the encoding is not utf-8
    encoding = 'utf-8'

    def __init__(self, fs):

        self.chardefs = {}

        for line in fs:

            line = line.strip()

            key, root = safeSplit(line)
            key = key.lower().strip()
            root = expandCodePosition(root.strip())

            try:
                self.chardefs[key].append(root)
            except KeyError:
                self.chardefs[key] = [root]

    def __del__(self):
        del self.chardefs
        self.chardefs = {}

    def isInCharDef(self, key):
        return key in self.chardefs

    def getCharDef(self, key):
        """ 
        will return a list conaining all possible result
        """
        return self.chardefs[key]


# EUDCEDIT hands the user a bare slot number (FA40 or 0x4e2d) for a self-made
# glyph, and the candidate window paints the code point from the configured
# font, so a hex code position is accepted as its character.
HEX_CODE_POSITION = re.compile(r"^([0-9A-Fa-f]{4}|0[xX][0-9A-Fa-f]{1,5})$")


def expandCodePosition(value):
    """Expand a bare hexadecimal code position to its character; keep anything else."""
    if HEX_CODE_POSITION.match(value):
        return chr(int(value, 16))
    return value


def safeSplit(line):
    if ' ' in line:
        return line.split(' ', 1)
    elif '\t' in line:
        return line.split('\t', 1)
    else:
        return line, "Error"

__all__ = ["extendtable"]

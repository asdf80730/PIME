"""PIME Key Bridge: type Chinese in windows that TSF never reaches.

The Windows 11 taskbar search flyout is a XAML island: it hosts no text
service, so the TSF client DLL never sees a key event and the PIME backend
never composes anything.  This package bridges the gap: it watches the
keyboard with a low-level hook, forwards the keys to the PIME backend over the
launcher pipe, and draws the composition and the candidate list in a small
overlay window of its own.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

__all__ = ["overlay", "protocol", "win32"]

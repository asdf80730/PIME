# Windows 10 is the support floor

PIME's installable artifact requires Windows 10 or newer, enforced by the
installer's `.onInit` gate. The floor is set by the runtime payload, not by the
C++ text service: the bundled Python, Node, Go and Rust runtimes all list
Windows 10 as their minimum supported release. Decided 2026-10-26, after
v2.0.0-beta4 shipped as an emergency CVE release.

## Considered Options

- **Windows 8.1 as the master floor** (rejected). It forces every runtime down
  to its last Windows-8.1-capable release: Python 3.12, Go 1.20, Rust 1.77.
  Python 3.12's last Windows binary is 3.12.10 (2025-04-08) and its OpenSSL is
  pinned to the 3.0 series, which reached end of life on 2026-09-07. That
  reverses the CVE fixes beta4 was released for, and turns the Rust launcher
  into a permanent fork of upstream.
- **Windows 8.1 as a separate legacy artifact** (rejected). Keeps master on
  Windows 10 but still needs the frozen toolchains above, a second artifact and
  release note declaring no security support, and re-verification of every
  upstream launcher change against Rust 1.77.
- **Windows 10** (chosen). Matches the Python 3.15.1, Node 22.23.4, Go 1.21 and
  stable-Rust payload master already ships, and keeps receiving interpreter and
  OpenSSL security updates.

There is deliberately no Windows 8.1 build. Windows 8.1 itself left support on
2023-01-10, and the only artifact that could run there would ship an
interpreter frozen in April 2025.

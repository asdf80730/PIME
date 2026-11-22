# Probe the PIME key bridge against the Windows 11 search flyout using real
# hardware scan codes (SendInput + KEYEVENTF_SCANCODE) and assert on the
# bridge's own --debug trace rather than reading the control's ValuePattern.
#
# Architecture and design by asdf80730.  Implementation generated with AI
# assistance from Sider.
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Usage (from the repository root):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tests\keybridge_flyout_probe.ps1

param(
  [string]$PythonExe = "python\python3\python.exe",
  [string]$LogPath = (Join-Path $env:TEMP ("pime-keybridge-probe-" + [guid]::NewGuid().ToString("N") + ".log"))
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class ScanInput {
  const uint INPUT_KEYBOARD = 1;
  const uint KEYEVENTF_KEYUP = 0x0002;
  const uint KEYEVENTF_SCANCODE = 0x0008;
  const uint MAPVK_VK_TO_VSC = 0;

  [StructLayout(LayoutKind.Sequential)]
  struct INPUT {
    public uint type;
    public INPUTUNION u;
  }

  [StructLayout(LayoutKind.Explicit)]
  struct INPUTUNION {
    [FieldOffset(0)] public MOUSEINPUT mi;
    [FieldOffset(0)] public KEYBDINPUT ki;
    [FieldOffset(0)] public HARDWAREINPUT hi;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct MOUSEINPUT {
    public int dx, dy;
    public uint mouseData, dwFlags, time;
    public UIntPtr dwExtraInfo;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct KEYBDINPUT {
    public ushort wVk;
    public ushort wScan;
    public uint dwFlags;
    public uint time;
    public UIntPtr dwExtraInfo;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct HARDWAREINPUT {
    public uint uMsg;
    public ushort wParamL, wParamH;
  }

  [DllImport("user32.dll", SetLastError = true)]
  static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

  [DllImport("user32.dll")]
  static extern uint MapVirtualKeyW(uint uCode, uint uMapType);

  static void SendScan(ushort scan, bool keyUp) {
    INPUT[] inp = new INPUT[1];
    inp[0].type = INPUT_KEYBOARD;
    inp[0].u.ki = new KEYBDINPUT {
      wVk = 0,
      wScan = scan,
      dwFlags = KEYEVENTF_SCANCODE | (keyUp ? KEYEVENTF_KEYUP : 0u),
      time = 0,
      dwExtraInfo = UIntPtr.Zero
    };
    SendInput(1, inp, Marshal.SizeOf(typeof(INPUT)));
  }

  public static ushort ScanForVk(uint vk) {
    return (ushort)MapVirtualKeyW(vk, MAPVK_VK_TO_VSC);
  }

  public static void TapVk(uint vk) {
    ushort scan = ScanForVk(vk);
    SendScan(scan, false);
    System.Threading.Thread.Sleep(60);
    SendScan(scan, true);
    System.Threading.Thread.Sleep(140);
  }

  public static void CtrlSpace() {
    ushort ctrl = ScanForVk(0x11);   // VK_CONTROL -> 0x1D
    ushort space = ScanForVk(0x20);  // VK_SPACE   -> 0x39
    SendScan(ctrl, false);
    System.Threading.Thread.Sleep(60);
    SendScan(space, false);
    System.Threading.Thread.Sleep(60);
    SendScan(space, true);
    System.Threading.Thread.Sleep(60);
    SendScan(ctrl, true);
    System.Threading.Thread.Sleep(250);
  }
}
'@

# Start keybridge --debug in the background and capture its stdout/stderr.
$errPath = "$LogPath.err"
$env:PYTHONPATH = "python"
$bridge = Start-Process -FilePath $PythonExe `
  -ArgumentList @("-u", "-m", "keybridge", "--debug") `
  -RedirectStandardOutput $LogPath `
  -RedirectStandardError $errPath `
  -PassThru -NoNewWindow

try {
  # Wait for the bridge banner.
  $ready = $false
  for ($i = 0; $i -lt 50; $i++) {
    Start-Sleep -Milliseconds 100
    if ((Test-Path $LogPath) -and ((Get-Content $LogPath -Raw) -match 'PIME key bridge: profile')) {
      $ready = $true
      break
    }
  }
  if (-not $ready) {
    throw "keybridge did not become ready within 5s (log: $LogPath)"
  }

  # Focus the taskbar search flyout's RichEditBox.
  $AE = [System.Windows.Automation.AutomationElement]
  $TC = [System.Windows.Automation.TreeScope]
  function Cond($prop, $val) { return New-Object System.Windows.Automation.PropertyCondition($prop, $val) }
  function And2($a, $b) { return New-Object System.Windows.Automation.AndCondition($a, $b) }
  $root = $AE::RootElement
  $foc = $AE::FocusedElement
  if ($null -eq $foc -or $foc.Current.ClassName -ne 'RichEditBox') {
    $pill = $root.FindFirst($TC::Subtree, (And2 (Cond $AE::NameProperty ([string][char]0x641C + [char]0x5C0B)) (Cond $AE::ClassNameProperty 'ToggleButton')))
    if ($null -eq $pill) { throw "taskbar search pill not found" }
    $tp = $null
    if (-not $pill.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern, [ref]$tp)) {
      throw "taskbar search pill has no TogglePattern"
    }
    $tp.Toggle()
    Start-Sleep -Milliseconds 1500
    $foc = $AE::FocusedElement
  }
  if ($null -eq $foc -or $foc.Current.ClassName -ne 'RichEditBox') {
    throw "search flyout RichEditBox does not have focus"
  }

  # 1. Chinese mode: type 'j', 'i', '5', Space, Enter using real scan codes.
  foreach ($vk in @(0x4A, 0x49, 0x35, 0x20, 0x0D)) {
    [ScanInput]::TapVk($vk)
  }
  Start-Sleep -Milliseconds 500

  # 2. Switch to English mode via Ctrl+Space, then type 'a', 'b', 'c'.
  [ScanInput]::CtrlSpace()
  foreach ($vk in @(0x41, 0x42, 0x43)) {
    [ScanInput]::TapVk($vk)
  }
  Start-Sleep -Milliseconds 500

  # 3. Switch back to Chinese mode via Ctrl+Space, then type 'j', 'i'.
  [ScanInput]::CtrlSpace()
  foreach ($vk in @(0x4A, 0x49)) {
    [ScanInput]::TapVk($vk)
  }
  Start-Sleep -Milliseconds 500
}
finally {
  if ($bridge -and -not $bridge.HasExited) {
    Stop-Process -Id $bridge.Id -Force -ErrorAction SilentlyContinue
  }
}

$trace = if (Test-Path $LogPath) { Get-Content $LogPath -Raw } else { "" }
$lines = $trace -split "`r?`n"

$fgLines      = @($lines | Where-Object { $_ -match 'foreground:' })
$hookLines    = @($lines | Where-Object { $_ -match 'hook: KeyEvent\(' })
$backendLines = @($lines | Where-Object { $_ -match 'backend: KeyEvent\(' })
$compLines    = @($lines | Where-Object { $_ -match "reply: .*'compositionString':" })
$commitLines  = @($lines | Where-Object { $_ -match "reply: .*'commitString':" })
$modeLines    = @($lines | Where-Object { $_ -match 'PIME key bridge: (english|chinese) mode' })

Write-Output "=== keybridge trace summary ($LogPath) ==="
Write-Output ("foreground changes : " + $fgLines.Count)
$fgLines | ForEach-Object { Write-Output ("  " + $_) }
Write-Output ("hook events        : " + $hookLines.Count)
Write-Output ("backend events     : " + $backendLines.Count)
Write-Output ("composition replies: " + $compLines.Count)
Write-Output ("commit replies     : " + $commitLines.Count)
Write-Output ("mode switches      : " + $modeLines.Count)
$modeLines | ForEach-Object { Write-Output ("  " + $_) }

$failures = @()
if ($hookLines.Count -eq 0)    { $failures += "hook saw no keys for the search box" }
if ($backendLines.Count -eq 0) { $failures += "backend received no keys" }
if ($compLines.Count -eq 0)    { $failures += "backend returned no compositionString reply" }
if ($modeLines.Count -lt 2)    { $failures += "expected >= 2 mode switches (english + chinese), saw $($modeLines.Count)" }

if ($failures.Count -gt 0) {
  Write-Error ("FAIL: " + ($failures -join "; "))
  exit 1
}

Write-Output "PASS: hook, backend, composition, and mode-switch assertions succeeded."
exit 0

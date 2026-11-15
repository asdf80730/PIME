# Issue #859 人工桌面重測紀錄表

軟體：PIME 2.0.0-beta4（本機 NSIS 安裝檔，未簽章）
整合樹 SHA：fee25b1（含 2d160fe 的兩層修復）
本機 Windows build：10.0.26300.9974

## 前置

1. 執行 `.tools/stage/installer/PIME-2.0.0-beta4-setup.exe`，元件頁勾選
   Python → 注音（chewing）。只勾筆畫時 注音 不會註冊。
2. 確認 `PIMELauncher.exe` 在跑：`cmd.exe /c "tasklist" | grep PIMELauncher`
3. 開一個 Word 文件、一個 記事本（第二個視窗用來分辨視窗層級狀態）。

## 測試 A：Win+Shift+S 七步（原報告步驟）

重複 3 次，每次記錄：

| 次 | 步驟 1-4 後注音是否顯示 | 恢復方式（關視窗 / 重啟 Launcher） | 同時間記事本能否打中文 |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

步驟：Word 打注音 → Win+Shift+S 截圖 → Ctrl+V 貼上 → 再打注音。

附加觀察 A5：先在截圖工具列按「關閉」再打字，結果是否不同。

## 測試 B：尺規變體（@q120144178）

| 次 | 拉動縮排尺規後注音是否顯示 | 恢復方式 |
|---|---|---|
| 1 | | |
| 2 | | |

## 版本

- Office：2019 Standard / 365（於 Word「檔案 → 關於」讀取）
- Windows build：10.0.26300.9974（本機 `cmd.exe /c ver`，2026-11-16）
- 已安裝 PIME：`C:\Program Files (x86)\PIME\version.txt` = `2.0.0-beta4`
- Outlook 是否也出現同一症狀：____________

## 判讀

- 測試 B 的每一「次」都要記 PASS 或 FAIL；FAIL 時標明是哪一層恢復：
  只重開該視窗，或需要重啟 `PIMELauncher.exe`。
- 兩層修復的來源（判讀用，不必重跑）：中斷管線重連
  `PIMETextService/PIMEClient.cpp:766-781`；watchdog 清除 pending 佇列
  `PIMELauncher/src/backend_manager.rs:117-135`、`:251`。

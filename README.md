# 乃木坂46 MSG 備份工具 GUI (Unofficial)

這是一個為 `colmsg` 命令列工具設計的圖形化介面 (GUI)。
讓使用者可以透過簡單的視窗介面來備份 MSG，並生成類似 LINE/APP 介面的 HTML 離線瀏覽器。

## 功能特色
- 🖼️ **圖形化操作**：不用再打指令，直接貼上 Token 即可使用。
- 📂 **單一入口網頁**：生成一個 `index.html` 整合所有成員對話。
- 🔍 **強大瀏覽器**：
  - 支援依年份/月份跳轉。
  - 支援圖片 (Lightbox)、影片、語音播放。
  - 側邊欄可拖曳排序成員順序。
  - 圖片預設 25% 大小，影片 50% 大小，閱讀更舒適。
- 👤 **客製化**：支援替換 `%%%` 暱稱，以及設定成員大頭貼。

## 使用方法
1. 下載本專案的 `gui.py`。
2. **自行下載核心工具**：前往 [colmsg 原作者 GitHub]https://github.com/proshunsuke/colmsg) 下載 `colmsg.exe`。
3. 將 `gui.py` 與 `colmsg.exe` 放在同一個資料夾。
4. 安裝 Python (若未安裝) 並執行：
   ```bash
   python gui.py
# 乃木坂46 MSG 備份工具 GUI (Unofficial)

這是一個為 `colmsg` 命令列工具設計的圖形化介面 (GUI)。
讓使用者可以透過簡單的視窗介面來備份 MSG，並生成類似 LINE/APP 介面的 HTML 離線瀏覽器。

## 介面預覽
![操作介面截圖](https://你的圖片連結.png)
*(這裡展示操作畫面，讓大家知道只要貼上 Token 就能用)*

## 功能特色
- 🖼️ **圖形化操作**：不用再打指令 (CMD)，直接在視窗貼上 Token 即可使用。
- 📂 **單一入口網頁**：自動生成 `index.html`，整合所有成員的對話紀錄。
- 🔍 **強大瀏覽器**：
  - 支援依年份/月份快速跳轉。
  - 支援 **圖片 (Lightbox)**、**影片**、**語音** 直接播放。
  - 側邊欄可拖曳排序成員順序。
  - 優化閱讀體驗：圖片預設 25% 大小，影片 50% 大小。
- 👤 **高度客製化**：支援替換 `%%%` 暱稱，以及自訂成員大頭貼。

## 使用方法
1. 下載本專案的 `gui.py` (或是 Releases 中的 exe 檔)。
2. **下載核心工具**：前往 [colmsg 原作者 GitHub](https://github.com/proshunsuke/colmsg) 下載 `colmsg.exe`。
3. 將 `gui.py` 與 `colmsg.exe` 放在同一個資料夾。
4. 安裝 Python (若未安裝) 並執行：
   ```bash
   python gui.py
## 關於本專案 & 討論
# 🤖 AI 生成聲明
本專案的程式碼架構與邏輯完全由 AI 協助生成。
程式碼可能不夠精簡或完美，非常歡迎大家自由修改、優化程式碼、或是 Fork 出去二次開發，希望能讓這個工具更好用！
💬 交流與回饋
如果你有任何使用上的問題、想要許願新功能，或是想聊聊關於備份的心得：

回報 Bug：請使用 [Issues]( https://github.com/ann-nogk/Nogi-MSG-GUI/issues) 頁面。

閒聊與討論：歡迎至 [Discussions]( https://github.com/ann-nogk/Nogi-MSG-GUI/discussions) 區留言。

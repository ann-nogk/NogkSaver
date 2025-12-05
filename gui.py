import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import re
import json
import shutil

# --- Avatar 選擇視窗 (保持不變) ---
class AvatarSelectionWindow(tk.Toplevel):
    def __init__(self, parent, member_list, target_dir):
        super().__init__(parent)
        self.title("設定成員頭像")
        self.geometry("500x400")
        self.member_list = member_list
        self.target_dir = target_dir
        self.avatar_map = {} 

        ttk.Label(self, text="請為成員選擇頭像圖片 (留空則使用預設文字頭像)", padding=10).pack(fill='x')

        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.path_vars = {}
        for member in member_list:
            row = ttk.Frame(self.scrollable_frame, padding=5)
            row.pack(fill='x', pady=2)
            
            ttk.Label(row, text=member, width=15, anchor='w').pack(side='left')
            
            path_var = tk.StringVar()
            self.path_vars[member] = path_var
            
            entry = ttk.Entry(row, textvariable=path_var)
            entry.pack(side='left', fill='x', expand=True, padx=5)
            
            btn = ttk.Button(row, text="選擇...", width=8, command=lambda m=member: self.browse_image(m))
            btn.pack(side='right')

        ttk.Button(self, text="確認並產生網頁", command=self.on_confirm).pack(pady=10)

    def browse_image(self, member):
        file_path = filedialog.askopenfilename(
            title=f"選擇 {member} 的頭像",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.gif")]
        )
        if file_path:
            self.path_vars[member].set(file_path)

    def on_confirm(self):
        for member, var in self.path_vars.items():
            src_path = var.get().strip()
            if src_path and os.path.exists(src_path):
                ext = os.path.splitext(src_path)[1]
                new_filename = f"avatar_{member}{ext}"
                dest_path = os.path.join(self.target_dir, new_filename)
                try:
                    shutil.copy2(src_path, dest_path)
                    self.avatar_map[member] = new_filename
                except Exception as e:
                    print(f"複製頭像失敗 {member}: {e}")
        self.destroy()

# --- HTML 生成器邏輯 (v14.0: Lightbox優化 + 拖曳排序) ---
class ChatGenerator:
    def generate_single_index(self, group_folder_path, nickname="", avatar_map=None):
        if avatar_map is None:
            avatar_map = {}

        if not os.path.exists(group_folder_path):
            return False, "找不到資料夾"

        # 1. 掃描資料
        all_data = {}
        members = []
        for entry in os.listdir(group_folder_path):
            full_path = os.path.join(group_folder_path, entry)
            if os.path.isdir(full_path) and len(os.listdir(full_path)) > 0:
                members.append(entry)
        members.sort()

        if not members:
            return False, "找不到成員資料夾"

        valid_exts = {'.txt', '.jpg', '.jpeg', '.png', '.mp4', '.m4a', '.mp3', '.wav'}
        time_pattern = re.compile(r'(\d{14})')

        for member in members:
            member_path = os.path.join(group_folder_path, member)
            member_msgs = []
            
            for f in os.listdir(member_path):
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    match = time_pattern.search(f)
                    timestamp_str = match.group(1) if match else "00000000000000"
                    
                    msg_obj = {
                        'f': f, 
                        't': ext, 
                        'ts': timestamp_str, 
                        'd': self._format_date(timestamp_str), 
                        'hm': self._format_time(timestamp_str), 
                        'c': '' 
                    }
                    if ext == '.txt':
                        try:
                            with open(os.path.join(member_path, f), 'r', encoding='utf-8') as tf:
                                raw_text = tf.read()
                                if nickname:
                                    raw_text = raw_text.replace('%%%', nickname)
                                msg_obj['c'] = raw_text
                        except: msg_obj['c'] = "(Error)"
                    
                    member_msgs.append(msg_obj)
            
            member_msgs.sort(key=lambda x: x['ts'])
            all_data[member] = member_msgs

        json_data = json.dumps(all_data, ensure_ascii=False)
        json_avatars = json.dumps(avatar_map, ensure_ascii=False)

        # 2. 生成 HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nogi MSG Viewer</title>
            <style>
                body {{ background-color: #f2f3f7; font-family: "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; }}
                
                /* --- 側邊欄 --- */
                .sidebar {{ width: 220px; background-color: #fff; border-right: 1px solid #ddd; display: flex; flex-direction: column; flex-shrink: 0; }}
                .sidebar-header {{ padding: 15px; background-color: #6a0d6e; color: white; font-weight: bold; text-align: center; }}
                
                /* 排序控制區 */
                .sidebar-sort-info {{ 
                    background-color: #f8f0fc; padding: 5px 10px; font-size: 12px; color: #666; 
                    display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee;
                }}
                .reset-btn {{ 
                    font-size: 10px; background: #ddd; border: none; padding: 2px 6px; 
                    cursor: pointer; border-radius: 4px; color: #333; display: none;
                }}
                .reset-btn:hover {{ background: #ccc; }}

                .member-list {{ overflow-y: auto; flex-grow: 1; }}
                
                /* 成員項目 (支援拖曳樣式) */
                .member-item {{ 
                    padding: 12px 20px; cursor: grab; border-bottom: 1px solid #f0f0f0; 
                    display: flex; align-items: center; gap: 10px; transition: background 0.1s; user-select: none;
                }}
                .member-item:hover {{ background-color: #f9f9f9; }}
                .member-item.active {{ background-color: #f3e5f5; color: #7e1083; font-weight: bold; border-left: 4px solid #7e1083; }}
                .member-item.dragging {{ opacity: 0.5; background-color: #eee; }}
                
                .member-avatar-icon {{ width: 32px; height: 32px; background: #ddd; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 12px; color: #fff; overflow: hidden; flex-shrink: 0; pointer-events: none; }}
                .member-avatar-icon img {{ width: 100%; height: 100%; object-fit: cover; }}

                /* --- 主區域 --- */
                .main-area {{ flex-grow: 1; display: flex; flex-direction: column; height: 100%; position: relative; }}
                
                /* Header */
                .header {{ 
                    background-color: #7e1083; color: white; height: 50px;
                    display: flex; align-items: center; justify-content: center; 
                    padding: 0 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                    flex-shrink: 0; position: relative;
                }}
                
                .header-center-group {{ display: flex; align-items: center; gap: 10px; }}
                .header-title {{ font-size: 18px; font-weight: bold; margin-right: 5px; }}
                
                select {{ 
                    padding: 3px 8px; border-radius: 12px; border: none; outline: none; 
                    background: rgba(255,255,255,0.9); color: #7e1083; font-weight: bold; cursor: pointer;
                    font-size: 13px;
                }}
                #scaleSelect {{ background: rgba(255,255,255,0.7); color: #333; }}

                .chat-container {{ 
                    flex-grow: 1; padding: 20px; overflow-y: auto; 
                    display: flex; flex-direction: column; gap: 10px; 
                }}
                
                .empty-state {{ text-align: center; color: #999; margin-top: 100px; }}

                /* 訊息樣式 */
                .timestamp-separator {{ text-align: center; color: #888; font-size: 12px; margin: 15px 0; background-color: rgba(0,0,0,0.05); padding: 4px 10px; border-radius: 12px; align-self: center; }}
                .msg-row {{ display: flex; align-items: flex-end; gap: 8px; margin-bottom: 5px; }}
                
                .avatar {{ width: 40px; height: 40px; background-color: #ccc; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; flex-shrink: 0; overflow: hidden; }}
                .avatar img {{ width: 100%; height: 100%; object-fit: cover; }}

                .bubble-wrapper {{ display: flex; flex-direction: column; max-width: 80%; }}
                
                .bubble {{ background-color: white; padding: 10px 14px; border-radius: 18px; border-bottom-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-wrap: break-word; line-height: 1.5; color: #333; font-size: 15px; white-space: pre-wrap; }}
                
                .media-bubble {{ background: transparent; box-shadow: none; padding: 0; border-radius: 12px; overflow: hidden; display: inline-block; }}
                
                :root {{ --img-scale: 25%; --video-scale: 50%; }}
                
                .chat-img {{ width: var(--img-scale); border-radius: 12px; display: block; cursor: zoom-in; border: 1px solid #eee; transition: width 0.3s; }}
                .chat-video {{ width: var(--video-scale); border-radius: 12px; max-height: 400px; }}
                .chat-audio {{ width: 240px; }}
                
                .time-label {{ font-size: 11px; color: #999; margin-left: 4px; margin-bottom: 2px; min-width: 35px; }}

                /* --- Lightbox (燈箱) --- */
                #lightbox {{
                    display: none; position: fixed; z-index: 1000; left: 0; top: 0;
                    width: 100%; height: 100%; overflow: auto;
                    background-color: rgba(0,0,0,0.85);
                    align-items: center; justify-content: center;
                }}
                #lightbox-img {{
                    max-width: 90%; max-height: 90%;
                    border-radius: 5px; box-shadow: 0 0 20px rgba(0,0,0,0.5);
                    object-fit: contain;
                    cursor: default; /* 圖片上游標不顯示點擊手勢，避免誤會 */
                }}

                @media (max-width: 768px) {{
                    .sidebar {{ display: none; }}
                    .header-center-group {{ flex-wrap: wrap; justify-content: center; }}
                }}
            </style>
        </head>
        <body>
            <!-- Lightbox 容器 (點擊背景關閉) -->
            <div id="lightbox" onclick="closeLightbox(event)">
                <img id="lightbox-img" src="" alt="Full size" onclick="event.stopPropagation()">
            </div>

            <div class="sidebar">
                <div class="sidebar-header">乃木坂46 MSG</div>
                <!-- 排序資訊列 -->
                <div class="sidebar-sort-info">
                    <span id="sortStatus">排序：50音 (預設)</span>
                    <button id="resetSortBtn" class="reset-btn" onclick="resetSort()">重置</button>
                </div>
                <div class="member-list" id="memberList"></div>
            </div>
            
            <div class="main-area">
                <div class="header">
                    <div class="header-center-group">
                        <div class="header-title" id="headerTitle">請選擇成員</div>
                        <select id="yearSelect" disabled><option>年</option></select>
                        <select id="monthSelect" disabled><option>月</option></select>
                        <select id="scaleSelect">
                            <option value="25%" selected>圖: 小</option>
                            <option value="50%">圖: 中</option>
                            <option value="75%">圖: 大</option>
                            <option value="100%">圖: 原</option>
                        </select>
                    </div>
                </div>
                <div class="chat-container" id="chatBox">
                    <div class="empty-state">請從左側選擇要瀏覽的成員</div>
                </div>
            </div>

            <script>
                const allData = {json_data};
                const avatarMap = {json_avatars};
                let currentMember = null;
                let currentYears = {{}}; 
                let scrollTimeout = null;

                const memberListEl = document.getElementById('memberList');
                const chatBox = document.getElementById('chatBox');
                const headerTitle = document.getElementById('headerTitle');
                const yearSelect = document.getElementById('yearSelect');
                const monthSelect = document.getElementById('monthSelect');
                const scaleSelect = document.getElementById('scaleSelect');
                const sortStatus = document.getElementById('sortStatus');
                const resetSortBtn = document.getElementById('resetSortBtn');

                // Lightbox functions
                function openLightbox(src) {{
                    const lb = document.getElementById('lightbox');
                    const lbImg = document.getElementById('lightbox-img');
                    lbImg.src = src;
                    lb.style.display = "flex";
                }}
                
                function closeLightbox(e) {{
                    // 因為圖片上有 stopPropagation，這裡不需要額外判斷
                    // 只要觸發到這個 container 的 click 就是點擊背景
                    document.getElementById('lightbox').style.display = "none";
                }}

                function init() {{
                    let members = Object.keys(allData).sort();
                    
                    // --- 讀取自訂排序 ---
                    const savedOrder = localStorage.getItem('nogi_member_order');
                    if (savedOrder) {{
                        try {{
                            const customOrder = JSON.parse(savedOrder);
                            // 檢查成員是否有變動，只保留存在的
                            const validCustom = customOrder.filter(m => members.includes(m));
                            const missing = members.filter(m => !validCustom.includes(m));
                            members = [...validCustom, ...missing];
                            
                            updateSortStatus(true);
                        }} catch(e) {{
                            console.error("Sort order load failed");
                        }}
                    }}

                    renderSidebar(members);
                    
                    scaleSelect.onchange = function() {{
                        document.documentElement.style.setProperty('--img-scale', this.value);
                    }};
                    document.documentElement.style.setProperty('--img-scale', '25%');

                    const lastMember = localStorage.getItem('nogi_last_member');
                    if (lastMember && allData[lastMember]) {{
                        loadMember(lastMember);
                    }}

                    chatBox.addEventListener('scroll', function() {{
                        if (!currentMember) return;
                        clearTimeout(scrollTimeout);
                        scrollTimeout = setTimeout(() => {{
                            localStorage.setItem('nogi_scroll_' + currentMember, chatBox.scrollTop);
                        }}, 200);
                    }});
                }}

                function renderSidebar(members) {{
                    memberListEl.innerHTML = '';
                    members.forEach(m => {{
                        const div = document.createElement('div');
                        div.className = 'member-item';
                        div.draggable = true; // 開啟拖曳
                        div.dataset.name = m;

                        let avatarHtml = `<div class="member-avatar-icon">${{m[0]}}</div>`;
                        if (avatarMap[m]) {{
                            avatarHtml = `<div class="member-avatar-icon"><img src="${{avatarMap[m]}}"></div>`;
                        }}

                        div.innerHTML = `${{avatarHtml}}<div>${{m}}</div>`;
                        div.onclick = () => loadMember(m);
                        
                        // Drag Events
                        div.addEventListener('dragstart', handleDragStart);
                        div.addEventListener('dragover', handleDragOver);
                        div.addEventListener('drop', handleDrop);
                        div.addEventListener('dragenter', handleDragEnter);
                        div.addEventListener('dragleave', handleDragLeave);

                        memberListEl.appendChild(div);
                    }});
                }}

                // --- Drag and Drop Logic ---
                let dragSrcEl = null;

                function handleDragStart(e) {{
                    this.classList.add('dragging');
                    dragSrcEl = this;
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('text/html', this.innerHTML);
                }}

                function handleDragOver(e) {{
                    if (e.preventDefault) {{ e.preventDefault(); }}
                    e.dataTransfer.dropEffect = 'move';
                    return false;
                }}

                function handleDragEnter(e) {{
                    this.classList.add('over');
                }}

                function handleDragLeave(e) {{
                    this.classList.remove('over');
                }}

                function handleDrop(e) {{
                    if (e.stopPropagation) {{ e.stopPropagation(); }}
                    
                    // 移除樣式
                    document.querySelectorAll('.member-item').forEach(col => {{
                        col.classList.remove('over');
                        col.classList.remove('dragging');
                    }});

                    if (dragSrcEl !== this) {{
                        // 交換 DOM 位置
                        // 簡單邏輯: 插入到目標之前或之後
                        const allItems = [...memberListEl.querySelectorAll('.member-item')];
                        const srcIndex = allItems.indexOf(dragSrcEl);
                        const targetIndex = allItems.indexOf(this);

                        if (srcIndex < targetIndex) {{
                            this.after(dragSrcEl);
                        }} else {{
                            this.before(dragSrcEl);
                        }}

                        saveSortOrder();
                    }}
                    return false;
                }}

                function saveSortOrder() {{
                    const items = document.querySelectorAll('.member-item');
                    const order = Array.from(items).map(item => item.dataset.name);
                    localStorage.setItem('nogi_member_order', JSON.stringify(order));
                    updateSortStatus(true);
                }}

                function resetSort() {{
                    localStorage.removeItem('nogi_member_order');
                    location.reload(); // 重新整理最快
                }}

                function updateSortStatus(isCustom) {{
                    if (isCustom) {{
                        sortStatus.textContent = "排序：自訂";
                        sortStatus.style.color = "#7e1083";
                        sortStatus.style.fontWeight = "bold";
                        resetSortBtn.style.display = "inline-block";
                    }} else {{
                        sortStatus.textContent = "排序：50音 (預設)";
                        sortStatus.style.color = "#666";
                        sortStatus.style.fontWeight = "normal";
                        resetSortBtn.style.display = "none";
                    }}
                }}

                // --- End D&D ---

                function loadMember(name) {{
                    currentMember = name;
                    localStorage.setItem('nogi_last_member', name);

                    document.querySelectorAll('.member-item').forEach(el => el.classList.remove('active'));
                    const targetItem = document.querySelector(`.member-item[data-name="${{name}}"]`);
                    if(targetItem) targetItem.classList.add('active');
                    
                    headerTitle.textContent = name;
                    analyzeDates(name);
                    renderMessages(name);
                }}

                function analyzeDates(name) {{
                    const msgs = allData[name];
                    currentYears = {{}};
                    msgs.forEach(msg => {{
                        const y = msg.ts.substring(0, 4);
                        const m = msg.ts.substring(4, 6);
                        if (!currentYears[y]) currentYears[y] = new Set();
                        currentYears[y].add(m);
                    }});
                    const years = Object.keys(currentYears).sort().reverse();
                    yearSelect.innerHTML = '<option value="">年</option>';
                    years.forEach(y => {{
                        const opt = document.createElement('option');
                        opt.value = y;
                        opt.textContent = y;
                        yearSelect.appendChild(opt);
                    }});
                    yearSelect.disabled = false;
                    monthSelect.innerHTML = '<option value="">月</option>';
                    monthSelect.disabled = true;
                    yearSelect.onchange = () => updateMonthSelect(yearSelect.value);
                    monthSelect.onchange = () => scrollToDate(yearSelect.value, monthSelect.value);
                }}

                function updateMonthSelect(year) {{
                    monthSelect.innerHTML = '<option value="">月</option>';
                    if (!year) {{ monthSelect.disabled = true; return; }}
                    const months = Array.from(currentYears[year]).sort();
                    months.forEach(m => {{
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.textContent = m + "月";
                        monthSelect.appendChild(opt);
                    }});
                    monthSelect.disabled = false;
                }}

                function renderMessages(name) {{
                    chatBox.innerHTML = '';
                    const msgs = allData[name];
                    let lastDate = '';
                    let lastMonthKey = '';

                    const fragment = document.createDocumentFragment();

                    msgs.forEach(msg => {{
                        const msgDiv = document.createElement('div');
                        const dateStr = msg.d;
                        const monthKey = msg.ts.substring(0, 6);

                        if (dateStr !== lastDate) {{
                            const sep = document.createElement('div');
                            sep.className = 'timestamp-separator';
                            sep.textContent = dateStr;
                            if (monthKey !== lastMonthKey) {{
                                sep.id = 'anchor-' + monthKey;
                                lastMonthKey = monthKey;
                            }}
                            fragment.appendChild(sep);
                            lastDate = dateStr;
                        }}

                        let contentHtml = '';
                        const safePath = name + '/' + msg.f;

                        if (msg.t === '.txt') {{
                            const textContent = msg.c.replace(/\\n/g, '<br>');
                            contentHtml = `<div class="bubble">${{textContent}}</div>`;
                        }} else if (['.jpg', '.jpeg', '.png'].includes(msg.t)) {{
                            contentHtml = `<div class="bubble media-bubble"><img src="${{safePath}}" class="chat-img" loading="lazy" onclick="openLightbox(this.src)"></div>`;
                        }} else if (msg.t === '.mp4') {{
                            contentHtml = `<div class="bubble media-bubble"><video src="${{safePath}}" controls class="chat-video" preload="metadata"></video></div>`;
                        }} else if (['.m4a', '.mp3', '.wav'].includes(msg.t)) {{
                            contentHtml = `<div class="bubble media-bubble"><audio src="${{safePath}}" controls class="chat-audio"></audio></div>`;
                        }}

                        msgDiv.className = 'msg-row';
                        
                        let avatarHtml = `<div class="avatar">${{name[0]}}</div>`;
                        if (avatarMap[name]) {{
                            avatarHtml = `<div class="avatar"><img src="${{avatarMap[name]}}"></div>`;
                        }}

                        msgDiv.innerHTML = `
                            ${{avatarHtml}}
                            <div class="bubble-wrapper">${{contentHtml}}</div>
                            <div class="time-label">${{msg.hm}}</div>
                        `;
                        fragment.appendChild(msgDiv);
                    }});

                    chatBox.appendChild(fragment);

                    const savedScroll = localStorage.getItem('nogi_scroll_' + name);
                    if (savedScroll) {{
                        chatBox.scrollTop = parseInt(savedScroll);
                    }} else {{
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }}
                }}

                function scrollToDate(year, month) {{
                    if (!year || !month) return;
                    const id = 'anchor-' + year + month;
                    const el = document.getElementById(id);
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'auto', block: 'start' }});
                    }}
                }}

                init();
            </script>
        </body>
        </html>
        """
        output_path = os.path.join(group_folder_path, "index.html")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True, output_path
        except Exception as e:
            return False, str(e)

    def _format_time(self, ts):
        if len(ts) >= 12: return f"{ts[8:10]}:{ts[10:12]}"
        return ""
    def _format_date(self, ts):
        if len(ts) >= 8: return f"{ts[0:4]}/{ts[4:6]}/{ts[6:8]}"
        return ""

# --- 主程式 (v14.0) ---
class NogiBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("乃木坂MSG 備份工具 (Nogizaka Only)")
        self.root.geometry("600x600")
        
        style = ttk.Style()
        style.configure("TButton", font=("Microsoft JhengHei", 10))
        style.configure("TLabel", font=("Microsoft JhengHei", 10))
        style.configure("TLabelframe.Label", font=("Microsoft JhengHei", 10, "bold"))
        style.configure("TCheckbutton", font=("Microsoft JhengHei", 10))

        # --- 1. 設定區域 ---
        self.frame_settings = ttk.LabelFrame(root, text="備份參數", padding=15)
        self.frame_settings.pack(fill="x", padx=10, pady=10)

        # Row 0: Token
        ttk.Label(self.frame_settings, text="Refresh Token:").grid(row=0, column=0, sticky="w", pady=5)
        self.token_entry = ttk.Entry(self.frame_settings, width=50)
        self.token_entry.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)
        
        # Row 1: Path
        ttk.Label(self.frame_settings, text="儲存位置:").grid(row=1, column=0, sticky="w", pady=5)
        self.path_var = tk.StringVar(value=os.getcwd())
        self.path_entry = ttk.Entry(self.frame_settings, textvariable=self.path_var, width=40)
        self.path_entry.grid(row=1, column=1, sticky="w", padx=5)
        self.btn_browse = ttk.Button(self.frame_settings, text="瀏覽...", command=self.browse_folder)
        self.btn_browse.grid(row=1, column=2, padx=5)

        # Row 2: Member
        ttk.Label(self.frame_settings, text="指定成員 (選填):").grid(row=2, column=0, sticky="w", pady=5)
        self.member_var = tk.StringVar()
        self.member_entry = ttk.Entry(self.frame_settings, textvariable=self.member_var, width=20)
        self.member_entry.grid(row=2, column=1, sticky="w", padx=5)
        ttk.Label(self.frame_settings, text="(備份用，留空 = 全部)").grid(row=2, column=2, sticky="w")

        # Row 3: 提示
        lbl_hint = ttk.Label(self.frame_settings, text="(可用 , 分隔多位成員 如：久保史緒里,田村真佑)", foreground="#666666", font=("Microsoft JhengHei", 8))
        lbl_hint.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 5))

        # Row 4: Nickname
        ttk.Label(self.frame_settings, text="Msg 暱稱:").grid(row=4, column=0, sticky="w", pady=5)
        self.nickname_var = tk.StringVar()
        self.nickname_entry = ttk.Entry(self.frame_settings, textvariable=self.nickname_var, width=20)
        self.nickname_entry.grid(row=4, column=1, sticky="w", padx=5)
        ttk.Label(self.frame_settings, text="(產生網頁用，替換 %%%)").grid(row=4, column=2, sticky="w")


        # --- 2. 操作按鈕 ---
        self.frame_action = ttk.Frame(root, padding=10)
        self.frame_action.pack(fill="x", padx=10)

        self.btn_start = ttk.Button(self.frame_action, text="開始備份", command=self.start_backup_thread)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_stop = ttk.Button(self.frame_action, text="停止備份", command=self.stop_process, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Separator(self.frame_action, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # HTML 產生按鈕區域
        self.frame_html = ttk.Frame(self.frame_action)
        self.frame_html.pack(side="right", fill="x", expand=True)

        self.btn_html = ttk.Button(self.frame_html, text="產生入口網頁", command=self.generate_html_action)
        self.btn_html.pack(side="left", fill="x", expand=True, padx=5)
        
        self.use_avatar_var = tk.BooleanVar(value=False)
        self.chk_avatar = ttk.Checkbutton(self.frame_html, text="自訂頭像", variable=self.use_avatar_var)
        self.chk_avatar.pack(side="right", padx=5)

        # --- 3. 執行紀錄 ---
        self.log_area = scrolledtext.ScrolledText(root, height=12, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_area.insert(tk.END, "V14.0 更新：Lightbox 誤觸修正，側邊欄支援拖曳排序功能。\n")
        self.log_area.config(state='disabled')

        self.process = None
        self.is_running = False

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, str(msg) + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def start_backup_thread(self):
        if not os.path.exists("colmsg.exe"):
            messagebox.showerror("錯誤", "找不到 colmsg.exe！")
            return

        token = self.token_entry.get().strip()
        if not token:
            messagebox.showwarning("警告", "請輸入 Refresh Token")
            return

        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.log("-" * 30)
        self.log("=== 開始執行備份 ===")
        
        threading.Thread(target=self.run_colmsg, args=(token,), daemon=True).start()

    def run_colmsg(self, token):
        save_dir = self.path_var.get()
        member_input = self.member_var.get().strip()
        
        cmd = ["colmsg.exe", "--n_refresh_token", token, "-d", save_dir]
        
        if member_input:
            names = re.split(r'[,,]', member_input)
            for n in names:
                n = n.strip()
                if n:
                    cmd.extend(["--name", n])
                    self.log(f"指定成員: {n}")

        self.log(f"執行中...")
        
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8', 
                bufsize=1,
                startupinfo=startupinfo
            )

            for line in self.process.stdout:
                if not self.is_running:
                    break
                self.root.after(0, self.log, line.strip())

            self.process.wait()
            
            if self.is_running:
                if self.process.returncode == 0:
                    self.root.after(0, self.log, "=== 備份完成 ===")
                    self.root.after(0, lambda: messagebox.showinfo("成功", "備份任務已完成"))
                else:
                    self.root.after(0, self.log, f"=== 異常結束 ({self.process.returncode}) ===")

        except Exception as e:
            self.root.after(0, self.log, f"執行錯誤: {e}")
        finally:
            self.root.after(0, self.reset_buttons)

    def stop_process(self):
        self.is_running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.log("!!! 強制停止 !!!")

    def reset_buttons(self):
        self.is_running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def generate_html_action(self):
        nickname = self.nickname_var.get().strip()
        use_avatar = self.use_avatar_var.get()
        
        initial_dir = os.path.join(self.path_var.get(), "nogizaka")
        if not os.path.exists(initial_dir):
            initial_dir = self.path_var.get()

        target_dir = filedialog.askdirectory(initialdir=initial_dir, title="請選擇 nogizaka 資料夾")
        
        if target_dir:
            if use_avatar:
                self.open_avatar_dialog(target_dir, nickname)
            else:
                self.run_generation(target_dir, nickname, {})

    def open_avatar_dialog(self, target_dir, nickname):
        members = []
        try:
            for entry in os.listdir(target_dir):
                if os.path.isdir(os.path.join(target_dir, entry)) and len(os.listdir(os.path.join(target_dir, entry))) > 0:
                    members.append(entry)
            members.sort()
        except Exception as e:
            messagebox.showerror("錯誤", f"讀取成員失敗: {e}")
            return

        if not members:
            messagebox.showwarning("提示", "找不到成員資料夾，無法設定頭像。")
            return

        dialog = AvatarSelectionWindow(self.root, members, target_dir)
        self.root.wait_window(dialog)
        self.run_generation(target_dir, nickname, dialog.avatar_map)

    def run_generation(self, target_dir, nickname, avatar_map):
        gen = ChatGenerator()
        success, result = gen.generate_single_index(target_dir, nickname, avatar_map)
        if success:
            msg = f"整合完成！\n"
            if nickname: msg += f"Msg 暱稱已替換為: {nickname}\n"
            msg += f"\n檔案位置: {result}\n請手動開啟瀏覽。"
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("失敗", result)

if __name__ == "__main__":
    root = tk.Tk()
    app = NogiBackupApp(root)
    root.mainloop()
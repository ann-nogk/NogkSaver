import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import re
import json
import shutil
import webbrowser

# --- Avatar 選擇視窗 ---
class AvatarSelectionWindow(tk.Toplevel):
    def __init__(self, parent, member_list, target_dir):
        super().__init__(parent)
        self.title("設定成員頭像")
        self.geometry("460x550") 
        self.member_list = member_list
        self.target_dir = target_dir
        self.avatar_map = {} 
        self.parent = parent
        self.attributes('-topmost', True)

        ttk.Label(self, text="請為成員選擇頭像圖片:", padding=15).pack(fill='x')

        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=15, pady=5)
        
        self.canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.bind("<Enter>", self._bind_mouse_scroll)
        self.bind("<Leave>", self._unbind_mouse_scroll)
        self.bind("<Up>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Down>", lambda event: self.canvas.yview_scroll(1, "units"))

        self.path_vars = {}
        for i, member in enumerate(member_list):
            row = ttk.Frame(self.scrollable_frame, padding=(5, 5))
            row.pack(fill='x', pady=2)
            
            ttk.Label(row, text=member, width=12, anchor='w').pack(side='left')
            path_var = tk.StringVar()
            self.path_vars[member] = path_var
            entry = ttk.Entry(row, textvariable=path_var)
            entry.pack(side='left', fill='x', expand=True, padx=(10, 10))
            btn = ttk.Button(row, text="選擇", width=6, command=lambda m=member: self.browse_image(m))
            btn.pack(side='right')

            if i < len(member_list) - 1:
                ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', pady=(5, 5), padx=5)

        bottom_frame = ttk.Frame(self, padding=15)
        bottom_frame.pack(fill='x')

        self.progress = ttk.Progressbar(bottom_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill='x', pady=(0, 15))
        
        self.confirm_btn = ttk.Button(bottom_frame, text="確認並產生網頁", command=self.on_confirm)
        self.confirm_btn.pack(ipadx=20, ipady=5)

        self.focus_force()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mouse_scroll(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mouse_scroll(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def browse_image(self, member):
        self.attributes('-topmost', False)
        file_path = filedialog.askopenfilename(
            title=f"選擇 {member} 的頭像",
            filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.gif")],
            parent=self
        )
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        if file_path:
            self.path_vars[member].set(file_path)

    def on_confirm(self):
        self.confirm_btn.config(state="disabled", text="處理中...")
        self.progress["maximum"] = len(self.path_vars)
        self.progress["value"] = 0
        threading.Thread(target=self.process_avatars, daemon=True).start()

    def process_avatars(self):
        avatar_dir = os.path.join(self.target_dir, "avatars")
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)

        count = 0
        for member, var in self.path_vars.items():
            src_path = var.get().strip()
            if src_path and os.path.exists(src_path):
                ext = os.path.splitext(src_path)[1]
                new_filename = f"avatar_{member}{ext}"
                dest_path = os.path.join(avatar_dir, new_filename)
                try:
                    shutil.copy2(src_path, dest_path)
                    self.avatar_map[member] = f"avatars/{new_filename}"
                except Exception as e:
                    print(f"複製頭像失敗 {member}: {e}")
            count += 1
            self.after(0, self.update_progress, count)
        self.after(500, self.finish)

    def update_progress(self, value):
        self.progress["value"] = value

    def finish(self):
        self.destroy()

# --- HTML 生成器邏輯 ---
class ChatGenerator:
    def generate_single_index(self, group_folder_path, nickname="", avatar_map=None):
        if avatar_map is None:
            avatar_map = {}

        if not os.path.exists(group_folder_path):
            return False, "找不到資料夾"

        all_data = {}
        members = []
        for entry in os.listdir(group_folder_path):
            full_path = os.path.join(group_folder_path, entry)
            if os.path.isdir(full_path) and len(os.listdir(full_path)) > 0:
                if entry == "avatars": continue
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

        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nogi MSG Viewer</title>
            <style>
                body {{ background-color: #f2f3f7; font-family: "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; }}
                .sidebar {{ width: 220px; background-color: #fff; border-right: 1px solid #ddd; display: flex; flex-direction: column; flex-shrink: 0; }}
                .sidebar-header {{ padding: 15px; background-color: #6a0d6e; color: white; font-weight: bold; text-align: center; }}
                .sidebar-sort-info {{ background-color: #f8f0fc; padding: 5px 10px; font-size: 12px; color: #666; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }}
                .reset-btn {{ font-size: 10px; background: #ddd; border: none; padding: 2px 6px; cursor: pointer; border-radius: 4px; color: #333; display: none; }}
                .reset-btn:hover {{ background: #ccc; }}
                .member-list {{ overflow-y: auto; flex-grow: 1; }}
                .member-item {{ padding: 12px 20px; cursor: grab; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; transition: background 0.1s; user-select: none; }}
                .member-item:hover {{ background-color: #f9f9f9; }}
                .member-item.active {{ background-color: #f3e5f5; color: #7e1083; font-weight: bold; border-left: 4px solid #7e1083; }}
                .member-item.dragging {{ opacity: 0.5; background-color: #eee; }}
                .member-avatar-icon {{ width: 32px; height: 32px; background: #ddd; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 12px; color: #fff; overflow: hidden; flex-shrink: 0; }}
                .member-avatar-icon img {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s; }}
                .member-avatar-icon.clickable {{ cursor: zoom-in; }} 
                .member-avatar-icon.clickable:hover img {{ transform: scale(1.1); }}
                .main-area {{ flex-grow: 1; display: flex; flex-direction: column; height: 100%; position: relative; }}
                .header {{ background-color: #7e1083; color: white; height: 50px; display: flex; align-items: center; justify-content: center; padding: 0 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex-shrink: 0; position: relative; }}
                .header-center-group {{ display: flex; align-items: center; gap: 10px; }}
                .header-title {{ font-size: 18px; font-weight: bold; margin-right: 5px; }}
                select {{ padding: 3px 8px; border-radius: 12px; border: none; outline: none; background: rgba(255,255,255,0.9); color: #7e1083; font-weight: bold; cursor: pointer; font-size: 13px; }}
                #scaleSelect {{ background: rgba(255,255,255,0.7); color: #333; }}
                .chat-container {{ flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; opacity: 0; transition: opacity 0.15s ease-out; }}
                .empty-state {{ text-align: center; color: #999; margin-top: 100px; }}
                .timestamp-separator {{ text-align: center; color: #888; font-size: 12px; margin: 15px 0; background-color: rgba(0,0,0,0.05); padding: 4px 10px; border-radius: 12px; align-self: center; }}
                .msg-row {{ display: flex; align-items: flex-start; gap: 8px; margin-bottom: 10px; }}
                .avatar {{ width: 40px; height: 40px; background-color: #ccc; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; flex-shrink: 0; overflow: hidden; }}
                .avatar img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity 0.2s; }}
                .avatar.clickable {{ cursor: zoom-in; }}
                .avatar.clickable:hover {{ opacity: 0.8; }}
                .bubble-wrapper {{ display: flex; flex-direction: column; max-width: 80%; }}
                .bubble a {{ color: #0066cc; text-decoration: underline; word-break: break-all; }}
                .bubble {{ background-color: white; padding: 10px 14px; border-radius: 18px; border-top-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-wrap: break-word; line-height: 1.5; color: #333; font-size: 15px; white-space: pre-wrap; }}
                .media-bubble {{ background: transparent; box-shadow: none; padding: 0; border-radius: 12px; overflow: hidden; display: inline-block; }}
                :root {{ --img-scale: 25%; --video-scale: 65%; }}
                .chat-img {{ width: var(--img-scale); border-radius: 12px; display: block; cursor: zoom-in; border: 1px solid #eee; transition: width 0.3s; }}
                .chat-video {{ width: 100%; border-radius: 12px; max-height: 400px; display: block; margin: 0; }}
                .video-container {{ display: flex; align-items: center; gap: 8px; }}
                .video-wrapper {{ width: var(--video-scale); line-height: 0; }}
                .video-expand-btn {{ width: 30px; height: 30px; border-radius: 50%; border: none; background-color: #ddd; color: #555; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }}
                .video-expand-btn:hover {{ background-color: #bbb; color: #000; }}
                .chat-audio {{ width: 240px; }}
                .time-label {{ font-size: 11px; color: #999; margin-left: 4px; margin-top: 5px; min-width: 35px; }}
                .nav-buttons {{ position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 10px; z-index: 500; }}
                .nav-btn {{ width: 40px; height: 40px; border-radius: 50%; background: rgba(126, 16, 131, 0.8); color: white; border: none; font-size: 20px; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; opacity: 0.7; transition: opacity 0.2s, transform 0.2s; }}
                .nav-btn:hover {{ opacity: 1; transform: scale(1.1); }}
                #lightbox {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.9); align-items: center; justify-content: center; }}
                #lightbox-img {{ max-width: 90%; max-height: 90%; border-radius: 5px; box-shadow: 0 0 20px rgba(0,0,0,0.5); object-fit: contain; cursor: default; }}
                #lightbox-video {{ max-width: 90%; max-height: 90%; outline: none; }}
                @media (max-width: 768px) {{ .sidebar {{ display: none; }} .header-center-group {{ flex-wrap: wrap; justify-content: center; }} }}
            </style>
        </head>
        <body>
            <div id="lightbox" onclick="closeLightbox(event)">
                <img id="lightbox-img" src="" alt="Full size" style="display:none;" onclick="event.stopPropagation()">
                <video id="lightbox-video" controls style="display:none;" onclick="event.stopPropagation()"></video>
            </div>
            <div class="nav-buttons">
                <button class="nav-btn" title="回頂端" onclick="scrollToTop()">↑</button>
                <button class="nav-btn" title="去底部" onclick="scrollToBottom()">↓</button>
            </div>
            <div class="sidebar">
                <div class="sidebar-header">乃木坂46 MSG</div>
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

                function openLightbox(src, type='img') {{
                    const lb = document.getElementById('lightbox');
                    const lbImg = document.getElementById('lightbox-img');
                    const lbVid = document.getElementById('lightbox-video');
                    lb.style.display = "flex";
                    if (type === 'video') {{
                        lbImg.style.display = "none";
                        lbVid.style.display = "block";
                        lbVid.src = src;
                        lbVid.play();
                    }} else {{
                        lbVid.style.display = "none";
                        lbVid.pause();
                        lbImg.style.display = "block";
                        lbImg.src = src;
                    }}
                }}
                function closeLightbox(e) {{
                    const lb = document.getElementById('lightbox');
                    const lbVid = document.getElementById('lightbox-video');
                    lbVid.pause();
                    lb.style.display = "none";
                }}
                function scrollToTop() {{ chatBox.scrollTo({{ top: 0, behavior: 'smooth' }}); }}
                function scrollToBottom() {{ chatBox.scrollTo({{ top: chatBox.scrollHeight, behavior: 'smooth' }}); }}

                function init() {{
                    let members = Object.keys(allData).sort();
                    const savedOrder = localStorage.getItem('nogi_member_order');
                    if (savedOrder) {{
                        try {{
                            const customOrder = JSON.parse(savedOrder);
                            const validCustom = customOrder.filter(m => members.includes(m));
                            const missing = members.filter(m => !validCustom.includes(m));
                            members = [...validCustom, ...missing];
                            updateSortStatus(true);
                        }} catch(e) {{}}
                    }}
                    renderSidebar(members);
                    scaleSelect.onchange = function() {{ document.documentElement.style.setProperty('--img-scale', this.value); }};
                    document.documentElement.style.setProperty('--img-scale', '25%');
                    const lastMember = localStorage.getItem('nogi_last_member');
                    if (lastMember && allData[lastMember]) {{ loadMember(lastMember); }}
                    chatBox.addEventListener('scroll', function() {{
                        if (!currentMember || chatBox.style.opacity === '0') return;
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
                        div.draggable = true;
                        div.dataset.name = m;
                        let avatarHtml = `<div class="member-avatar-icon">${{m[0]}}</div>`;
                        if (avatarMap[m]) {{
                            avatarHtml = `<div class="member-avatar-icon clickable" onclick="event.stopPropagation(); openLightbox('${{avatarMap[m]}}')"><img src="${{avatarMap[m]}}"></div>`;
                        }}
                        div.innerHTML = `${{avatarHtml}}<div>${{m}}</div>`;
                        div.onclick = () => loadMember(m);
                        div.addEventListener('dragstart', handleDragStart);
                        div.addEventListener('dragover', handleDragOver);
                        div.addEventListener('drop', handleDrop);
                        div.addEventListener('dragenter', handleDragEnter);
                        div.addEventListener('dragleave', handleDragLeave);
                        memberListEl.appendChild(div);
                    }});
                }}

                let dragSrcEl = null;
                function handleDragStart(e) {{ this.classList.add('dragging'); dragSrcEl = this; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/html', this.innerHTML); }}
                function handleDragOver(e) {{ if (e.preventDefault) {{ e.preventDefault(); }} e.dataTransfer.dropEffect = 'move'; return false; }}
                function handleDragEnter(e) {{ this.classList.add('over'); }}
                function handleDragLeave(e) {{ this.classList.remove('over'); }}
                function handleDrop(e) {{
                    if (e.stopPropagation) {{ e.stopPropagation(); }}
                    document.querySelectorAll('.member-item').forEach(col => {{ col.classList.remove('over'); col.classList.remove('dragging'); }});
                    if (dragSrcEl !== this) {{
                        const allItems = [...memberListEl.querySelectorAll('.member-item')];
                        const srcIndex = allItems.indexOf(dragSrcEl);
                        const targetIndex = allItems.indexOf(this);
                        if (srcIndex < targetIndex) {{ this.after(dragSrcEl); }} else {{ this.before(dragSrcEl); }}
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
                function resetSort() {{ localStorage.removeItem('nogi_member_order'); location.reload(); }}
                function updateSortStatus(isCustom) {{
                    if (isCustom) {{
                        sortStatus.textContent = "排序：自訂"; sortStatus.style.color = "#7e1083"; sortStatus.style.fontWeight = "bold"; resetSortBtn.style.display = "inline-block";
                    }} else {{
                        sortStatus.textContent = "排序：50音 (預設)"; sortStatus.style.color = "#666"; sortStatus.style.fontWeight = "normal"; resetSortBtn.style.display = "none";
                    }}
                }}

                function loadMember(name) {{
                    chatBox.style.opacity = '0';
                    currentMember = name;
                    localStorage.setItem('nogi_last_member', name);
                    document.querySelectorAll('.member-item').forEach(el => el.classList.remove('active'));
                    const targetItem = document.querySelector(`.member-item[data-name="${{name}}"]`);
                    if(targetItem) targetItem.classList.add('active');
                    headerTitle.textContent = name;
                    analyzeDates(name);
                    setTimeout(() => {{ renderMessages(name); }}, 10);
                }}

                function analyzeDates(name) {{
                    const msgs = allData[name];
                    currentYears = {{}};
                    msgs.forEach(msg => {{
                        const y = msg.ts.substring(0, 4); const m = msg.ts.substring(4, 6);
                        if (!currentYears[y]) currentYears[y] = new Set(); currentYears[y].add(m);
                    }});
                    const years = Object.keys(currentYears).sort().reverse();
                    yearSelect.innerHTML = '<option value="">年</option>';
                    years.forEach(y => {{ const opt = document.createElement('option'); opt.value = y; opt.textContent = y; yearSelect.appendChild(opt); }});
                    yearSelect.disabled = false; monthSelect.innerHTML = '<option value="">月</option>'; monthSelect.disabled = true;
                    yearSelect.onchange = () => updateMonthSelect(yearSelect.value);
                    monthSelect.onchange = () => scrollToDate(yearSelect.value, monthSelect.value);
                }}

                function updateMonthSelect(year) {{
                    monthSelect.innerHTML = '<option value="">月</option>';
                    if (!year) {{ monthSelect.disabled = true; return; }}
                    const months = Array.from(currentYears[year]).sort();
                    months.forEach(m => {{ const opt = document.createElement('option'); opt.value = m; opt.textContent = m + "月"; monthSelect.appendChild(opt); }});
                    monthSelect.disabled = false;
                }}

                function linkify(text) {{
                    var urlRegex = /(https?:\\/\\/[^\\s]+)/g;
                    return text.replace(urlRegex, function(url) {{ return '<a href="' + url + '" target="_blank">' + url + '</a>'; }});
                }}

                function renderMessages(name) {{
                    chatBox.innerHTML = ''; const msgs = allData[name]; let lastDate = ''; let lastMonthKey = '';
                    const fragment = document.createDocumentFragment();
                    msgs.forEach(msg => {{
                        const msgDiv = document.createElement('div'); const dateStr = msg.d; const monthKey = msg.ts.substring(0, 6);
                        if (dateStr !== lastDate) {{
                            const sep = document.createElement('div'); sep.className = 'timestamp-separator'; sep.textContent = dateStr;
                            if (monthKey !== lastMonthKey) {{ sep.id = 'anchor-' + monthKey; lastMonthKey = monthKey; }}
                            fragment.appendChild(sep); lastDate = dateStr;
                        }}
                        let contentHtml = ''; const safePath = name + '/' + msg.f;
                        if (msg.t === '.txt') {{
                            let textContent = msg.c.replace(/\\n/g, '<br>'); textContent = linkify(textContent); contentHtml = `<div class="bubble">${{textContent}}</div>`;
                        }} else if (['.jpg', '.jpeg', '.png'].includes(msg.t)) {{
                            contentHtml = `<div class="bubble media-bubble"><img src="${{safePath}}" class="chat-img" onclick="openLightbox(this.src)"></div>`;
                        }} else if (msg.t === '.mp4') {{
                            contentHtml = `<div class="video-container"><div class="video-wrapper"><div class="bubble media-bubble"><video src="${{safePath}}" controls class="chat-video" preload="metadata"></video></div></div><button class="video-expand-btn" title="全螢幕播放" onclick="openLightbox('${{safePath}}', 'video')">⛶</button></div>`;
                        }} else if (['.m4a', '.mp3', '.wav'].includes(msg.t)) {{
                            contentHtml = `<div class="bubble media-bubble"><audio src="${{safePath}}" controls class="chat-audio"></audio></div>`;
                        }}
                        msgDiv.className = 'msg-row';
                        let avatarHtml = `<div class="avatar">${{name[0]}}</div>`;
                        if (avatarMap[name]) {{ avatarHtml = `<div class="avatar clickable" onclick="openLightbox('${{avatarMap[name]}}')"><img src="${{avatarMap[name]}}"></div>`; }}
                        msgDiv.innerHTML = `${{avatarHtml}}<div class="bubble-wrapper">${{contentHtml}}</div><div class="time-label">${{msg.hm}}</div>`;
                        fragment.appendChild(msgDiv);
                    }});
                    chatBox.appendChild(fragment);
                    waitForImagesAndScroll(name);
                }}

                function waitForImagesAndScroll(name) {{
                    const imgs = chatBox.querySelectorAll('img'); let loadedCount = 0; const total = imgs.length;
                    const reveal = () => {{
                        const savedScroll = localStorage.getItem('nogi_scroll_' + name);
                        if (savedScroll) {{ chatBox.scrollTop = parseInt(savedScroll); }} else {{ chatBox.scrollTop = chatBox.scrollHeight; }}
                        chatBox.style.opacity = '1';
                    }};
                    if (total === 0) {{ reveal(); }} else {{
                        const fallback = setTimeout(reveal, 1000); 
                        imgs.forEach(img => {{
                            if(img.complete) {{ loadedCount++; if(loadedCount === total) {{ clearTimeout(fallback); reveal(); }} }}
                            else {{ img.onload = img.onerror = () => {{ loadedCount++; if(loadedCount === total) {{ clearTimeout(fallback); reveal(); }} }}; }}
                        }});
                    }}
                }}
                function scrollToDate(year, month) {{
                    if (!year || !month) return;
                    const id = 'anchor-' + year + month; const el = document.getElementById(id);
                    if (el) {{ el.scrollIntoView({{ behavior: 'auto', block: 'start' }}); }}
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

# --- 主程式 (v29.0) ---
class NogiBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NogkSaver (非官方) - 乃木坂MSG 備份工具 | by ann-nogk")
        self.root.geometry("510x700") 
        
        style = ttk.Style()
        style.configure("TButton", font=("Microsoft JhengHei", 10))
        style.configure("TLabel", font=("Microsoft JhengHei", 10))
        style.configure("TLabelframe.Label", font=("Microsoft JhengHei", 10, "bold"))
        style.configure("TCheckbutton", font=("Microsoft JhengHei", 10))

        # --- 0. 頂部連結 ---
        link_frame = ttk.Frame(root, padding=(0, 5))
        link_frame.pack(fill="x", padx=10)

        # --- 1. 區塊 A: 下載與備份設定 ---
        self.frame_backup = ttk.LabelFrame(root, text="備份與下載設定", padding=15)
        self.frame_backup.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.frame_backup, text="Refresh Token:").grid(row=0, column=0, sticky="w", pady=5)
        self.token_entry = ttk.Entry(self.frame_backup, width=50)
        self.token_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5)
        
        ttk.Label(self.frame_backup, text="儲存位置:").grid(row=1, column=0, sticky="w", pady=5)
        self.path_var = tk.StringVar(value=os.getcwd())
        self.path_entry = ttk.Entry(self.frame_backup, textvariable=self.path_var)
        self.path_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.btn_browse = ttk.Button(self.frame_backup, text="瀏覽...", command=self.browse_folder)
        self.btn_browse.grid(row=1, column=2, padx=5)

        ttk.Label(self.frame_backup, text="指定成員 (選填):").grid(row=2, column=0, sticky="w", pady=5)
        self.member_var = tk.StringVar()
        self.member_entry = ttk.Entry(self.frame_backup, textvariable=self.member_var)
        self.member_entry.grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Label(self.frame_backup, text="(留空 = 備份全部)").grid(row=2, column=2, sticky="w")

        lbl_hint = ttk.Label(self.frame_backup, text="(可用 , 分隔多位成員 如：久保史緒里,田村真佑)", foreground="#666666", font=("Microsoft JhengHei", 8))
        lbl_hint.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        self.btn_start = ttk.Button(self.frame_backup, text="開始備份", command=self.start_backup_thread)
        self.btn_start.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)

        # --- 區塊 B: 網頁檢視器設定 ---
        self.frame_viewer = ttk.LabelFrame(root, text="網頁檢視器設定", padding=15)
        self.frame_viewer.pack(fill="x", padx=10, pady=10)

        ttk.Label(self.frame_viewer, text="Msg 暱稱:").grid(row=0, column=0, sticky="w", pady=5)
        self.nickname_var = tk.StringVar()
        self.nickname_entry = ttk.Entry(self.frame_viewer, textvariable=self.nickname_var, width=15)
        self.nickname_entry.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self.frame_viewer, text="(產生網頁用，替換 %%%，可留空)").grid(row=0, column=2, sticky="w")

        action_frame = ttk.Frame(self.frame_viewer)
        action_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)

        self.use_avatar_var = tk.BooleanVar(value=False)
        self.chk_avatar = ttk.Checkbutton(action_frame, text="自訂成員頭像", variable=self.use_avatar_var)
        self.chk_avatar.pack(side="left", padx=(0, 15))

        self.btn_html = ttk.Button(action_frame, text="產生入口網頁", command=self.generate_html_action)
        self.btn_html.pack(side="left", fill="x", expand=True)

        # 5. GitHub 連結
        link_frame_mid = ttk.Frame(root, padding=(0, 5))
        link_frame_mid.pack(fill="x", padx=15)
        lbl_link = ttk.Label(link_frame_mid, text="前往 GitHub 專案頁面", foreground="blue", cursor="hand2", font=("Microsoft JhengHei", 9, "underline"))
        lbl_link.pack(anchor="e")
        lbl_link.bind("<Button-1>", lambda e: self.open_github())

        # --- 執行紀錄 ---
        self.log_area = scrolledtext.ScrolledText(root, height=12, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 靜態插入歡迎訊息，不使用任何判斷式
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, "歡迎使用 NogkSaver！\n\n【已知問題】\n感謝訂閱訊息：因為 API 資料特性，訂閱時的第一則「感謝訂閱」訊息可能不會顯示在第一則。\n----------------------------------------")
        self.log_area.config(state='disabled')

        self.process = None
        self.is_running = False

    def open_github(self):
        webbrowser.open("https://github.com/ann-nogk/NogkSaver")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def log(self, msg):
        self.log_area.config(state='normal')
        # 確保有換行符
        self.log_area.insert(tk.END, "\n" + str(msg))
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
        self.log("\n" + "-" * 30)
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

    def reset_buttons(self):
        self.is_running = False
        self.btn_start.config(state="normal")

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
                full_path = os.path.join(target_dir, entry)
                if os.path.isdir(full_path) and len(os.listdir(full_path)) > 0:
                    if entry == "avatars": continue
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
        
        log_msg = f"=== 網頁產生完畢 ===\n檔案位置: {result}"
        if nickname: log_msg += f"\nMsg 暱稱: {nickname}"
        
        if success:
            self.log(log_msg)
            
            popup_msg = f"整合完成！\n"
            if nickname: popup_msg += f"Msg 暱稱已替換為: {nickname}\n"
            popup_msg += f"\n檔案位置: {result}\n請手動開啟瀏覽。"
            messagebox.showinfo("成功", popup_msg)
        else:
            self.log(f"產生失敗: {result}")
            messagebox.showerror("失敗", result)

if __name__ == "__main__":
    root = tk.Tk()
    app = NogiBackupApp(root)
    root.mainloop()
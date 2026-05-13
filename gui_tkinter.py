import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import sys
import ctypes
from datetime import datetime

from process_scanner import ProcessScanner
from service_scanner import ServiceScanner
from task_scanner import TaskScanner
from registry_scanner import RegistryScanner


class ProScanKillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("进程溯源查杀工具 v1.0")
        self.root.geometry("950x720")
        self.root.resizable(False, False)
        
        self.scanner = ProcessScanner()
        self.scan_thread = None
        self.cleanup_thread = None
        self.full_registry_scan = False
        
        self._init_ui()
        self._check_admin()
        self._update_status()
    
    def _init_ui(self):
        self.root.configure(bg='#fafafa')
        
        main_frame = tk.Frame(self.root, bg='#fafafa')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self._create_header(main_frame)
        self._create_separator(main_frame)
        self._create_input_section(main_frame)
        self._create_separator(main_frame)
        self._create_button_section(main_frame)
        self._create_progress_section(main_frame)
        self._create_log_section(main_frame)
        self._create_status_bar()
    
    def _create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#fafafa')
        header_frame.pack(fill='x', pady=(0, 10))
        
        title_label = tk.Label(
            header_frame,
            text="🔍 进程溯源查杀工具",
            font=('Microsoft YaHei UI', 18, 'bold'),
            fg='#1e232d',
            bg='#fafafa'
        )
        title_label.pack(side='left')
        
        version_label = tk.Label(
            header_frame,
            text="v1.0",
            font=('Microsoft YaHei UI', 10),
            fg='#6b7280',
            bg='#f3f4f6',
            padx=8,
            pady=3
        )
        version_label.pack(side='right')
    
    def _create_separator(self, parent):
        sep = tk.Frame(parent, height=1, bg='#e5e7eb')
        sep.pack(fill='x', pady=10)
    
    def _create_input_section(self, parent):
        input_frame = tk.Frame(parent, bg='#ffffff', relief='solid', bd=1)
        input_frame.pack(fill='x', pady=(0, 10))
        
        inner_frame = tk.Frame(input_frame, bg='#ffffff', padx=15, pady=12)
        inner_frame.pack(fill='both', expand=True)
        
        grid = tk.Frame(inner_frame, bg='#ffffff')
        grid.pack(fill='both', expand=True)
        
        tk.Label(grid, text="PID", font=('Microsoft YaHei UI', 11, 'bold'), 
                fg='#374151', bg='#ffffff', width=10, anchor='w').grid(row=0, column=0, sticky='w', pady=8)
        
        self.pid_input = tk.Entry(grid, font=('Consolas', 12), fg='#1e232d', 
                                bg='#ffffff', relief='solid', bd=1, width=40)
        self.pid_input.grid(row=0, column=1, sticky='ew', pady=8, padx=(0, 10))
        
        tk.Label(grid, text="进程名", font=('Microsoft YaHei UI', 11, 'bold'),
                fg='#374151', bg='#ffffff', width=10, anchor='w').grid(row=1, column=0, sticky='w', pady=8)
        
        self.name_input = tk.Entry(grid, font=('Consolas', 12), fg='#1e232d',
                                  bg='#ffffff', relief='solid', bd=1, width=40)
        self.name_input.grid(row=1, column=1, sticky='ew', pady=8, padx=(0, 10))
        
        tk.Label(grid, text="进程路径", font=('Microsoft YaHei UI', 11, 'bold'),
                fg='#374151', bg='#ffffff', width=10, anchor='w').grid(row=2, column=0, sticky='nw', pady=8)
        
        path_frame = tk.Frame(grid, bg='#ffffff')
        path_frame.grid(row=2, column=1, sticky='ew', pady=8, padx=(0, 10))
        
        self.path_input = tk.Entry(path_frame, font=('Consolas', 12), fg='#1e232d',
                                  bg='#ffffff', relief='solid', bd=1)
        self.path_input.pack(side='left', fill='both', expand=True)
        
        self.path_browse = tk.Button(
            path_frame,
            text="浏览",
            command=self._browse_file,
            bg='#6366f1',
            fg='#ffffff',
            activebackground='#818cf8',
            activeforeground='#ffffff',
            relief='flat',
            padx=15,
            font=('Microsoft YaHei UI', 10, 'bold')
        )
        self.path_browse.pack(side='right', padx=(5, 0))
        
        grid.columnconfigure(1, weight=1)
        
        self.pid_input.bind('<KeyRelease>', self._on_input_changed)
        self.name_input.bind('<KeyRelease>', self._on_input_changed)
        self.path_input.bind('<KeyRelease>', self._on_input_changed)
    
    def _create_button_section(self, parent):
        button_frame = tk.Frame(parent, bg='#fafafa')
        button_frame.pack(fill='x', pady=(0, 10))
        
        self.btn_scan = tk.Button(
            button_frame,
            text="🔍 检测溯源",
            command=self._start_scan,
            bg='#3b82f6',
            fg='#ffffff',
            activebackground='#60a5fa',
            activeforeground='#ffffff',
            relief='flat',
            padx=25,
            pady=10,
            font=('Microsoft YaHei UI', 11, 'bold'),
            cursor='hand2'
        )
        self.btn_scan.pack(side='left', padx=(0, 10))
        
        self.btn_delete = tk.Button(
            button_frame,
            text="🗑️ 强制清理",
            command=self._confirm_delete,
            bg='#ff4757',
            fg='#ffffff',
            activebackground='#ff6b7a',
            activeforeground='#ffffff',
            relief='flat',
            padx=25,
            pady=10,
            font=('Microsoft YaHei UI', 11, 'bold'),
            cursor='hand2'
        )
        self.btn_delete.pack(side='left', padx=(0, 10))
        
        self.chk_full_registry_var = tk.BooleanVar(value=False)
        self.chk_full_registry = tk.Checkbutton(
            button_frame,
            text="全量扫描注册表",
            variable=self.chk_full_registry_var,
            bg='#fafafa',
            fg='#374151',
            font=('Microsoft YaHei UI', 10),
            selectcolor='#ffffff',
            activebackground='#fafafa',
            anchor='center'
        )
        self.chk_full_registry.pack(side='left', padx=(0, 10))
        
        spacer = tk.Frame(button_frame, bg='#fafafa')
        spacer.pack(side='left', fill='both', expand=True)
        
        self.btn_clear = tk.Button(
            button_frame,
            text="清空日志",
            command=self._clear_log,
            bg='#6b7280',
            fg='#ffffff',
            activebackground='#9ca3af',
            activeforeground='#ffffff',
            relief='flat',
            padx=15,
            pady=10,
            font=('Microsoft YaHei UI', 10, 'bold'),
            cursor='hand2'
        )
        self.btn_clear.pack(side='right', padx=(0, 10))
        
        self.btn_export = tk.Button(
            button_frame,
            text="导出报告",
            command=self._export_report,
            bg='#10b981',
            fg='#ffffff',
            activebackground='#34d399',
            activeforeground='#ffffff',
            relief='flat',
            padx=15,
            pady=10,
            font=('Microsoft YaHei UI', 10, 'bold'),
            cursor='hand2'
        )
        self.btn_export.pack(side='right')
    
    def _create_progress_section(self, parent):
        self.progress_frame = tk.Frame(parent, bg='#ffffff', relief='solid', bd=1)
        self.progress_frame.pack(fill='x', pady=(0, 10))
        self.progress_frame.pack_forget()
        
        inner_frame = tk.Frame(self.progress_frame, bg='#ffffff', padx=15, pady=10)
        inner_frame.pack(fill='both', expand=True)
        
        self.progress_label = tk.Label(
            inner_frame,
            text="正在扫描...",
            font=('Microsoft YaHei UI', 10),
            fg='#374151',
            bg='#ffffff'
        )
        self.progress_label.pack(side='left')
        
        self.progress_bar = ttk.Progressbar(
            inner_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(15, 15))
        
        self.progress_percent = tk.Label(
            inner_frame,
            text="0%",
            font=('Microsoft YaHei UI', 10, 'bold'),
            fg='#3b82f6',
            bg='#ffffff',
            width=5
        )
        self.progress_percent.pack(side='right')
    
    def _create_log_section(self, parent):
        log_frame = tk.LabelFrame(
            parent,
            text="检测报告",
            font=('Microsoft YaHei UI', 10, 'bold'),
            fg='#374151',
            bg='#ffffff',
            padx=10,
            pady=5
        )
        log_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.log_output = scrolledtext.ScrolledText(
            log_frame,
            font=('Consolas', 11),
            fg='#1e232d',
            bg='#ffffff',
            relief='flat',
            padx=10,
            pady=10,
            wrap='none'
        )
        self.log_output.pack(fill='both', expand=True)
        
        self.log_output.tag_configure('success', foreground='#10b981')
        self.log_output.tag_configure('warning', foreground='#f59e0b')
        self.log_output.tag_configure('error', foreground='#ef4444')
        self.log_output.tag_configure('info', foreground='#3b82f6')
        self.log_output.tag_configure('header', foreground='#6366f1', font=('Consolas', 12, 'bold'))
        self.log_output.tag_configure('progress', foreground='#6366f1')
        
        self.log_output.config(state='disabled')
    
    def _create_status_bar(self):
        status_frame = tk.Frame(self.root, bg='#ffffff', relief='raised', bd=1)
        status_frame.pack(fill='x', side='bottom')
        
        self.status_admin = tk.Label(
            status_frame,
            text="权限: 检测中",
            font=('Microsoft YaHei UI', 9),
            fg='#374151',
            bg='#ffffff',
            padx=10
        )
        self.status_admin.pack(side='left')
        
        tk.Label(status_frame, text="|", fg='#d1d5db', bg='#ffffff').pack(side='left')
        
        self.status_running = tk.Label(
            status_frame,
            text="状态: 空闲",
            font=('Microsoft YaHei UI', 9),
            fg='#374151',
            bg='#ffffff',
            padx=10
        )
        self.status_running.pack(side='left')
        
        tk.Label(status_frame, text="|", fg='#d1d5db', bg='#ffffff').pack(side='left')
        
        self.status_time = tk.Label(
            status_frame,
            text="耗时: 0.00s",
            font=('Microsoft YaHei UI', 9),
            fg='#374151',
            bg='#ffffff',
            padx=10
        )
        self.status_time.pack(side='left')
        
        tk.Label(status_frame, text="|", fg='#d1d5db', bg='#ffffff').pack(side='left')
        
        self.status_os = tk.Label(
            status_frame,
            text="系统: 检测中",
            font=('Microsoft YaHei UI', 9),
            fg='#374151',
            bg='#ffffff',
            padx=10
        )
        self.status_os.pack(side='left')
    
    def _on_input_changed(self, event):
        sender = event.widget
        
        if sender == self.pid_input:
            if self.pid_input.get():
                self.name_input.delete(0, tk.END)
                self.path_input.delete(0, tk.END)
        elif sender == self.name_input:
            text = self.name_input.get()
            if text and not text.endswith('.exe'):
                self.name_input.insert(tk.END, '.exe')
            if self.name_input.get():
                self.pid_input.delete(0, tk.END)
                self.path_input.delete(0, tk.END)
        elif sender == self.path_input:
            if self.path_input.get():
                self.pid_input.delete(0, tk.END)
                self.name_input.delete(0, tk.END)
    
    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title='选择程序文件',
            filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')]
        )
        if file_path:
            self.path_input.delete(0, tk.END)
            self.path_input.insert(0, file_path)
            self._on_input_changed(tk.Event())
    
    def _check_admin(self):
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                self.status_admin.config(text="✅ 权限: 管理员", fg='#10b981')
                self._log_message('程序已以管理员权限启动', 'success')
            else:
                self.status_admin.config(text="⚠️ 权限: 非管理员", fg='#f59e0b')
                self._log_message('警告: 当前权限不足，部分功能可能受限', 'warning')
        except Exception as e:
            self.status_admin.config(text="权限: 未知")
    
    def _update_status(self):
        try:
            import platform
            os_info = platform.platform()
            self.status_os.config(text=f"系统: {os_info}")
        except:
            self.status_os.config(text="系统: 未知")
    
    def _log_message(self, message, tag='info'):
        self.log_output.config(state='normal')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_output.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_output.config(state='disabled')
        self.log_output.see(tk.END)
    
    def _clear_log(self):
        self.log_output.config(state='normal')
        self.log_output.delete(1.0, tk.END)
        self.log_output.config(state='disabled')
        self._log_message('日志已清空', 'info')
    
    def _export_report(self):
        if not self.log_output.get(1.0, tk.END).strip():
            messagebox.showwarning('提示', '没有可导出的报告内容')
            return
        
        file_path = filedialog.asksaveasfilename(
            title='导出报告',
            defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')],
            initialfile=f'ProScanKill_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_output.get(1.0, tk.END))
                messagebox.showinfo('成功', f'报告已保存至:\n{file_path}')
            except Exception as e:
                messagebox.showerror('错误', f'导出失败:\n{str(e)}')
    
    def _show_progress(self):
        self.progress_frame.pack(fill='x', pady=(0, 10))
        self.progress_bar['value'] = 0
        self.progress_percent.config(text="0%")
        self.progress_label.config(text="准备扫描...")
    
    def _update_progress(self, percent, message):
        self.progress_bar['value'] = percent
        self.progress_percent.config(text=f"{percent}%")
        self.progress_label.config(text=message)
        self.root.update_idletasks()
    
    def _hide_progress(self):
        self.progress_frame.pack_forget()
    
    def _start_scan(self):
        pid = self.pid_input.get().strip()
        name = self.name_input.get().strip()
        path = self.path_input.get().strip()
        
        if not pid and not name and not path:
            messagebox.showwarning('输入错误', '请填写 PID / 进程名 / 进程路径 任意一项')
            return
        
        input_type = None
        input_value = None
        
        if pid:
            if not pid.isdigit():
                messagebox.showerror('输入错误', 'PID 必须为纯数字')
                return
            input_type = 'pid'
            input_value = pid
        elif name:
            input_type = 'name'
            input_value = name
        elif path:
            input_type = 'path'
            input_value = path
        
        self._set_buttons_state(tk.DISABLED)
        self.status_running.config(text="状态: 扫描中...")
        self._show_progress()
        
        self.full_registry_scan = self.chk_full_registry_var.get()
        
        self.scan_thread = threading.Thread(target=self._scan_worker, args=(input_type, input_value))
        self.scan_thread.start()
    
    def _scan_worker(self, input_type, input_value):
        start_time = datetime.now()
        
        result = {
            'processes': [],
            'services': [],
            'tasks': [],
            'registry': [],
            'error': None
        }
        
        try:
            self.root.after(0, lambda: self._update_progress(5, "初始化扫描器..."))
            
            scanner = ProcessScanner()
            
            self.root.after(0, lambda: self._update_progress(10, "正在扫描进程..."))
            
            if input_type == 'pid':
                pid = int(input_value)
                proc = scanner.get_process_by_pid(pid)
                if proc:
                    result['processes'] = [proc]
            
            elif input_type == 'name':
                result['processes'] = scanner.get_processes_by_name(input_value)
            
            elif input_type == 'path':
                result['processes'] = scanner.get_processes_by_path(input_value)
            
            self.root.after(0, lambda: self._update_progress(25, "进程扫描完成"))
            
            if result['processes']:
                self.root.after(0, lambda: self._update_progress(30, "正在扫描系统服务..."))
                
                service_scanner = ServiceScanner()
                for proc in result['processes']:
                    services = service_scanner.find_matching_services(proc)
                    result['services'].extend(services)
                
                self.root.after(0, lambda: self._update_progress(50, "服务扫描完成"))
                
                self.root.after(0, lambda: self._update_progress(55, "正在扫描计划任务..."))
                
                task_scanner = TaskScanner()
                seen_tasks = set()
                for proc in result['processes']:
                    tasks = task_scanner.find_matching_tasks(proc)
                    for task in tasks:
                        task_name = task.get('name', '')
                        if task_name not in seen_tasks:
                            result['tasks'].append(task)
                            seen_tasks.add(task_name)
                
                self.root.after(0, lambda: self._update_progress(75, "计划任务扫描完成"))
                
                self.root.after(0, lambda: self._update_progress(80, "正在扫描注册表..."))
                
                registry_scanner = RegistryScanner()
                seen_registry = set()
                for proc in result['processes']:
                    entries = registry_scanner.find_matching_entries(proc, self.full_registry_scan)
                    for entry in entries:
                        entry_key = f"{entry.get('hive', '')}_{entry.get('path', '')}_{entry.get('name', '')}"
                        if entry_key not in seen_registry:
                            result['registry'].append(entry)
                            seen_registry.add(entry_key)
            
            self.root.after(0, lambda: self._update_progress(100, "扫描完成"))
            
        except Exception as e:
            result['error'] = str(e)
        
        self.root.after(0, lambda: self._scan_finished(result, start_time))
    
    def _scan_finished(self, result, start_time):
        elapsed = (datetime.now() - start_time).total_seconds()
        self.status_time.config(text=f"耗时: {elapsed:.2f}s")
        self.status_running.config(text="状态: 空闲")
        
        self._hide_progress()
        
        self._display_results(result)
        
        self._set_buttons_state(tk.NORMAL)
    
    def _display_results(self, result):
        self._log_message('=' * 60, 'header')
        self._log_message('检测完成', 'header')
        self._log_message('=' * 60, 'header')
        
        if result['error']:
            self._log_message(f"扫描出错: {result['error']}", 'error')
            return
        
        self._log_message(f"进程: {len(result['processes'])} 个", 'info')
        self._log_message(f"服务: {len(result['services'])} 个", 'info')
        self._log_message(f"计划任务: {len(result['tasks'])} 个", 'info')
        self._log_message(f"注册表: {len(result['registry'])} 个", 'info')
        
        self._log_message('-' * 60, 'info')
        
        if result['processes']:
            self._log_message('📌 进程信息', 'header')
            for proc in result['processes']:
                self._log_message(f"PID: {proc.get('pid', 'N/A')}", 'success')
                self._log_message(f"名称: {proc.get('name', 'N/A')}", 'success')
                self._log_message(f"路径: {proc.get('exe', 'N/A')}", 'success')
                self._log_message('', 'info')
        
        if result['services']:
            self._log_message('🔧 系统服务', 'header')
            for svc in result['services']:
                self._log_message(f"服务名: {svc.get('name', 'N/A')}", 'warning')
                self._log_message(f"显示名: {svc.get('display_name', 'N/A')}", 'warning')
                self._log_message(f"路径: {svc.get('config', {}).get('binary_path', 'N/A')}", 'warning')
                self._log_message('', 'info')
        
        if result['tasks']:
            self._log_message('⏰ 计划任务', 'header')
            for task in result['tasks']:
                self._log_message(f"任务名: {task.get('name', 'N/A')}", 'warning')
                self._log_message(f"命令: {task.get('command', 'N/A')}", 'warning')
                self._log_message('', 'info')
        
        if result['registry']:
            self._log_message('📝 注册表项', 'header')
            for entry in result['registry']:
                self._log_message(f"位置: {entry.get('hive', '')}\\{entry.get('path', '')}", 'error')
                self._log_message(f"键名: {entry.get('name', 'N/A')}", 'error')
                self._log_message(f"值: {entry.get('value', 'N/A')}", 'error')
                self._log_message('', 'info')
        
        self.processes = result['processes']
        self.services = result['services']
        self.tasks = result['tasks']
        self.registry_entries = result['registry']
        
        if not result['processes']:
            self._log_message('未找到匹配的进程', 'warning')
    
    def _confirm_delete(self):
        if not hasattr(self, 'processes') or not self.processes:
            messagebox.showwarning('提示', '请先执行检测操作')
            return
        
        self._show_cleanup_options()
    
    def _show_cleanup_options(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("清理选项")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="选择要执行的清理操作：",
            font=('Microsoft YaHei UI', 11, 'bold'),
            pady=10
        ).pack()
        
        var_terminate = tk.BooleanVar(value=True)
        var_file = tk.BooleanVar(value=True)
        var_registry = tk.BooleanVar(value=True)
        var_tasks = tk.BooleanVar(value=True)
        var_services = tk.BooleanVar(value=True)
        
        tk.Checkbutton(
            dialog,
            text="🔴 终止进程",
            variable=var_terminate,
            font=('Microsoft YaHei UI', 10),
            pady=5
        ).pack(anchor='w', padx=50)
        
        tk.Checkbutton(
            dialog,
            text="🗑️ 删除程序文件",
            variable=var_file,
            font=('Microsoft YaHei UI', 10),
            pady=5
        ).pack(anchor='w', padx=50)
        
        tk.Checkbutton(
            dialog,
            text="📝 删除注册表项",
            variable=var_registry,
            font=('Microsoft YaHei UI', 10),
            pady=5
        ).pack(anchor='w', padx=50)
        
        tk.Checkbutton(
            dialog,
            text="⏰ 删除计划任务",
            variable=var_tasks,
            font=('Microsoft YaHei UI', 10),
            pady=5
        ).pack(anchor='w', padx=50)
        
        tk.Checkbutton(
            dialog,
            text="🔧 删除服务",
            variable=var_services,
            font=('Microsoft YaHei UI', 10),
            pady=5
        ).pack(anchor='w', padx=50)
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        def do_cleanup():
            dialog.destroy()
            self._start_cleanup({
                'terminate': var_terminate.get(),
                'delete_file': var_file.get(),
                'delete_registry': var_registry.get(),
                'delete_tasks': var_tasks.get(),
                'delete_services': var_services.get()
            })
        
        def cancel():
            dialog.destroy()
        
        tk.Button(
            btn_frame,
            text="确认执行",
            command=do_cleanup,
            bg='#ef4444',
            fg='#ffffff',
            activebackground='#f87171',
            activeforeground='#ffffff',
            relief='flat',
            padx=20,
            pady=8,
            font=('Microsoft YaHei UI', 10, 'bold'),
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="取消",
            command=cancel,
            bg='#6b7280',
            fg='#ffffff',
            activebackground='#9ca3af',
            activeforeground='#ffffff',
            relief='flat',
            padx=20,
            pady=8,
            font=('Microsoft YaHei UI', 10, 'bold'),
            cursor='hand2'
        ).pack(side='left', padx=5)
    
    def _start_cleanup(self, options):
        self._set_buttons_state(tk.DISABLED)
        self.status_running.config(text="状态: 清理中...")
        self._show_progress()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, args=(options,))
        self.cleanup_thread.start()
    
    def _cleanup_worker(self, options):
        step = 0
        total_steps = sum(1 for v in options.values() if v)
        
        try:
            if options.get('delete_registry', False) and hasattr(self, 'registry_entries') and self.registry_entries:
                step += 1
                self.root.after(0, lambda: self._update_progress(int(step/total_steps*100), "正在删除注册表项..."))
                
                registry_scanner = RegistryScanner()
                for entry in self.registry_entries:
                    hive_str = entry.get('hive', '')
                    path = entry.get('path', '')
                    name = entry.get('name', '')
                    result = registry_scanner.delete_registry_entry(hive_str, path, name)
                    status = '✅' if result.get('success') else '❌'
                    self.root.after(0, lambda s=status, m=result.get('message', ''):
                                  self._log_message(f"{s} {m}", 'success' if result.get('success') else 'error'))
            
            if options.get('delete_tasks', False) and hasattr(self, 'tasks') and self.tasks:
                step += 1
                self.root.after(0, lambda: self._update_progress(int(step/total_steps*100), "正在删除计划任务..."))
                
                task_scanner = TaskScanner()
                for task in self.tasks:
                    task_name = task.get('name', '')
                    result = task_scanner.delete_task(task_name, monitor_mode=True, monitor_seconds=8)
                    status = '✅' if result.get('success') else '❌'
                    self.root.after(0, lambda s=status, m=result.get('message', ''):
                                  self._log_message(f"{s} {m}", 'success' if result.get('success') else 'error'))
            
            if options.get('delete_services', False) and hasattr(self, 'services') and self.services:
                step += 1
                self.root.after(0, lambda: self._update_progress(int(step/total_steps*100), "正在删除服务..."))
                
                service_scanner = ServiceScanner()
                for service in self.services:
                    service_name = service.get('name', '')
                    result = service_scanner.delete_service(service_name)
                    status = '✅' if result.get('success') else '❌'
                    self.root.after(0, lambda s=status, m=result.get('message', ''):
                                  self._log_message(f"{s} {m}", 'success' if result.get('success') else 'error'))
            
            if options.get('terminate', False) and hasattr(self, 'processes') and self.processes:
                step += 1
                self.root.after(0, lambda: self._update_progress(int(step/total_steps*100), "正在终止进程..."))
                
                scanner = ProcessScanner()
                
                failed_pids = []
                pids = [proc.get('pid') for proc in self.processes if proc.get('pid')]
                term_results = scanner.terminate_processes(pids)
                
                for r in term_results:
                    status = '✅' if r.get('success') else '❌'
                    self.root.after(0, lambda s=status, m=r.get('message', ''):
                                  self._log_message(f"{s} {m}", 'success' if r.get('success') else 'error'))
                    if not r.get('success'):
                        failed_pids.append(r.get('pid'))
                
                if failed_pids:
                    self.root.after(0, lambda: self._log_message('尝试通过进程名重新终止...', 'info'))
                    
                    for proc in self.processes:
                        proc_name = proc.get('name', '')
                        if proc_name:
                            processes_by_name = scanner.get_processes_by_name(proc_name)
                            if processes_by_name:
                                new_pids = [p.get('pid') for p in processes_by_name if p.get('pid')]
                                new_results = scanner.terminate_processes(new_pids)
                                for r in new_results:
                                    status = '✅' if r.get('success') else '❌'
                                    self.root.after(0, lambda s=status, m=r.get('message', ''):
                                                  self._log_message(f"{s} {m}", 'success' if r.get('success') else 'error'))
            
            import time
            if options.get('delete_file', False) and hasattr(self, 'processes') and self.processes:
                step += 1
                self.root.after(0, lambda: self._update_progress(int(step/total_steps*100), "正在删除程序文件..."))
                
                time.sleep(1)
                
                scanner = ProcessScanner()
                for proc in self.processes:
                    if proc.get('exe'):
                        file_result = scanner.delete_file(proc['exe'])
                        status = '✅' if file_result.get('success') else '❌'
                        self.root.after(0, lambda s=status, m=file_result.get('message', ''):
                                      self._log_message(f"{s} {m}", 'success' if file_result.get('success') else 'error'))
            
            self.root.after(0, lambda: self._update_progress(100, "清理完成"))
            
            self.root.after(0, lambda: self._log_message('=' * 60, 'header'))
            self.root.after(0, lambda: self._log_message('清理操作完成', 'header'))
            self.root.after(0, lambda: self._log_message('=' * 60, 'header'))
            
        except Exception as e:
            self.root.after(0, lambda: self._log_message(f"清理过程出错: {str(e)}", 'error'))
        
        self.root.after(0, self._cleanup_finished)
    
    def _cleanup_finished(self):
        self.status_running.config(text="状态: 空闲")
        self._hide_progress()
        self._set_buttons_state(tk.NORMAL)
    
    def _set_buttons_state(self, state):
        self.btn_scan.config(state=state)
        self.btn_delete.config(state=state)
        input_state = 'normal' if state == tk.NORMAL else 'disabled'
        self.pid_input.config(state=input_state)
        self.name_input.config(state=input_state)
        self.path_input.config(state=input_state)
    
    def run(self):
        self.root.mainloop()


def main():
    from gui_tkinter import ProScanKillApp
    import tkinter as tk
    
    root = tk.Tk()
    app = ProScanKillApp(root)
    app.run()


if __name__ == '__main__':
    main()

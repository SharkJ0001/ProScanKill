import sys
import os
import ctypes
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QTextEdit, QStatusBar, QVBoxLayout, QHBoxLayout,
    QMessageBox, QFileDialog, QFrame, QGridLayout, QProgressBar,
    QCheckBox
)
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from process_scanner import ProcessScanner
from service_scanner import ServiceScanner
from task_scanner import TaskScanner
from registry_scanner import RegistryScanner


class ScanThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    
    def __init__(self, input_type, input_value, full_registry_scan=False):
        super().__init__()
        self.input_type = input_type
        self.input_value = input_value
        self.full_registry_scan = full_registry_scan
    
    def run(self):
        result = {
            'processes': [],
            'services': [],
            'tasks': [],
            'registry': [],
            'error': None
        }
        
        try:
            scanner = ProcessScanner()
            
            if self.input_type == 'pid':
                pid = int(self.input_value)
                proc = scanner.get_process_by_pid(pid)
                if proc:
                    result['processes'] = [proc]
            
            elif self.input_type == 'name':
                result['processes'] = scanner.get_processes_by_name(self.input_value)
            
            elif self.input_type == 'path':
                result['processes'] = scanner.get_processes_by_path(self.input_value)
            
            self.progress.emit(25)
            
            if result['processes']:
                service_scanner = ServiceScanner()
                for proc in result['processes']:
                    services = service_scanner.find_matching_services(proc)
                    result['services'].extend(services)
                
                self.progress.emit(50)
                
                task_scanner = TaskScanner()
                seen_tasks = set()
                for proc in result['processes']:
                    tasks = task_scanner.find_matching_tasks(proc)
                    for task in tasks:
                        task_name = task.get('name', '')
                        if task_name not in seen_tasks:
                            result['tasks'].append(task)
                            seen_tasks.add(task_name)
                
                self.progress.emit(75)
                
                registry_scanner = RegistryScanner()
                seen_registry = set()
                for proc in result['processes']:
                    entries = registry_scanner.find_matching_entries(proc, self.full_registry_scan)
                    for entry in entries:
                        entry_key = f"{entry.get('hive', '')}_{entry.get('path', '')}_{entry.get('name', '')}"
                        if entry_key not in seen_registry:
                            result['registry'].append(entry)
                            seen_registry.add(entry_key)
                
                self.progress.emit(100)
        
        except Exception as e:
            result['error'] = str(e)
        
        self.finished.emit(result)


class CleanupThread(QThread):
    finished = pyqtSignal(list)
    
    def __init__(self, processes, options, registry_entries=None, tasks=None):
        super().__init__()
        self.processes = processes
        self.options = options
        self.registry_entries = registry_entries or []
        self.tasks = tasks or []
    
    def run(self):
        results = []
        
        if self.options.get('delete_registry', False) and self.registry_entries:
            reg_scanner = RegistryScanner()
            for entry in self.registry_entries:
                reg_result = reg_scanner.delete_registry_entry(
                    entry['hive'], entry['path'], entry['name']
                )
                results.append(reg_result)
        
        if self.options.get('delete_tasks', False) and self.tasks:
            task_scanner = TaskScanner()
            for task in self.tasks:
                task_result = task_scanner.delete_task(task['name'])
                results.append(task_result)
        
        if self.options.get('terminate', False):
            scanner = ProcessScanner()
            pids = [p['pid'] for p in self.processes]
            term_results = scanner.terminate_processes(pids)
            results.extend(term_results)
        
        if self.options.get('delete_file', False):
            scanner = ProcessScanner()
            for proc in self.processes:
                if proc.get('exe'):
                    file_result = scanner.delete_file(proc['exe'])
                    results.append(file_result)
        
        self.finished.emit(results)


class ProScanKillMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ProScanKill_SharkJ0001')
        self.resize(950, 720)
        self.setMinimumSize(800, 600)
        
        # 设置窗口图标（使用try-except防止图标加载失败导致程序异常）
        try:
            icon_path = self._get_icon_path()
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.process_scanner = ProcessScanner()
        self.scan_thread = None
        self.cleanup_thread = None
        
        self._setup_theme()
        self._init_ui()
        self._check_admin()
        self._update_status()
    
    def _get_icon_path(self):
        """获取图标文件路径，支持打包后和开发环境"""
        if getattr(sys, 'frozen', False):
            # 打包后运行
            base_path = sys._MEIPASS
            return os.path.join(base_path, 'favicon.ico')
        else:
            # 开发环境
            return os.path.join(os.path.dirname(__file__), 'favicon.ico')
    
    def _setup_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 35, 45))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 250))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 35, 45))
        palette.setColor(QPalette.ColorRole.Text, QColor(30, 35, 45))
        palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 250))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(30, 35, 45))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(230, 80, 80))
        palette.setColor(QPalette.ColorRole.Link, QColor(30, 100, 200))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(30, 100, 200))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #fafafa;
            }
            QFrame {
                border: none;
            }
            QLabel {
                color: #1e232d;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 12px;
                color: #1e232d;
                font-size: 13px;
                selection-background-color: #1e60f5;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
                color: #ffffff;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
            QPushButton#btn_scan {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton#btn_scan:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
            }
            QPushButton#btn_delete {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff4757, stop:1 #c0392b);
                border: 2px solid #a93226;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton#btn_delete:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b7a, stop:1 #e74c3c);
            }
            QPushButton#btn_delete:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #c0392b, stop:1 #a93226);
            }
            QPushButton#btn_clear {
                background-color: #6b7280;
            }
            QPushButton#btn_clear:hover {
                background-color: #9ca3af;
            }
            QPushButton#btn_export {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
            }
            QPushButton#btn_export:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton#btn_browse {
                background-color: #6366f1;
                color: #ffffff;
                padding: 8px 16px;
                min-width: 60px;
                min-height: 34px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#btn_browse:hover {
                background-color: #818cf8;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                color: #1e232d;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
            QStatusBar {
                background-color: #ffffff;
                color: #4b5563;
                border-top: 1px solid #e5e7eb;
            }
            QStatusBar::item {
                border: none;
            }
            QProgressBar {
                background-color: #e5e7eb;
                border: 1px solid #d1d5db;
                border-radius: 3px;
                text-align: center;
                height: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 2px;
            }
            QCheckBox {
                color: #374151;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QMessageBox {
                background-color: #fafafa;
            }
            QMessageBox QLabel {
                color: #1e232d;
            }
            QMessageBox QPushButton {
                background-color: #e5e7eb;
                color: #1e232d;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 500;
            }
            QMessageBox QPushButton:hover {
                background-color: #d1d5db;
            }
        """)
    
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 15)
        
        self._init_header(main_layout)
        self._init_input_section(main_layout)
        self._init_button_section(main_layout)
        self._init_summary_section(main_layout)
        self._init_log_section(main_layout)
        self._init_status_bar()
    
    def _init_header(self, parent_layout):
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel('🔍 进程溯源查杀工具')
        title_label.setStyleSheet('font-size: 18px; font-weight: 700; color: #1e232d;')
        
        version_label = QLabel('v2.3')
        version_label.setStyleSheet('font-size: 11px; color: #6b7280; background-color: #f3f4f6; padding: 3px 8px; border-radius: 10px;')
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(version_label)
         
        parent_layout.addWidget(header_frame)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet('background-color: #e5e7eb;')
        parent_layout.addWidget(separator)
    
    def _init_input_section(self, parent_layout):
        input_frame = QFrame()
        input_frame.setStyleSheet('background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;')
        
        grid_layout = QGridLayout(input_frame)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(15, 12, 15, 12)
        
        grid_layout.addWidget(QLabel('PID'), 0, 0)
        self.pid_input = QLineEdit()
        self.pid_input.setPlaceholderText('请输入十进制进程PID')
        self.pid_input.setMaxLength(10)
        self.pid_input.textChanged.connect(self._on_input_changed)
        grid_layout.addWidget(self.pid_input, 0, 1)
        
        grid_layout.addWidget(QLabel('进程名'), 1, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('例如: virus.exe')
        self.name_input.textChanged.connect(self._on_input_changed)
        grid_layout.addWidget(self.name_input, 1, 1)
        
        grid_layout.addWidget(QLabel('路径'), 2, 0)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText('请输入程序绝对磁盘路径')
        self.path_input.textChanged.connect(self._on_input_changed)
        
        self.path_browse = QPushButton('浏览')
        self.path_browse.setObjectName('btn_browse')
        self.path_browse.setStyleSheet('''
            QPushButton {
                background-color: #6366f1;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 3px 16px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #818cf8;
            }
        ''')
        self.path_browse.clicked.connect(self._browse_file)
        
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        path_layout.addWidget(self.path_input, 1)
        path_layout.addWidget(self.path_browse)
        
        grid_layout.addLayout(path_layout, 2, 1)
        
        parent_layout.addWidget(input_frame)
    
    def _init_button_section(self, parent_layout):
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        self.btn_scan = QPushButton('🔍 检测溯源')
        self.btn_scan.setObjectName('btn_scan')
        self.btn_scan.clicked.connect(self._start_scan)
        
        self.btn_delete = QPushButton('🗑️ 强制清理')
        self.btn_delete.setObjectName('btn_delete')
        self.btn_delete.clicked.connect(self._confirm_delete)
        
        self.chk_full_registry = QCheckBox('全量扫描注册表')
        self.chk_full_registry.setStyleSheet('color: #374151; font-size: 12px;')
        
        self.btn_clear = QPushButton('清空日志')
        self.btn_clear.setObjectName('btn_clear')
        self.btn_clear.clicked.connect(self._clear_log)
        
        self.btn_export = QPushButton('导出报告')
        self.btn_export.setObjectName('btn_export')
        self.btn_export.clicked.connect(self._export_report)
        
        button_layout.addWidget(self.btn_scan)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.chk_full_registry)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_clear)
        button_layout.addWidget(self.btn_export)
        
        parent_layout.addWidget(button_frame)
    
    def _init_summary_section(self, parent_layout):
        summary_frame = QFrame()
        summary_frame.setFixedHeight(36)
        summary_frame.setStyleSheet('background-color: #f8fafc; border-radius: 8px;')
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(12, 6, 12, 6)
        summary_layout.setSpacing(30)
        
        self.summary_labels = {
            'process': QLabel('进程: 0'),
            'service': QLabel('服务: 0'),
            'task': QLabel('计划任务: 0'),
            'registry': QLabel('注册表项: 0')
        }
        
        colors = ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b']
        icons = ['⚙️', '🔧', '⏰', '📝']
        keys = ['process', 'service', 'task', 'registry']
        
        for i, key in enumerate(keys):
            summary_layout.addStretch()
            
            item_layout = QHBoxLayout()
            item_layout.setSpacing(5)
            
            icon_label = QLabel(icons[i])
            icon_label.setStyleSheet('font-size: 14px;')
            
            label = self.summary_labels[key]
            label.setStyleSheet(f'font-size: 12px; color: {colors[i]}; font-weight: 500;')
            
            item_layout.addWidget(icon_label)
            item_layout.addWidget(label)
            
            summary_layout.addLayout(item_layout)
        
        summary_layout.addStretch()
        
        parent_layout.addWidget(summary_frame)
    
    def _update_summary(self, results):
        self.summary_labels['process'].setText(f'进程: {len(results.get("processes", []))}')
        self.summary_labels['service'].setText(f'服务: {len(results.get("services", []))}')
        self.summary_labels['task'].setText(f'计划任务: {len(results.get("tasks", []))}')
        self.summary_labels['registry'].setText(f'注册表项: {len(results.get("registry", []))}')
    
    def _init_log_section(self, parent_layout):
        log_frame = QFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)
        
        log_label = QLabel('📋 检测报告')
        log_label.setStyleSheet('font-size: 13px; font-weight: 600; color: #374151;')
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_output)
        log_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(log_frame, 1)
    
    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(28)
        self.setStatusBar(self.status_bar)
        
        self.status_admin = QLabel('权限: 检测中')
        self.status_running = QLabel('状态: 空闲')
        self.status_time = QLabel('耗时: 0.00s')
        self.status_os = QLabel('系统: 检测中')
        
        self.status_bar.addWidget(self.status_admin)
        self.status_bar.addWidget(QLabel(' | '))
        self.status_bar.addWidget(self.status_running)
        self.status_bar.addWidget(QLabel(' | '))
        self.status_bar.addWidget(self.status_time)
        self.status_bar.addWidget(QLabel(' | '))
        self.status_bar.addWidget(self.status_os)
    
    def _on_input_changed(self):
        sender = self.sender()
        
        if sender == self.pid_input:
            if self.pid_input.text():
                self.name_input.clear()
                self.path_input.clear()
        elif sender == self.name_input:
            text = self.name_input.text()
            if text and not text.endswith('.exe'):
                self.name_input.setText(text + '.exe')
            if self.name_input.text():
                self.pid_input.clear()
                self.path_input.clear()
        elif sender == self.path_input:
            if self.path_input.text():
                self.pid_input.clear()
                self.name_input.clear()
    
    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择程序文件',
            '',
            '可执行文件 (*.exe);;所有文件 (*.*)'
        )
        if file_path:
            self.path_input.setText(file_path)
    
    def _check_admin(self):
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if is_admin:
                self.status_admin.setText('✅ 权限: 管理员')
                self.status_admin.setStyleSheet('color: #10b981;')
                self._log_message('程序已以管理员权限启动', 'success')
            else:
                self.status_admin.setText('⚠️ 权限: 非管理员')
                self.status_admin.setStyleSheet('color: #f59e0b;')
                self._log_message('警告: 当前权限不足，部分功能可能受限', 'warning')
        except Exception as e:
            self.status_admin.setText('权限: 未知')
    
    def _update_status(self):
        try:
            import platform
            os_info = platform.platform()
            self.status_os.setText(f'系统: {os_info}')
        except:
            self.status_os.setText('系统: Windows')
    
    def _log_message(self, message, level='info'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        level_styles = {
            'info': '#374151',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444'
        }
        
        color = level_styles.get(level, '#374151')
        html = f'<span style="color: {color};">[{timestamp}] {message}</span><br>'
        
        self.log_output.append(html)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
    
    def _clear_log(self):
        self.log_output.clear()
        self._reset_summary()
    
    def _reset_summary(self):
        self.summary_labels['process'].setText('进程: 0')
        self.summary_labels['service'].setText('服务: 0')
        self.summary_labels['task'].setText('计划任务: 0')
        self.summary_labels['registry'].setText('注册表项: 0')
    
    def _export_report(self):
        content = self.log_output.toPlainText()
        if not content.strip():
            QMessageBox.warning(self, '提示', '日志为空，无需导出')
            return
        
        file_name = f'process_scan_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        file_path = os.path.join(os.getcwd(), file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, '导出成功', f'报告已保存到:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', str(e))
    
    def _start_scan(self):
        input_type, input_value = self._get_input()
        full_registry_scan = self.chk_full_registry.isChecked()
        
        if not input_value:
            QMessageBox.warning(self, '提示', '请填写PID/进程名/进程路径任意一项')
            return
        
        self._lock_inputs(True)
        self.btn_scan.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_running.setText('状态: 扫描中')
        self.scan_start_time = time.time()
        
        scan_mode = '全量扫描' if full_registry_scan else '快速扫描'
        self._log_message(f'开始扫描 [{scan_mode}]，输入类型: {input_type}，值: {input_value}', 'info')
        
        self.scan_thread = ScanThread(input_type, input_value, full_registry_scan)
        self.scan_thread.progress.connect(self._update_progress)
        self.scan_thread.finished.connect(self._on_scan_finished)
        self.scan_thread.start()
    
    def _get_input(self):
        pid_text = self.pid_input.text().strip()
        name_text = self.name_input.text().strip()
        path_text = self.path_input.text().strip()
        
        if pid_text:
            return ('pid', pid_text)
        elif name_text:
            return ('name', name_text)
        elif path_text:
            return ('path', path_text)
        return (None, None)
    
    def _update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def _on_scan_finished(self, result):
        elapsed = time.time() - self.scan_start_time
        self.status_time.setText(f'耗时: {elapsed:.2f}s')
        self.status_running.setText('状态: 空闲')
        
        self._lock_inputs(False)
        self.btn_scan.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result['error']:
            self._log_message(f'扫描出错: {result["error"]}', 'error')
            return
        
        self._display_results(result)
    
    def _display_results(self, result):
        processes = result['processes']
        services = result['services']
        tasks = result['tasks']
        registry = result['registry']
        
        if not processes:
            self._log_message('未找到匹配的进程', 'warning')
            return
        
        self._log_message('═══════════════════════════════════════', 'info')
        self._log_message('进程信息', 'success')
        self._log_message('═══════════════════════════════════════', 'info')
        for proc in processes:
            self._log_message(f'PID: {proc["pid"]}', 'info')
            self._log_message(f'进程名: {proc["name"]}', 'info')
            self._log_message(f'路径: {proc["exe"]}', 'info')
            self._log_message(f'命令行: {proc["cmdline"]}', 'info')
            self._log_message(f'父进程: {proc["ppid"]} ({proc.get("parent_name", "Unknown")})', 'info')
            self._log_message(f'状态: {proc["status"]}', 'info')
            self._log_message(f'用户: {proc["username"]}', 'info')
            self._log_message(f'CPU: {proc["cpu_percent"]}% | 内存: {proc["memory_info"] / 1024 / 1024:.2f} MB', 'info')
            self._log_message('───────────────────────────────────────', 'info')
        
        if services:
            self._log_message('═══════════════════════════════════════', 'info')
            self._log_message(f'关联服务 ({len(services)})', 'warning')
            self._log_message('═══════════════════════════════════════', 'info')
            for service in services:
                self._log_message(f'服务名: {service["name"]}', 'warning')
                self._log_message(f'显示名: {service.get("display_name", "")}', 'warning')
                self._log_message(f'状态: {service.get("state", "")}', 'warning')
                self._log_message(f'路径: {service.get("config", {}).get("binary_path", "")}', 'warning')
                self._log_message(f'启动类型: {service.get("config", {}).get("start_type", "")}', 'warning')
                self._log_message('───────────────────────────────────────', 'info')
        
        self._log_message('═══════════════════════════════════════', 'info')
        self._log_message(f'所有计划任务扫描 ({len(tasks)})', 'warning')
        self._log_message('═══════════════════════════════════════', 'info')
        for task in tasks:
            self._log_message(f'任务名: {task["name"]}', 'warning')
            self._log_message(f'状态: {task.get("state", "")}', 'warning')
            self._log_message(f'命令: {task.get("command", "")}', 'warning')
            self._log_message(f'计划: {task.get("schedule", "")}', 'warning')
            self._log_message(f'下次运行: {task.get("next_run", "")}', 'warning')
            self._log_message('───────────────────────────────────────', 'info')
        
        self._log_message('═══════════════════════════════════════', 'info')
        self._log_message(f'注册表关联项 ({len(registry)})', 'warning')
        self._log_message('═══════════════════════════════════════', 'info')
        if registry:
            for entry in registry:
                self._log_message(f'位置: {entry["hive"]}\\{entry["path"]}', 'warning')
                self._log_message(f'键名: {entry["name"]}', 'warning')
                self._log_message(f'值: {entry["value"]}', 'warning')
                self._log_message('───────────────────────────────────────', 'info')
        else:
            self._log_message('未找到关联的注册表项', 'info')
        
        self._log_message(f'扫描完成，共发现 {len(processes)} 个进程', 'success')
        
        self.found_processes = processes
        self.found_registry = registry
        self.found_tasks = tasks
        
        self._update_summary({
            'processes': processes,
            'services': [],
            'tasks': tasks,
            'registry': registry
        })
    
    def _confirm_delete(self):
        if not hasattr(self, 'found_processes') or not self.found_processes:
            QMessageBox.warning(self, '提示', '请先执行检测溯源')
            return
        
        delete_dialog = QMessageBox(self)
        delete_dialog.setIcon(QMessageBox.Icon.Warning)
        delete_dialog.setWindowTitle('⚠️ 危险操作确认')
        
        process_list = '\n'.join([f'• PID {p["pid"]} - {p["name"]}' for p in self.found_processes])
        
        msg = f'<h3 style="color:#c0392b;">即将执行以下清理操作</h3>'
        msg += f'<p style="color:#374151;">目标进程:</p>'
        msg += f'<p style="font-family:monospace; color:#1f2937;">{process_list}</p>'
        msg += '<p style="color:#f59e0b;">⚠️ 请谨慎操作，错误删除可能导致系统异常！</p>'
        
        delete_dialog.setTextFormat(Qt.TextFormat.RichText)
        delete_dialog.setText(msg)
        
        self.chk_terminate = QCheckBox('🔴 终止进程')
        self.chk_terminate.setChecked(True)
        self.chk_delete_file = QCheckBox('🗑️ 删除程序文件')
        self.chk_delete_file.setChecked(False)
        self.chk_delete_registry = QCheckBox('📝 删除注册表项')
        self.chk_delete_registry.setChecked(False)
        self.chk_delete_tasks = QCheckBox('⏰ 删除计划任务')
        self.chk_delete_tasks.setChecked(False)
        
        layout = delete_dialog.layout()
        layout.addWidget(self.chk_terminate, layout.rowCount(), 0, 1, layout.columnCount())
        layout.addWidget(self.chk_delete_file, layout.rowCount(), 0, 1, layout.columnCount())
        layout.addWidget(self.chk_delete_registry, layout.rowCount(), 0, 1, layout.columnCount())
        layout.addWidget(self.chk_delete_tasks, layout.rowCount(), 0, 1, layout.columnCount())
        
        delete_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        delete_dialog.setDefaultButton(QMessageBox.StandardButton.No)
        
        result = delete_dialog.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            options = {
                'terminate': self.chk_terminate.isChecked(),
                'delete_file': self.chk_delete_file.isChecked(),
                'delete_registry': self.chk_delete_registry.isChecked(),
                'delete_tasks': self.chk_delete_tasks.isChecked()
            }
            self._start_cleanup(options)
    
    def _start_cleanup(self, options):
        self._lock_inputs(True)
        self.btn_scan.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.status_running.setText('状态: 清理中')
        
        actions = []
        if options['delete_registry']:
            actions.append('删除注册表')
        if options['delete_tasks']:
            actions.append('删除计划任务')
        if options['terminate']:
            actions.append('终止进程')
        if options['delete_file']:
            actions.append('删除文件')
        
        self._log_message('═' * 50, 'warning')
        self._log_message('⚠️ 开始执行清理操作', 'warning')
        self._log_message(f'清理顺序: {" → ".join(actions)}', 'warning')
        self._log_message('═' * 50, 'warning')
        
        self.cleanup_thread = CleanupThread(
            self.found_processes, 
            options,
            self.found_registry,
            self.found_tasks
        )
        self.cleanup_thread.finished.connect(self._on_cleanup_finished)
        self.cleanup_thread.start()
    
    def _on_cleanup_finished(self, results):
        self.status_running.setText('状态: 空闲')
        self._lock_inputs(False)
        self.btn_scan.setEnabled(True)
        self.btn_delete.setEnabled(True)
        
        success_count = 0
        fail_count = 0
        info_count = 0
        
        for result in results:
            if result.get('success', False):
                message = result.get('message', '操作成功')
                if 'pid' in result:
                    self._log_message(f'✅ 成功终止进程: PID {result["pid"]} ({result.get("name", "")})', 'success')
                elif 'path' in result:
                    self._log_message(f'✅ 成功删除文件: {result["path"]}', 'success')
                elif 'hive' in result:
                    self._log_message(f'✅ 成功删除注册表: {result.get("message", "")}', 'success')
                elif 'task_name' in result:
                    self._log_message(f'✅ 成功删除计划任务: {result.get("message", "")}', 'success')
                success_count += 1
            else:
                message = result.get('message', '操作失败')
                is_info = False
                
                if 'pid' in result:
                    if '进程不存在' in message:
                        self._log_message(f'⚠️ PID {result["pid"]}: {message}', 'info')
                        is_info = True
                    else:
                        self._log_message(f'❌ 终止失败 PID {result["pid"]}: {message}', 'error')
                elif 'path' in result:
                    if '文件不存在' in message:
                        self._log_message(f'⚠️ 文件操作: {message}', 'info')
                        is_info = True
                    else:
                        self._log_message(f'❌ 删除文件失败: {message}', 'error')
                elif 'hive' in result:
                    if '不存在' in message:
                        self._log_message(f'⚠️ 注册表操作: {message}', 'info')
                        is_info = True
                    else:
                        self._log_message(f'❌ 删除注册表失败: {message}', 'error')
                elif 'task_name' in result:
                    if '不存在' in message:
                        self._log_message(f'⚠️ 计划任务操作: {message}', 'info')
                        is_info = True
                    else:
                        self._log_message(f'❌ 删除计划任务失败: {message}', 'error')
                
                if is_info:
                    info_count += 1
                else:
                    fail_count += 1
        
        self._log_message('═' * 50, 'info')
        self._log_message(f'✅ 清理完成: 成功 {success_count}，失败 {fail_count}', 'success')
        self._log_message('═' * 50, 'info')
    
    def _lock_inputs(self, locked):
        self.pid_input.setEnabled(not locked)
        self.name_input.setEnabled(not locked)
        self.path_input.setEnabled(not locked)
        self.path_browse.setEnabled(not locked)

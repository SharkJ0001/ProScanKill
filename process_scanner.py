import psutil
import os
import re

class ProcessScanner:
    def __init__(self):
        pass
    
    def get_process_by_pid(self, pid):
        try:
            process = psutil.Process(pid)
            return self._get_process_info(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def get_processes_by_name(self, name):
        results = []
        if not name.endswith('.exe'):
            name = name + '.exe'
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'ppid', 'create_time']):
            try:
                if proc.info['name'] and name.lower() in proc.info['name'].lower():
                    results.append(self._get_process_info(proc))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
    
    def get_processes_by_path(self, path):
        results = []
        path = os.path.normpath(path).lower()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'ppid', 'create_time']):
            try:
                exe_path = proc.info['exe']
                if exe_path:
                    exe_path_norm = os.path.normpath(exe_path).lower()
                    if exe_path_norm == path or path in exe_path_norm:
                        results.append(self._get_process_info(proc))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
    
    def _get_process_info(self, process):
        try:
            info = {
                'pid': process.pid,
                'name': process.name(),
                'exe': process.exe(),
                'cmdline': ' '.join(process.cmdline()) if process.cmdline() else '',
                'ppid': process.ppid(),
                'status': process.status(),
                'create_time': process.create_time(),
                'username': process.username(),
                'cpu_percent': process.cpu_percent(),
                'memory_info': process.memory_info().rss,
                'memory_percent': process.memory_percent()
            }
            
            if info['ppid'] != 0:
                try:
                    parent_proc = psutil.Process(info['ppid'])
                    info['parent_name'] = parent_proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    info['parent_name'] = 'Unknown'
            else:
                info['parent_name'] = 'System'
            
            return info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def terminate_process(self, pid):
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=3)
            except psutil.TimeoutExpired:
                process.kill()
            return {'success': True, 'pid': pid, 'name': process.name(), 'message': '进程已成功终止'}
        except psutil.NoSuchProcess:
            return {'success': False, 'pid': pid, 'name': 'Unknown', 'message': '进程不存在'}
        except psutil.AccessDenied:
            return {'success': False, 'pid': pid, 'name': 'Unknown', 'message': '权限不足，无法终止进程'}
        except Exception as e:
            return {'success': False, 'pid': pid, 'name': 'Unknown', 'message': str(e)}
    
    def terminate_processes(self, pids):
        results = []
        for pid in pids:
            result = self.terminate_process(pid)
            results.append(result)
        return results
    
    def delete_file(self, file_path):
        if not os.path.exists(file_path):
            return {'success': False, 'path': file_path, 'message': '文件不存在'}
        
        for attempt in range(3):
            try:
                os.remove(file_path)
                return {'success': True, 'path': file_path, 'message': '文件已成功删除'}
            except PermissionError:
                pass
            except Exception:
                pass
            
            try:
                import win32api
                import win32con
                win32api.SetFileAttributes(file_path, win32con.FILE_ATTRIBUTE_NORMAL)
                os.remove(file_path)
                return {'success': True, 'path': file_path, 'message': '文件已成功删除'}
            except Exception:
                pass
            
            try:
                result = subprocess.run(
                    ['cmd', '/c', 'del', '/f', '/q', file_path],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 and not os.path.exists(file_path):
                    return {'success': True, 'path': file_path, 'message': '文件已成功删除'}
            except Exception:
                pass
            
            try:
                result = subprocess.run(
                    ['powershell', '-Command', f'Remove-Item -Path "{file_path}" -Force -ErrorAction SilentlyContinue'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 and not os.path.exists(file_path):
                    return {'success': True, 'path': file_path, 'message': '文件已成功删除'}
            except Exception:
                pass
            
            import time
            time.sleep(0.5)
        
        try:
            import ctypes
            MOVEFILE_DELAY_UNTIL_REBOOT = 0x4
            result = ctypes.windll.kernel32.MoveFileExW(file_path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
            if result:
                return {'success': True, 'path': file_path, 'message': '文件将在系统重启后删除'}
        except Exception:
            pass
        
        return {'success': False, 'path': file_path, 'message': '权限不足，无法删除文件'}
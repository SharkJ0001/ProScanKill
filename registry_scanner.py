import winreg
import os

class RegistryScanner:
    def __init__(self):
        self.run_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Run'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\RunOnce'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\RunServices'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\RunServicesOnce'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\RunOnce'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Run'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\RunOnce'),
        ]
        
        self.service_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services'),
        ]
        
        self.extended_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Internet Explorer\Extensions'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Classes\exefile\shell\open\command'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Classes\comfile\shell\open\command'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Classes\batfile\shell\open\command'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Classes\cmdfile\shell\open\command'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Winlogon'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Winlogon\Notify'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\SharedDlls'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Internet Explorer\Extensions'),
            (winreg.HKEY_CURRENT_USER, r'Software\Classes\exefile\shell\open\command'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Wow6432Node\Microsoft\Internet Explorer\Extensions'),
            (winreg.HKEY_CURRENT_USER, r'Volatile Environment'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Command Processor\AutoRun'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Command Processor\AutoRun'),
        ]
    
    def scan_run_keys(self):
        results = []
        for hkey, path in self.run_keys:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            results.append({
                                'hive': self._hive_to_string(hkey),
                                'path': path,
                                'name': name,
                                'value': value,
                                'type': 'run_key'
                            })
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue
            except PermissionError:
                continue
        return results
    
    def scan_service_keys(self):
        results = []
        for hkey, path in self.service_keys:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    i = 0
                    while True:
                        try:
                            service_name = winreg.EnumKey(key, i)
                            service_path = os.path.join(path, service_name)
                            try:
                                with winreg.OpenKey(hkey, service_path) as service_key:
                                    j = 0
                                    while True:
                                        try:
                                            value_name, value_data, _ = winreg.EnumValue(service_key, j)
                                            if value_data and (isinstance(value_data, str) and len(value_data) > 0):
                                                results.append({
                                                    'hive': self._hive_to_string(hkey),
                                                    'path': service_path,
                                                    'name': value_name,
                                                    'value': value_data,
                                                    'type': 'service'
                                                })
                                            j += 1
                                        except OSError:
                                            break
                            except PermissionError:
                                pass
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue
            except PermissionError:
                continue
        return results
    
    def scan_extended_keys(self):
        results = []
        for hkey, path in self.extended_keys:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if value and (isinstance(value, str) and len(value) > 0):
                                results.append({
                                    'hive': self._hive_to_string(hkey),
                                    'path': path,
                                    'name': name,
                                    'value': value,
                                    'type': 'extended'
                                })
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue
            except PermissionError:
                continue
        return results
    
    def _recursive_scan(self, hkey, current_path, max_depth=5, current_depth=0, callback=None):
        results = []
        
        if current_depth > max_depth:
            return results
            
        try:
            with winreg.OpenKey(hkey, current_path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        if value and isinstance(value, str) and len(value) > 4:
                            entry = {
                                'hive': self._hive_to_string(hkey),
                                'path': current_path,
                                'name': name,
                                'value': value,
                                'type': 'full_scan'
                            }
                            if callback:
                                callback(entry)
                            results.append(entry)
                        i += 1
                    except OSError:
                        break
                
                j = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, j)
                        subkey_path = os.path.join(current_path, subkey_name)
                        
                        if subkey_name.startswith('{') and subkey_name.endswith('}'):
                            j += 1
                            continue
                            
                        if subkey_name.lower() in ['security', 'policy', 'sam', 'systemprofile']:
                            j += 1
                            continue
                            
                        results.extend(self._recursive_scan(hkey, subkey_path, max_depth, current_depth + 1, callback))
                        j += 1
                    except OSError:
                        break
                    except PermissionError:
                        j += 1
                        continue
        except PermissionError:
            pass
        except FileNotFoundError:
            pass
        
        return results
    
    def scan_entire_registry(self, callback=None):
        results = []
        
        results.extend(self._recursive_scan(
            winreg.HKEY_CURRENT_USER, '', max_depth=5, callback=callback
        ))
        
        scan_paths = [
            r'Software',
            r'SYSTEM\CurrentControlSet\Services',
            r'Software\Wow6432Node',
        ]
        
        for path in scan_paths:
            results.extend(self._recursive_scan(
                winreg.HKEY_LOCAL_MACHINE, path, max_depth=5, callback=callback
            ))
        
        try:
            with winreg.OpenKey(winreg.HKEY_USERS, '') as hku_key:
                i = 0
                while True:
                    try:
                        sid = winreg.EnumKey(hku_key, i)
                        if sid.startswith('S-1-5'):
                            user_path = sid
                            results.extend(self._recursive_scan(
                                winreg.HKEY_USERS, user_path, max_depth=4, callback=callback
                            ))
                        i += 1
                    except OSError:
                        break
                    except PermissionError:
                        i += 1
                        continue
        except PermissionError:
            pass
        
        return results
    
    def _hive_to_string(self, hive):
        hive_map = {
            winreg.HKEY_LOCAL_MACHINE: 'HKEY_LOCAL_MACHINE',
            winreg.HKEY_CURRENT_USER: 'HKEY_CURRENT_USER',
            winreg.HKEY_CLASSES_ROOT: 'HKEY_CLASSES_ROOT',
            winreg.HKEY_CURRENT_CONFIG: 'HKEY_CURRENT_CONFIG',
            winreg.HKEY_USERS: 'HKEY_USERS',
        }
        return hive_map.get(hive, str(hive))
    
    def _string_to_hive(self, hive_str):
        hive_map = {
            'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
            'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
            'HKEY_CLASSES_ROOT': winreg.HKEY_CLASSES_ROOT,
            'HKEY_CURRENT_CONFIG': winreg.HKEY_CURRENT_CONFIG,
            'HKEY_USERS': winreg.HKEY_USERS,
        }
        return hive_map.get(hive_str, None)
    
    def delete_registry_entry(self, hive_str, path, name):
        hive = self._string_to_hive(hive_str)
        if hive is None:
            return {'success': False, 'message': f'无效的注册表根键: {hive_str}'}
        
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.DeleteValue(key, name)
            return {'success': True, 'message': f'已删除注册表项: {hive_str}\\{path}\\{name}'}
        except FileNotFoundError:
            return {'success': False, 'message': '注册表项不存在'}
        except PermissionError:
            return {'success': False, 'message': '权限不足，无法删除注册表项'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def find_matching_entries(self, target_info, full_scan=False):
        all_entries = []
        all_entries.extend(self.scan_run_keys())
        all_entries.extend(self.scan_service_keys())
        
        if full_scan:
            all_entries.extend(self.scan_extended_keys())
            all_entries.extend(self.scan_entire_registry())
        
        matches = []
        target_name = target_info.get('name', '').lower()
        target_path = target_info.get('exe', '').lower()
        
        seen_entries = set()
        
        for entry in all_entries:
            entry_value = entry.get('value', '').lower()
            
            if not entry_value or len(entry_value) < 8:
                continue
            
            entry_key = f"{entry.get('hive', '')}_{entry.get('path', '')}_{entry.get('name', '')}"
            if entry_key in seen_entries:
                continue
            seen_entries.add(entry_key)
            
            matched = False
            
            if target_path and target_path in entry_value:
                matches.append(entry)
                continue
            
            if target_name and '.exe' in target_name:
                process_name = target_name
                process_name_no_ext = target_name.replace('.exe', '')
                
                if process_name in entry_value:
                    matches.append(entry)
                    continue
                
                if process_name_no_ext in entry_value and '.exe' in entry_value:
                    value_parts = entry_value.split()
                    for part in value_parts:
                        if part.endswith('.exe') and process_name_no_ext in part:
                            matches.append(entry)
                            break
        
        return matches
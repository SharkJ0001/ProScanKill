import subprocess
import re
import os
import winreg

class ServiceScanner:
    def __init__(self):
        pass
    
    def get_all_services(self):
        services = []
        try:
            result = subprocess.run(
                ['sc', 'query', 'type=', 'service', 'state=', 'all'],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            service_blocks = re.split(r'\n\n', output)
            
            for block in service_blocks:
                if 'SERVICE_NAME:' in block:
                    service_info = self._parse_service_block(block)
                    if service_info:
                        services.append(service_info)
        except Exception as e:
            pass
        return services
    
    def _parse_service_block(self, block):
        info = {}
        lines = block.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('SERVICE_NAME:'):
                info['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('DISPLAY_NAME:'):
                info['display_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('TYPE:'):
                info['type'] = line.split(':', 1)[1].strip()
            elif line.startswith('STATE:'):
                info['state'] = line.split(':', 1)[1].strip()
            elif line.startswith('WIN32_EXECUTABLE_PATH:'):
                info['path'] = line.split(':', 1)[1].strip()
        
        if 'name' in info:
            info['config'] = self._get_service_config(info['name'])
        return info
    
    def _get_service_config(self, service_name):
        config = {}
        
        try:
            key_path = fr'SYSTEM\CurrentControlSet\Services\{service_name}'
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                try:
                    image_path, _ = winreg.QueryValueEx(key, 'ImagePath')
                    config['binary_path'] = image_path.strip('"')
                except FileNotFoundError:
                    pass
        except Exception:
            pass
        
        if not config.get('binary_path'):
            try:
                result = subprocess.run(
                    ['sc', 'qc', service_name],
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                output = result.stdout
                lines = output.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('BINARY_PATH_NAME:'):
                        path = line.split(':', 1)[1].strip()
                        path = path.strip('"')
                        config['binary_path'] = path
                        break
            except Exception:
                pass
        
        return config
    
    def find_matching_services(self, target_info):
        all_services = self.get_all_services()
        matches = []
        
        target_name = target_info.get('name', '').lower()
        target_path = target_info.get('exe', '').lower()
        
        for service in all_services:
            service_path = service.get('config', {}).get('binary_path', '')
            
            if service_path:
                service_path_clean = service_path.lower()
                service_path_clean = service_path_clean.strip('"')
                
                if ' ' in service_path_clean and '.exe' in service_path_clean:
                    parts = service_path_clean.split(' ')
                    for part in parts:
                        if part.endswith('.exe'):
                            service_path_clean = part
                            break
            
            matched = False
            
            if target_path and service_path_clean:
                target_exe = os.path.basename(target_path)
                service_exe = os.path.basename(service_path_clean)
                
                if target_exe == service_exe:
                    matches.append(service)
                    continue
                
                if target_path in service_path_clean or service_path_clean in target_path:
                    matches.append(service)
                    continue
            
            if target_name:
                service_name = service.get('name', '').lower()
                display_name = service.get('display_name', '').lower()
                
                if target_name in service_name or target_name in display_name:
                    matches.append(service)
                    continue
                
                target_base = os.path.splitext(target_name)[0]
                service_base = os.path.splitext(service_name)[0]
                display_base = os.path.splitext(display_name)[0]
                
                if target_base in service_base or target_base in display_base:
                    matches.append(service)
                    continue
        
        return matches
    
    def delete_service(self, service_name):
        try:
            result_stop = subprocess.run(
                ['sc', 'stop', service_name],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            result_delete = subprocess.run(
                ['sc', 'delete', service_name],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result_delete.returncode == 0:
                return {'success': True, 'message': f'已删除服务: {service_name}'}
            else:
                return {'success': False, 'message': f'删除服务失败: {result_delete.stderr or result_delete.stdout}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

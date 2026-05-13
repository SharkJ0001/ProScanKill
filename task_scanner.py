import subprocess
import os

class TaskScanner:
    def __init__(self):
        pass
    
    def get_all_tasks(self):
        tasks = []
        try:
            result = subprocess.run(
                ['schtasks', '/query', '/fo', 'CSV', '/v'],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            lines = output.split('\n')
            
            if len(lines) >= 2:
                headers = self._parse_csv_line(lines[0])
                for line in lines[1:]:
                    line = line.strip()
                    if line and not line.startswith('"主机名"'):
                        values = self._parse_csv_line(line)
                        if len(values) >= len(headers):
                            task_info = {}
                            for i, header in enumerate(headers):
                                if i < len(values):
                                    task_info[header.strip()] = values[i].strip()
                            if task_info.get('TaskName') or task_info.get('任务名'):
                                tasks.append(self._normalize_task(task_info))
        
        except Exception as e:
            pass
        
        return tasks
    
    def _parse_csv_line(self, line):
        values = []
        current = ''
        in_quotes = False
        
        for char in line:
            if char == '"' and not in_quotes:
                in_quotes = True
            elif char == '"' and in_quotes:
                in_quotes = False
            elif char == ',' and not in_quotes:
                values.append(current)
                current = ''
            else:
                current += char
        
        values.append(current)
        return values
    
    def _normalize_task(self, task_info):
        normalized = {}
        normalized['name'] = task_info.get('TaskName', task_info.get('任务名', '')).replace('\\', '/')
        normalized['next_run'] = task_info.get('Next Run Time', task_info.get('下次运行时间', ''))
        normalized['status'] = task_info.get('Status', task_info.get('状态', ''))
        normalized['logon_mode'] = task_info.get('Logon Mode', task_info.get('登录状态', ''))
        normalized['last_run'] = task_info.get('Last Run Time', task_info.get('上次运行时间', ''))
        normalized['last_result'] = task_info.get('Last Result', task_info.get('上次结果', ''))
        normalized['author'] = task_info.get('Author', task_info.get('创建者', ''))
        normalized['command'] = task_info.get('Task To Run', task_info.get('要运行的任务', ''))
        normalized['start_in'] = task_info.get('Start In', task_info.get('起始于', ''))
        normalized['schedule'] = task_info.get('Schedule', task_info.get('计划', ''))
        normalized['state'] = task_info.get('Scheduled Task State', task_info.get('计划任务状态', ''))
        
        return normalized
    
    def find_matching_tasks(self, target_info):
        all_tasks = self.get_all_tasks()
        matches = []
        seen_task_names = set()
        
        target_name = target_info.get('name', '').lower()
        target_path = target_info.get('exe', '').lower()
        
        for task in all_tasks:
            task_command = task.get('command', '').lower()
            task_name = task.get('name', '').lower()
            task_name_original = task.get('name', '')
            
            if task_name_original in seen_task_names:
                continue
            
            matched = False
            
            if target_path and task_command:
                if target_path in task_command or task_command in target_path:
                    matches.append(task)
                    seen_task_names.add(task_name_original)
                    matched = True
            
            if not matched and target_name and task_command:
                if target_name in task_command:
                    matches.append(task)
                    seen_task_names.add(task_name_original)
                    matched = True
            
            if not matched and target_name and task_name:
                if target_name in task_name:
                    matches.append(task)
                    seen_task_names.add(task_name_original)
        
        return matches
    
    def delete_task(self, task_name, monitor_mode=False, monitor_seconds=5):
        task_name_normalized = task_name.replace('/', '\\')
        
        try:
            result = subprocess.run(
                ['schtasks', '/delete', '/tn', task_name_normalized, '/f'],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                if monitor_mode:
                    import time
                    start_time = time.time()
                    deleted_count = 1
                    
                    while time.time() - start_time < monitor_seconds:
                        all_tasks = self.get_all_tasks()
                        found = False
                        for task in all_tasks:
                            if task.get('name', '').lower() == task_name.lower():
                                result = subprocess.run(
                                    ['schtasks', '/delete', '/tn', task_name_normalized, '/f'],
                                    capture_output=True,
                                    text=True,
                                    encoding='gbk',
                                    errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                if result.returncode == 0:
                                    deleted_count += 1
                                found = True
                                break
                        
                        if found:
                            time.sleep(0.5)
                        else:
                            time.sleep(0.2)
                    
                    return {'success': True, 'task_name': task_name, 'message': f'已成功删除计划任务 {deleted_count} 次: {task_name}'}
                else:
                    return {'success': True, 'task_name': task_name, 'message': f'已成功删除计划任务: {task_name}'}
            else:
                error_msg = result.stderr.strip() if result.stderr else f'命令执行失败，退出码: {result.returncode}'
                return {'success': False, 'task_name': task_name, 'message': error_msg}
        except Exception as e:
            return {'success': False, 'task_name': task_name, 'message': str(e)}
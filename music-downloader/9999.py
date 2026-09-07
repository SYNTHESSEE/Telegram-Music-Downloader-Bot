import os

def analyze_project_structure(root_path, output_filename):
    with open(output_filename, 'w', encoding='utf-8') as report:
        # Step 1: Write the Project Tree
        report.write("=== ПОЛНОЕ ДРЕВО ПРОЕКТА ===\n")
        for root, dirs, files in os.walk(root_path, topdown=True):
            # Исключаем скрытые папки (начинающиеся с '.')
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            level = root.replace(root_path, '').count(os.sep)
            indent = ' ' * 4 * level
            report.write(f"{indent}{os.path.basename(root)}/\n")
            
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                # Исключаем .json и скрытые файлы из дерева
                if not f.endswith('.json') and not f.startswith('.'):
                    report.write(f"{sub_indent}{f}\n")
        
        report.write("\n" + "="*40 + "\n")
        report.write("=== ИЗВЛЕЧЕННЫЙ КОД ===\n\n")

        # Step 2: Extract file contents
        for root, dirs, files in os.walk(root_path, topdown=True):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            current_folder = os.path.basename(root) or root_path
            
            for f in files:
                # Пропускаем .json и скрытые файлы
                if f.endswith('.json') or f.startswith('.'):
                    continue
                
                file_full_path = os.path.join(root, f)
                report.write(f"ПАПКА: {current_folder} | ФАЙЛ: {f}\n")
                report.write("-" * 30 + "\n")
                
                try:
                    with open(file_full_path, 'r', encoding='utf-8') as source_file:
                        report.write(source_file.read())
                except Exception as error:
                    report.write(f"[Ошибка при чтении файла: {error}]\n")
                
                report.write("\n\n" + "*"*40 + "\n\n")

# Используем текущую директорию для анализа проекта CORTEX
analyze_project_structure('.', 'project_analysis.txt')

import os
import re
import sys
import subprocess

def get_current_directory():
    """Gets the directory path where the script itself is located."""
    return os.path.dirname(os.path.abspath(__file__))

def extract_imports_from_file(file_path):
    """Finds all imported modules within a single .py file."""
    imports = set()
    import_re = re.compile(r'^\s*import\s+([a-zA-Z0-9_]+)')
    from_re = re.compile(r'^\s*from\s+([a-zA-Z0-9_]+)')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match_import = import_re.match(line)
                match_from = from_re.match(line)
                if match_import:
                    imports.add(match_import.group(1))
                elif match_from:
                    imports.add(match_from.group(1))
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return imports

def get_local_modules(directory):
    """Finds names of all local .py files and root folders in the current directory."""
    local_modules = set()
    try:
        for item in os.listdir(directory):
            if item.endswith('.py') and item != os.path.basename(__file__):
                local_modules.add(item[:-3])
            elif os.path.isdir(os.path.join(directory, item)) and not item.startswith('.'):
                local_modules.add(item)
    except Exception as e:
        print(f"Error scanning local directory items: {e}")
    return local_modules

def scan_directory(directory):
    """Scans the directory recursively for .py files and extracts imports."""
    all_imports = set()
    script_name = os.path.basename(__file__)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != script_name:
                file_path = os.path.join(root, file)
                all_imports.update(extract_imports_from_file(file_path))
    return all_imports

def filter_stdlib_and_local(modules, directory):
    """Filters out Python standard libraries and local files, leaving only external packages."""
    stdlib = sys.builtin_module_names
    
    # Extended list of common Python standard library modules
    common_stdlib = {
        'os', 'sys', 're', 'math', 'datetime', 'json', 'urllib', 'subprocess', 
        'shutil', 'glob', 'time', 'collections', 'itertools', 'functools', 
        'pathlib', 'logging', 'threading', 'multiprocessing', 'argparse', 'csv',
        'dataclasses', 'typing', 'asyncio', 'hashlib', 'warnings', 'abc', 'copy',
        'ast', 'inspect', 'traceback'
    }
    
    local_modules = get_local_modules(directory)
    print(f"Detected local project modules/folders: {', '.join(local_modules) if local_modules else 'None'}")
    
    external_modules = {
        mod for mod in modules 
        if mod not in stdlib and mod not in common_stdlib and mod not in local_modules
    }
    return external_modules

def generate_requirements_file(packages, directory, aliases):
    """Creates a requirements.txt file based on the analyzed modules."""
    requirements_path = os.path.join(directory, 'requirements.txt')
    
    try:
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write("# Auto-generated package list for environment restoration\n")
            for package in sorted(packages):
                pip_name = aliases.get(package, package)
                f.write(f"{pip_name}\n")
        print(f"[SUCCESS] Generated dependency manifest: {requirements_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save requirements.txt: {e}")

def install_or_update_packages(packages, aliases):
    """Installs or upgrades discovered external packages using pip."""
    if not packages:
        print("No external dependencies found to install.")
        return

    print(f"Found external packages to check: {', '.join(packages)}")
    
    for package in packages:
        pip_name = aliases.get(package, package)
        print(f"\nChecking and updating package: {pip_name} (imported as {package})")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", pip_name])
        except subprocess.CalledProcessError:
            print(f"[ERROR] Could not install or update {pip_name}.")

if __name__ == "__main__":
    print("Starting directory analysis...")
    current_dir = get_current_directory()
    
    # Define mapping dictionary for import names vs pip installer names
    package_aliases = {
        'flask_cors': 'flask-cors',
        'bridge_utils': 'bridge-utils'
    }
    
    # 1. Collect all explicit imports
    detected_modules = scan_directory(current_dir)
    
    # 2. Filter out standard Python utilities and local workspace files
    external_packages = filter_stdlib_and_local(detected_modules, current_dir)
    
    # 3. Create/update the requirements.txt configuration manifest
    if external_packages:
        generate_requirements_file(external_packages, current_dir, package_aliases)
        
        # 4. Run automated download/update phase
        install_or_update_packages(external_packages, package_aliases)
    else:
        print("No external packages detected to document or install.")
        
    print("\nProcess execution completed!")

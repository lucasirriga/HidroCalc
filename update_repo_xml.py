import os
import configparser
import zipfile
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

def generate_repo():
    # 0. Setup Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    releases_dir = os.path.join(current_dir, 'releases')
    
    if not os.path.exists(releases_dir):
        os.makedirs(releases_dir)

    # 1. Read Metadata
    config = configparser.ConfigParser()
    config.read(os.path.join(current_dir, 'metadata.txt'))
    
    try:
        general = config['general']
        name = general['name']
        version = general['version']
        qt_ver = general.get('qgisMinimumVersion', '3.0')
        desc = general.get('description', '')
        author = general.get('author', '')
        email = general.get('email', '')
        about = general.get('about', '')
        tags = general.get('tags', '')
        homepage = general.get('homepage', '')
        tracker = general.get('tracker', '')
        repository = general.get('repository', '')
        icon = general.get('icon', 'icon.png')
        experimental = general.get('experimental', 'False')
        deprecated = general.get('deprecated', 'False')
    except KeyError as e:
        print(f"Erro ao ler metadata.txt: {e}")
        return

    # 2. Create ZIP with correct structure
    # QGIS requires the top-level folder in the zip to match the plugin name
    zip_filename = f"{name}.zip" 
    # We use a static name (HidroCalc.zip) for the XML, or we can use versioned?
    # Using versioned zip allows rollbacks, but requires committing new binary files every time.
    # However, for a personal repo, committing binaries (small plugins) is acceptable.
    # Let's use versioned name to avoid caching issues on download.
    zip_filename = f"{name}_{version}.zip"
    zip_path = os.path.join(releases_dir, zip_filename)
    
    print(f"Gerando pacote: {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(current_dir):
            # Ignorar pastas ocultas e temporarias
            if '.git' in root or '__pycache__' in root or 'releases' in root or 'tests' in root:
                continue
                
            for file in files:
                if file.endswith('.pyc') or file.endswith('.zip') or file == '.gitignore':
                    continue
                if file in ['update_repo_xml.py', 'plugins.xml']:
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, current_dir)
                
                # IMPORTANT: Prepend Folder Name and Force Forward Slashes
                arcname = os.path.join(name, rel_path).replace("\\", "/")
                zipf.write(file_path, arcname)

    # 3. Define URLs
    # Base URL for the raw file access on GitHub
    # User: lucasirriga, Repo: HidroCalc, Branch: main
    base_url = "https://raw.githubusercontent.com/lucasirriga/HidroCalc/main"
    download_url = f"{base_url}/releases/{zip_filename}"
    
    # 4. Build XML
    plugins = ET.Element('plugins')
    plugin = ET.SubElement(plugins, 'pyqgis_plugin', name=name, version=version)
    
    ET.SubElement(plugin, 'description').text = desc
    ET.SubElement(plugin, 'about').text = about
    ET.SubElement(plugin, 'version').text = version
    ET.SubElement(plugin, 'qgis_minimum_version').text = qt_ver
    ET.SubElement(plugin, 'homepage').text = homepage
    ET.SubElement(plugin, 'file_name').text = zip_filename
    ET.SubElement(plugin, 'icon').text = icon
    ET.SubElement(plugin, 'author_name').text = author
    ET.SubElement(plugin, 'download_url').text = download_url
    ET.SubElement(plugin, 'date').text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(plugin, 'timestamp').text = str(int(datetime.now().timestamp()))
    ET.SubElement(plugin, 'experimental').text = experimental
    ET.SubElement(plugin, 'deprecated').text = deprecated
    ET.SubElement(plugin, 'tracker').text = tracker
    ET.SubElement(plugin, 'repository').text = repository
    ET.SubElement(plugin, 'tags').text = tags

    # 5. Save XML
    xmlstr = minidom.parseString(ET.tostring(plugins)).toprettyxml(indent="   ")
    with open("plugins.xml", "w", encoding="utf-8") as f:
        f.write(xmlstr)
        
    print(f"Arquivo 'plugins.xml' gerado com sucesso!")
    print(f"Versão: {version}")
    print(f"Download URL: {download_url}")
    print("\nPRÓXIMOS PASSOS:")
    print(f"1. git add plugins.xml releases/{zip_filename}")
    print(f"2. git commit -m 'Release v{version}'")
    print(f"3. git push origin main")

if __name__ == "__main__":
    generate_repo()

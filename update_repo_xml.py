import os
import configparser
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

def generate_xml():
    # 1. Read Metadata
    config = configparser.ConfigParser()
    config.read('metadata.txt')
    
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

    # 2. Define URLs
    # Base URL for the raw file access on GitHub
    # Assuming user: lucasirriga, repo: HidroCalc
    # XML will be at: https://raw.githubusercontent.com/lucasirriga/HidroCalc/main/plugins.xml
    # Zip will be at: https://github.com/lucasirriga/HidroCalc/archive/refs/tags/v{version}.zip
    
    # NOTE: The user MUST tag the release in git for this link to work!
    # verifying if tag exists is beyond this script scope, but we assume the flow.
    
    download_url = f"https://github.com/lucasirriga/HidroCalc/archive/refs/tags/v{version}.zip"
    
    # 3. Build XML
    plugins = ET.Element('plugins')
    plugin = ET.SubElement(plugins, 'pyqgis_plugin', name=name, version=version)
    
    ET.SubElement(plugin, 'description').text = desc
    ET.SubElement(plugin, 'about').text = about
    ET.SubElement(plugin, 'version').text = version
    ET.SubElement(plugin, 'qgis_minimum_version').text = qt_ver
    ET.SubElement(plugin, 'homepage').text = homepage
    ET.SubElement(plugin, 'file_name').text = f"{name}.zip"
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

    # 4. Save
    xmlstr = minidom.parseString(ET.tostring(plugins)).toprettyxml(indent="   ")
    with open("plugins.xml", "w", encoding="utf-8") as f:
        f.write(xmlstr)
        
    print(f"Arquivo 'plugins.xml' gerado com sucesso!")
    print(f"Versão: {version}")
    print(f"Download URL: {download_url}")
    print("\nAVISO IMPORTANTE:")
    print(f"Para que o download funcione, você DEVE criar uma TAG no git chamada 'v{version}'.")
    print(f"Comando sugerido: git tag v{version} && git push origin v{version}")

if __name__ == "__main__":
    generate_xml()

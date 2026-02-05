import os
import shutil
import zipfile
import configparser
import sys

def get_version():
    """Reads version from metadata.txt"""
    metadata_path = os.path.join(os.path.dirname(__file__), 'metadata.txt')
    config = configparser.ConfigParser()
    config.read(metadata_path)
    return config['general']['version']

def zip_plugin(source_dir, output_zip):
    """Zips the plugin directory."""
    print(f"Compactando {source_dir} para {output_zip}...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude patterns
            if '.git' in root or '__pycache__' in root or 'deploy.py' in root:
                continue
                
            for file in files:
                if file.endswith('.pyc') or file == 'deploy.py' or file.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(root, file)
                # Archive name should be relative to the source_dir, PREPENDED with 'HidroCalc/'
                # QGIS plugins expect the zip to contain the folder.
                rel_path = os.path.relpath(file_path, source_dir)
                arcname = os.path.join('HidroCalc', rel_path)
                zipf.write(file_path, arcname)

def install_plugin(zip_path, plugin_name):
    """Uninstalls old version and installs new one."""
    appdata = os.getenv('APPDATA')
    qgis_plugins_dir = os.path.join(appdata, 'QGIS', 'QGIS3', 'profiles', 'default', 'python', 'plugins')
    
    target_dir = os.path.join(qgis_plugins_dir, plugin_name)
    
    if not os.path.exists(qgis_plugins_dir):
        print(f"ERRO: Diretório de plugins do QGIS não encontrado em: {qgis_plugins_dir}")
        return

    # 1. Uninstall (Delete folder)
    if os.path.exists(target_dir):
        print(f"Removendo versão anterior em {target_dir}...")
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            print(f"ERRO ao remover pasta antiga: {e}")
            print("Certifique-se de que o QGIS está fechado ou não está usando os arquivos.")
            return

    # 2. Install (Unzip)
    print(f"Instalando nova versão em {qgis_plugins_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(qgis_plugins_dir)
        print("Instalação concluída com sucesso!")
    except Exception as e:
        print(f"ERRO ao extrair zip: {e}")

def main():
    # Current dir (HidroCalc)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    plugin_name = "HidroCalc"
    
    try:
        version = get_version()
    except Exception as e:
        print(f"Erro ao ler versão: {e}")
        version = "unknown"
        
    zip_name = f"{plugin_name}_v{version}.zip"
    zip_path = os.path.join(parent_dir, zip_name)
    
    print(f"--- Deploy Automático {plugin_name} v{version} ---")
    
    # 1. Zip
    zip_plugin(current_dir, zip_path)
    
    # 2. Install
    install_plugin(zip_path, plugin_name)
    
    print("\nProcesso finalizado.")
    print(f"Arquivo ZIP salvo em: {zip_path}")
    input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()

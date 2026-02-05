import os
import shutil
import zipfile
import configparser
import sys
from qgis.core import QgsMessageLog, Qgis, QgsApplication
import qgis.utils

class DeployManager:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.parent_dir = os.path.dirname(plugin_dir)
        self.plugin_name = "HidroCalc"

    def get_version(self):
        """Reads version from metadata.txt"""
        metadata_path = os.path.join(self.plugin_dir, 'metadata.txt')
        config = configparser.ConfigParser()
        config.read(metadata_path)
        return config['general']['version']

    def run_deploy(self):
        """Executes the deploy process: Zip -> Copy -> Reload"""
        try:
            version = self.get_version()
            zip_name = f"{self.plugin_name}_v{version}.zip"
            zip_path = os.path.join(self.parent_dir, zip_name)
            
            # 1. Zip
            self._zip_plugin(zip_path)
            QgsMessageLog.logMessage(f"Plugin compactado em: {zip_path}", self.plugin_name, Qgis.Info)
            
            # 2. Copy to QGIS Plugins Dir
            # Only if current dir is NOT the install dir
            qgis_plugins_dir = os.path.join(QgsApplication.qgisSettingsDirPath(), 'python', 'plugins')
            target_dir = os.path.join(qgis_plugins_dir, self.plugin_name)
            
            # Normalize paths to compare
            if os.path.normpath(self.plugin_dir) != os.path.normpath(target_dir):
                self._copy_files(target_dir)
                QgsMessageLog.logMessage(f"Arquivos copiados para: {target_dir}", self.plugin_name, Qgis.Info)
            else:
                QgsMessageLog.logMessage("Diretório atual já é o diretório de instalação. Pulando cópia.", self.plugin_name, Qgis.Info)

            # 3. Reload
            # We use qgis.utils.reloadPlugin
            if self.plugin_name in qgis.utils.plugins:
                qgis.utils.reloadPlugin(self.plugin_name)
                return f"Deploy v{version} realizado com sucesso! Plugin recarregado."
            else:
                return f"Deploy v{version} realizado! Reinicie o QGIS para aplicar."

        except Exception as e:
            import traceback
            return f"Erro no deploy: {str(e)}\n{traceback.format_exc()}"

    def _zip_plugin(self, output_zip):
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.plugin_dir):
                if '.git' in root or '__pycache__' in root or 'deploy.py' in root:
                    continue
                for file in files:
                    if file.endswith('.pyc') or file == 'deploy.py' or file.endswith('.zip'):
                        continue
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.plugin_dir)
                    arcname = os.path.join(self.plugin_name, rel_path)
                    zipf.write(file_path, arcname)

    def _copy_files(self, target_dir):
        """Copies files to target directory, overwriting existing ones."""
        
        def ignore_patterns(path, names):
            ignore = []
            for n in names:
                if n == '__pycache__' or n.endswith('.pyc') or n.endswith('.zip') or n == '.git' or n == '.github' or n == '.vscode':
                    ignore.append(n)
            return ignore

        # Ensure target directory exists
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # On Windows, rmtree often fails due to file locks (QGIS holding handles).
        # We use copytree with dirs_exist_ok=True to overwrite files.
        # This keeps 'zombie' files (deleted in source but present in target), 
        # but prevents crashing the deploy process.
        try:
            # dirs_exist_ok=True requires Python 3.8+ (Standard in QGIS 3)
            shutil.copytree(self.plugin_dir, target_dir, ignore=ignore_patterns, dirs_exist_ok=True)
        except TypeError:
            # Fallback for older Python versions (if any) or if specific implementation issues arise
            # Manual copy allowing overwrite
            from distutils.dir_util import copy_tree
            # copy_tree doesn't support ignore patterns easily, so we prefer copytree workaround if needed.
            # But let's assume Python 3.8+ for modern QGIS.
            raise RuntimeError("QGIS Python version too old for dirs_exist_ok=True. Update QGIS.")
        except PermissionError as e:
            # If a specific file is locked, we can't do much without unlocking it.
            # But usually .py files are not locked by QGIS interpreter after loading, unless opened explicitly.
             raise PermissionError(f"Arquivo em uso ou permissão negada: {e}. Tente fechar outras instâncias.")

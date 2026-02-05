import zipfile
import os
import configparser

def verify_zip():
    # 1. Get Version/Name
    config = configparser.ConfigParser()
    config.read('metadata.txt')
    name = config['general']['name']
    version = config['general']['version']
    
    zip_path = os.path.join('releases', f"{name}_{version}.zip")
    
    if not os.path.exists(zip_path):
        print(f"ERRO: Arquivo {zip_path} não encontrado.")
        return

    print(f"Verificando {zip_path}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            files = z.namelist()
            if not files:
                print("ERRO: Zip vazio.")
                return

            print(f"Total de arquivos: {len(files)}")
            print("Primeiros 5 arquivos:")
            for f in files[:5]:
                print(f" - {f}")
            
            # Check structure
            # All files should start with "HidroCalc/"
            invalid = [f for f in files if not f.startswith(f"{name}/")]
            
            if invalid:
                print("\nERRO CRÍTICO: Arquivos fora da pasta raiz do plugin!")
                for f in invalid[:5]:
                    print(f" - {f}")
                print(f"... e mais {len(invalid)-5} arquivos.")
            else:
                print(f"\nSUCESSO: Todos os arquivos estão dentro da pasta '{name}/'.")
                
    except Exception as e:
        print(f"ERRO ao ler zip: {e}")

if __name__ == "__main__":
    verify_zip()

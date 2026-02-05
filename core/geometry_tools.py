from qgis.core import (
    QgsProcessingFeatureSourceDefinition, QgsProject, QgsVectorLayer, 
    QgsFeature, QgsGeometry, QgsWkbTypes, QgsField, edit
)
from qgis.PyQt.QtCore import QVariant
import processing

class GeometryTools:
    def __init__(self):
        pass

    def clip_lines_and_update(self, line_layer: QgsVectorLayer, poly_layer: QgsVectorLayer) -> str:
        """
        Recorta a camada de linhas pela camada de polígonos usando Interseção,
        atualiza a camada de linhas ORIGINAL substituindo as feições antigas
        pelas novas recortadas, e calcula o comprimento.
        """
        if not line_layer or not poly_layer:
            return "Camadas inválidas."

        # 1. Executar Interseção (Native: Intersection)
        # Input: line_layer, Overlay: poly_layer
        # Output: temporário (memory)
        
        # Parâmetros para processing
        params = {
            'INPUT': line_layer,
            'OVERLAY': poly_layer,
            'INPUT_FIELDS': [], # Manter todos ou especificar? Vazio = todos de INPUT
            'OVERLAY_FIELDS': [], # Manter todos de OVERLAY também? Sim, útil para saber qual poligono cortou.
            'OVERLAY_FIELDS_PREFIX': 'poly_', # Prefixo para evitar conflito
            'OUTPUT': 'memory:'
        }

        try:
            result = processing.run("native:intersection", params)
            output_layer = result['OUTPUT']
        except Exception as e:
            return f"Erro ao executar interseção: {str(e)}"

        if not output_layer or output_layer.featureCount() == 0:
            return "Nenhuma linha encontrada dentro dos polígonos (Interseção vazia)."

        # 2. Preparar Camada Original para Atualização
        
        # Verificar campo 'Comprimento'
        FIELD_LENGTH = "Comprimento" # Nome do campo
        
        # Mapeamento de campos: O output da interseção tem campos de Linha + Polígono.
        # A camada original só tem campos de Linha. 
        # Se quisermos salvar dados do polígono (ex: Setor), precisamos criar os campos na original.
        
        # Vamos tentar identificar campos prefixados 'poly_' e adicioná-los se não existirem?
        # Ou simplificar e manter apenas schema original + Comprimento?
        # O usuário pediu "camada de poligono deve cortar... ficando apenas linhas dentro".
        # Não especificou herança de atributos, mas é bom manter se possível.
        # Vamos focar no essencial: Geometria cortada + Comprimento.
        
        needs_field_length = False
        idx_length = line_layer.fields().indexFromName(FIELD_LENGTH)
        if idx_length == -1:
             needs_field_length = True

        line_layer.startEditing()
        
        if needs_field_length:
            line_layer.dataProvider().addAttributes([QgsField(FIELD_LENGTH, QVariant.Double, len=10, prec=2)])
            line_layer.updateFields()
            idx_length = line_layer.fields().indexFromName(FIELD_LENGTH) # Refresh index

        # 3. Substituição das Feições
        # Estratégia: Deletar TODAS as feições antigas e inserir as NOVAS.
        # CUIDADO: Isso perde feições que NÃO interceptam se o usuário quisesse mantê-las?
        # O pedido foi "ficando na camada de linha APENAS as linhas que estão dentro do poligono".
        # Então sim, removemos tudo que está fora.
        
        all_ids = line_layer.allFeatureIds()
        line_layer.deleteFeatures(all_ids)
        
        # 4. Inserir Novas Feições
        new_features = []
        
        # Campos da camada original
        orig_fields = line_layer.fields().names()
        
        for feat in output_layer.getFeatures():
            new_feat = QgsFeature(line_layer.fields())
            new_feat.setGeometry(feat.geometry())
            
            # Copiar atributos coincidentes
            for field_name in orig_fields:
                # O output da interseção preserva nomes (possivelmente truncados se shapefile, mas aqui é memory)
                # Se o campo existe no output, copiamos.
                # Cuidado com Length -> geometry recalculado.
                
                if field_name == FIELD_LENGTH:
                     continue # Calculamos abaixo
                
                # Tentar pegar valor do feature de interseção
                # O nome pode ter mudado se houve conflito, mas geralmente 'native:intersection' preserva input.
                try:
                    val = feat[field_name]
                    new_feat[field_name] = val
                except KeyError:
                    pass # Campo não existe no output (estranho, mas ok)
            
            # Calcular Comprimento
            length = new_feat.geometry().length()
            new_feat[FIELD_LENGTH] = length
            
            new_features.append(new_feat)
            
        line_layer.dataProvider().addFeatures(new_features)
        
        success = line_layer.commitChanges()
        
        if success:
            return f"Sucesso! Camada atualizada. {len(new_features)} segmentos criados/mantidos."
        else:
            return "Erro ao salvar alterações na camada (Commit falhou)."

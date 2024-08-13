from flask import Flask, request, jsonify, send_file
import json
from collections import defaultdict, Counter

app = Flask(__name__)

# Carregar dados do arquivo JSON
with open('qbank.qbank_prebuilt_testscomtodas.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/institutions', methods=['GET'])
def get_institutions():
    institutions = []
    for test in data:
        institution = {
            'id': test['institutionId'],
            'name': test['institutionName']
        }
        if institution not in institutions:
            institutions.append(institution)
    return jsonify(institutions)


@app.route('/filter_data', methods=['POST'])
def filter_data():
    request_data = request.json
    institution_id = int(request_data['institution'])
    start_year = int(request_data['startYear'])
    end_year = int(request_data['endYear'])

    # Separar arrays de tags e parentTags
    tags_data = []
    parent_tags_data = []

    for test in data:
        if test.get('institutionId') == institution_id and start_year <= test.get('year') <= end_year:
            tags_data.extend(test.get('tags', []))
            parent_tags_data.extend(test.get('parentTags', []))

    # Função auxiliar para extrair o ID da tag
    def extract_oid(tag):
        return tag['_id']['$oid']

    # Criar contadores de tags
    tag_count = Counter()

    # Contar tags primárias e suas frequências
    for tag in tags_data:
        tag_id = extract_oid(tag)
        tag_count[tag_id] += 1
        parent_id = tag.get('parentId', {})
        if isinstance(parent_id, dict):
            parent_id = parent_id.get('$oid')
            if parent_id:
                tag_count[parent_id] += 0  # Garante que o parent_id seja contado mesmo que não apareça na lista de tags

    for tag in parent_tags_data:
        tag_id = extract_oid(tag)
        tag_count[tag_id] += 1
        parent_id = tag.get('parentId', {})
        if isinstance(parent_id, dict):
            parent_id = parent_id.get('$oid')
            if parent_id:
                tag_count[parent_id] += 0  # Garante que o parent_id seja contado mesmo que não apareça na lista de tags

    
    

    # Criar a árvore de tags
    tag_tree = {}
    tag_frequencies = defaultdict(float)

    # Processar o array de tags para criar a árvore inicial
    for tag in tags_data:
        tag_id = extract_oid(tag)
        parent_id = tag.get('parentId', {})
        if isinstance(parent_id, dict):
            parent_id = parent_id.get('$oid')
        tag_tree[tag_id] = {
            '_id': tag_id,
            'name': tag['name'],
            'parentId': parent_id,
            'children': [],
            'absoluteValue': tag_count[tag_id] 
        }

    # Adicionar informações dos parentTags à árvore de tags
    for parent_tag in parent_tags_data:
        tag_id = extract_oid(parent_tag)
        parent_id = parent_tag.get('parentId', {})
        if isinstance(parent_id, dict):
            parent_id = parent_id.get('$oid')
        if tag_id not in tag_tree:
            tag_tree[tag_id] = {
                '_id': tag_id,
                'name': parent_tag['name'],
                'parentId': parent_id,
                'children': [],
                'absoluteValue': tag_count[tag_id] 
            }

    # Construir a lista de operações para adicionar filhos
    operations = []

    for tag_id, tag_info in tag_tree.items():
        parent_id = tag_info['parentId']
        if parent_id:
            operations.append((parent_id, tag_info))

    # Aplicar as operações de adição de filhos
    for parent_id, tag_info in operations:
        if parent_id in tag_tree:
            tag_tree[parent_id]['children'].append(tag_info)

    
    
    

    def calculate_frequencies(node, sibling_count):
        if 'children' in node and node['children']:
            # Calcula o total de contagem dos filhos para a tag atual
            child_count = sum(tag_count[child['_id']] for child in node['children'])
            print(f"Calculando para a tag {node['name']}. Contagem dos filhos: {child_count}, Contagem da tag mãe: {tag_count[node['_id']]}")

            # Se a soma das contagens das tags filhas for menor que a contagem da tag mãe
            if child_count < tag_count[node['_id']]:
                # Calcula a diferença e a frequência para a nova tag "Outras"
                other_tag_count = tag_count[node['_id']] - child_count
                other_tag_frequency = other_tag_count / tag_count[node['_id']] if sibling_count > 0 else 0
                print(f"Tag 'Outras' criada para {node['name']}. Contagem: {other_tag_count}, Frequência: {other_tag_frequency}")

                # Cria a nova tag "Outras"
                other_tag = {
                    '_id': 'other_' + node['_id'],  # ID único para a tag "Outras"
                    'name': f'Outras tags sobre {node["name"]}',
                    'parentId': node['_id'],
                    'children': [],
                    'absoluteValue': other_tag_count,
                    'frequency': other_tag_frequency
                }

                # Adiciona a nova tag "Outras" à lista de filhos
                node['children'].append(other_tag)

                # Atualiza a contagem dos filhos após adicionar a nova tag "Outras"
                child_count = sum(tag_count[child['_id']] for child in node['children'])
                print(f"Contagem dos filhos atualizada após adicionar 'Outras': {child_count}")

            # Atualiza a frequência de cada filho
            print(f"sibli{sibling_count}")
            for child in node['children']:
                if sibling_count > 0:
                    child['frequency'] = tag_count[child['_id']] / sibling_count
                else:
                    child['frequency'] = 0
                    print("epa")
                print(f"Frequência da tag filha {child['name']}: {child['frequency']}")
                calculate_frequencies(child, tag_count[node['_id']])
        print(f"sibli2{sibling_count}")
        # Calcula a frequência da tag atual em relação à soma das tags irmãs (sibling_count)
        if sibling_count > 0 and tag_count[node['_id']] > 0:
            node['frequency'] = tag_count[node['_id']] / sibling_count
        else:
            node['frequency'] = node['absoluteValue'] / sibling_count
        print(f"Frequência da tag mãe {node['name']}: {node['frequency']}")

    # Calcular a frequência das tags primárias
    primary_tags = [tag for tag_id, tag in tag_tree.items() if tag['parentId'] is None]
    total_primary_count = sum(tag_count[tag['_id']] for tag in primary_tags)
    print(f"Contagem total das tags primárias: {total_primary_count}")

    for tag in primary_tags:
        if total_primary_count > 0:
            tag['frequency'] = tag_count[tag['_id']] / total_primary_count
        else:
            tag['frequency'] = 0
        print(f"Frequência da tag primária {tag['name']}: {tag['frequency']}")
        calculate_frequencies(tag, total_primary_count)

    





    # Estruturar os dados para D3.js
    hierarchical_data = {
        'name': 'Tags',
        'children': primary_tags
    }
    
    with open('hierarchical_data.json', 'w', encoding='utf-8') as f:
        json.dump(hierarchical_data, f, ensure_ascii=False, indent=4)

    return jsonify(hierarchical_data)


if __name__ == '__main__':
    app.run(debug=True, port=8000)

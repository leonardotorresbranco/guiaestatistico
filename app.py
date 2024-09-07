from flask import Flask, request, jsonify, send_file
import json
from collections import defaultdict, Counter

app = Flask(__name__)

with open('testeTED.json', 'r', encoding='utf-8') as f:
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
    

    tags_data = []
    parent_tags_data = []

    for test in data:
        if test.get('institutionId') == institution_id and start_year <= test.get('year') <= end_year:
            tags_data.extend(test.get('tags', []))
            parent_tags_data.extend(test.get('parentTags', []))
    print (len(tags_data))
    def extract_oid(tag):
        return tag['_id']['$oid']

    tag_count = Counter()

    for tag in tags_data:
        tag_id = extract_oid(tag)
        tag_count[tag_id] += 1
        # parent_id = tag.get('parentId', {})
        # if isinstance(parent_id, dict):
        #     parent_id = parent_id.get('$oid')
        #     if parent_id:
        #         tag_count[parent_id] += 0  # Garante que o parent_id seja contado mesmo que não apareça na lista de tags

    for tag in parent_tags_data:
        tag_id = extract_oid(tag)
        tag_count[tag_id] += 1
        # parent_id = tag.get('parentId', {})
        # if isinstance(parent_id, dict):
        #     parent_id = parent_id.get('$oid')
        #     if parent_id:
        #         tag_count[parent_id] += 0  # Garante que o parent_id seja contado mesmo que não apareça na lista de tags

    
    with open('counter.json', 'w', encoding='utf-8') as f:
        json.dump(tag_count, f, ensure_ascii=False, indent=4)


    tag_tree = {}
    tag_frequencies = defaultdict(float)

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
            'absoluteValue': tag_count[tag_id],
        }

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
                'absoluteValue': tag_count[tag_id],
            }

    operations = []

    for tag_id, tag_info in tag_tree.items():
        parent_id = tag_info['parentId']
        if parent_id:
            operations.append((parent_id, tag_info))

    for parent_id, tag_info in operations:
        if parent_id in tag_tree:
            tag_tree[parent_id]['children'].append(tag_info)

    
    
    

    def calculate_frequencies(node, sibling_count):
        if 'children' in node and node['children']:
            child_count = sum(tag_count[child['_id']] for child in node['children'])

            if child_count < tag_count[node['_id']]:
                other_tag_count = tag_count[node['_id']] - child_count
                other_tag_frequency = other_tag_count / tag_count[node['_id']] if sibling_count > 0 else 0

                other_tag = {
                    '_id': 'other_' + node['_id'],  # ID único para a tag "Outras"
                    'name': f'Outras tags sobre {node["name"]}',
                    'parentId': node['_id'],
                    'children': [],
                    'absoluteValue': other_tag_count,
                    
                    'frequency': other_tag_frequency
                    
                }

                node['children'].append(other_tag)

                child_count = sum(tag_count[child['_id']] for child in node['children'])

            for child in node['children']:
                #child['symbol'] = node['symbol']
                if sibling_count > 0:
                    child['frequency'] = tag_count[child['_id']] / sibling_count
                else:
                    child['frequency'] = 0
                    print("epa")
                calculate_frequencies(child, tag_count[node['_id']])
        if sibling_count > 0 and tag_count[node['_id']] > 0:
            node['frequency'] = tag_count[node['_id']] / sibling_count
        else:
            node['frequency'] = node['absoluteValue'] / sibling_count

    primary_tags = [tag for tag_id, tag in tag_tree.items() if tag['parentId'] is None]
    total_primary_count = sum(tag_count[tag['_id']] for tag in primary_tags)

    for tag in primary_tags:
        
       
            

        if total_primary_count > 0:
            tag['frequency'] = tag_count[tag['_id']] / total_primary_count
        else:
            tag['frequency'] = 0
        calculate_frequencies(tag, total_primary_count)

    
    primary_tags[0]['frequency'] = 1
    primary_tags[0]['name'] = "Dermatologia"

    for tag in primary_tags:
        if tag['name'] == "Dermatologia":
            print(tag['name']) 
            primary_tags.clear()
            primary_tags.append(tag) 
            break




    hierarchical_data = {
        'name': 'Tags',
        'children': primary_tags
    }
    
    #with open('hierarchical_data.json', 'w', encoding='utf-8') as f:
    #    json.dump(hierarchical_data, f, ensure_ascii=False, indent=4)

    return jsonify(hierarchical_data)


if __name__ == '__main__':
    app.run(debug=True, port=8000)

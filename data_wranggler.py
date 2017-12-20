
from audit import audit_tag_key
from audit import audit_street_names
from collections import defaultdict
from utils import sample_generator
from utils import mapparser
from pymongo import MongoClient

import xml.etree.cElementTree as ET
import pprint
import re


OSM_FILE = 'data/granasuncion_paraguay.osm'
SAMPLE_FILE = 'data/sample_granasuncion.osm'


"""
The goals of this script is to report:
- Problems encountered in your map
- Overview of the Data
- Other ideas about the datasets
"""


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = ['version', 'changeset', 'timestamp', 'user', 'uid']


def shape_element(element):
    """
    Transform the shape of the data into a new model of data.
    The output should be a list of dictionaries that look like this:
    {
    "id": "2406124091",
    "type: "node",
    "visible":"true",
    "created": {
              "version":"2",
              "changeset":"17206049",
              "timestamp":"2013-08-03T16:43:42Z",
              "user":"linuxUser16",
              "uid":"1219059"
            },
    "pos": [41.9757030, -87.6921867],
    "address": {
              "housenumber": "5157",
              "postcode": "60625",
              "street": "North Lincoln Ave"
            },
    "amenity": "restaurant",
    "cuisine": "mexican",
    "name": "La Cabana De Don Luis",
    "phone": "1 (773)-271-5176"
    }
    """
    node_has_tags = False
    node = {'type_element': '', 'created': {}}
    if element.tag == 'node' or element.tag == 'way':
        node['type_element'] = element.tag
        element_attrs = element.attrib
        for key, value in element_attrs.items():
            if key in CREATED:
                node['created'][key] = value
            else:
                if key in ['lat', 'lon']:
                    if 'pos' not in node.keys():
                        node['pos'] = [0.0] * 2
                    if key == 'lat':
                        node['pos'][0] = float(value)
                    else:
                        node['pos'][1] = float(value)
                else:
                    node[key] = value
        for child in element:
            child_attrs = child.attrib
            if child.tag == 'tag':
                if problemchars.search(child_attrs['k']):
                    continue
                else:
                    node_has_tags = True
                    if child_attrs['k'].startswith('addr:'):
                        addr_splitted = child_attrs['k'].split(':')
                        for token in addr_splitted:
                            if len(addr_splitted) == 2:
                                if 'address' not in node.keys():
                                    node['address'] = {}
                                # Clean street name
                                street_name = child_attrs['v']
                                street_name = audit_street_names.update_street_name(street_name)
                                node['address'][addr_splitted[1]] = street_name
                    else:
                        if ':' in child_attrs['k']:
                            child_attrs['k'].replace(':', '_')
                        node[child_attrs['k']] = child_attrs['v']
            elif child.tag == 'nd':
                if 'node_refs' not in node.keys():
                    node['node_refs'] = []
                node['node_refs'].append(child_attrs['ref'])
        return (node, node_has_tags)
    else:
        return None


def get_db():
    client = MongoClient('localhost:27017')
    db = client.osm
    return db


def transform_xml_map_data_to_dict(osm_file):
    data = []
    problematic_elements = {
        'nodes_without_id': 0,
        'nodes_without_position': 0,
        'nodes_without_tags': 0,
        'ways_without_references': 0,
        'ways_without_tags': 0
    }
    for _, element in ET.iterparse(osm_file):
        el = shape_element(element)
        if el:
            el_dict = el[0]
            el_has_tags = el[1]
            if el_dict['type_element'] == 'node':
                if not el_has_tags:
                    problematic_elements['nodes_without_tags'] +=1
                if 'id' not in el_dict.keys():
                    problematic_elements['nodes_without_id'] +=1
                if 'pos' not in el_dict.keys():
                    problematic_elements['nodes_without_position'] +=1
            else:
                if not el_has_tags:
                    problematic_elements['ways_without_tags'] += 1
                if 'node_refs' not in el_dict.keys():
                    problematic_elements['ways_without_references'] += 1
            data.append(el_dict)
    return (data, problematic_elements)


def read_xml_and_insert_into_db(osm_file, clear_collection=True):
    print('Reading and transforming data...')
    # Transform data in xml format to python dictionaries
    data_tuple = transform_xml_map_data_to_dict(osm_file)
    arr_data = data_tuple[0]
    pro_data = data_tuple[1]
    # Print data with problems
    print(pro_data)
    # Save into the MongoDB collection
    db = get_db()
    if clear_collection:
        db.asuncion.remove({})
    print('Inserting data into the db...')
    for element in arr_data:
        db.asuncion.insert(element)
    # Print out some simple statistics about the collection
    print('There are {0} records registered in the database'.format(db.asuncion.count()))


def aggregate(db, pipeline):
    return [doc for doc in db.asuncion.aggregate(pipeline)]


def records_by_type(db):
    pipeline = [
        {
            '$group': {
                '_id': '$type_element',
                'num_rec': {'$sum': 1}
            }
        },
        {
            '$sort': {'count': -1}
        }
    ]
    return aggregate(db, pipeline)


def unique_contributors(db):
    pipeline = [
        {
            '$group': {
                '_id': '$created.uid',
                'user': {'$first': '$created.uid'},
                'contributions': {'$sum': 1}
            }
        },
        {
            '$sort': {'contributions': -1}
        }
    ]
    return aggregate(db, pipeline)


def value_tags(db, tag):
    pipeline = [
        {
            '$match': {
                'type_element': {'$eq': 'node'},
                tag: {'$exists': 1}
            }
        },
        {
            '$group': {
                '_id': '$'+tag,
                'counter': {'$sum': 1}
            }
        },
        {
            '$sort': {'counter': -1}
        }
    ]
    return aggregate(db, pipeline)


def common_tags(db, type_element='node'):
    print('Type element: ', type_element)
    minimun_keys = ['_id', 'created', 'id', 'type_element', 'pos']
    nodes = db.asuncion.find({'type_element': type_element})
    print('Total elements: ', nodes.count())
    nodes_without_tags = 0
    extra_attrs = defaultdict(int)
    for node in nodes:
        node_attrs = node.keys()
        new_attrs_counter = 0
        for node_attr in node_attrs:
            if node_attr not in minimun_keys:
                new_attrs_counter += 1
                extra_attrs[node_attr] += 1
        if new_attrs_counter == 0:
            nodes_without_tags += 1
    print('Elements without tags: ', nodes_without_tags)
    print('Most common tags')
    sorted_attrs = [(k, extra_attrs[k])
                    for k in sorted(extra_attrs, key=extra_attrs.get, reverse=True)]
    pprint.pprint(sorted_attrs[0:10])
    # give examples of common tags
    print()
    for i in range(10):
        tag = sorted_attrs[i][0]
        print('Tag: ', tag)
        pprint.pprint(value_tags(db, tag)[0:10])
        print()


def compute_statistics(db):
    print('Number of records: {0}'.format(db.asuncion.count()))
    print('Type of records and frequency')
    pprint.pprint(records_by_type(db))
    print('Unique contributors')
    contributors = unique_contributors(db)
    print(len(contributors))
    print('Top-10 contributors')
    pprint.pprint(contributors[0:10])


if __name__ == "__main__":
    # Generate a sample of the large dataset
    sample_generator.generate_sample(OSM_FILE, SAMPLE_FILE, k=15)
    # Count the number of unique tags
    tags_dict = mapparser.count_tags(SAMPLE_FILE)
    pprint.pprint(tags_dict)
    # Audit tag key names
    keys = audit_tag_key.audit_tag_key_names(SAMPLE_FILE)
    pprint.pprint(keys)
    # Audit street names
    sts = audit_street_names.audit(SAMPLE_FILE)
    pprint.pprint(sts)
    # Insert data into ta MongoDB collection
    read_xml_and_insert_into_db(OSM_FILE)
    db = get_db()
    # Print an overview of the data
    compute_statistics(db)
    # Find common tags in nodes and print the most common ones
    common_tags(db, type_element='node')
    # Find common tags in ways and print the most common ones
    common_tags(db, type_element='way')



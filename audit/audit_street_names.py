
import xml.etree.cElementTree as ET
from collections import defaultdict
import re


"""
Your task in this exercise has two steps:

- audit the OSMFILE and change the variable 'mapping' to reflect the changes needed to fix
    the unexpected street types to the appropriate ones in the expected list.
    You have to add mappings only for the actual problems you find in this OSMFILE,
    not a generalized solution, since that may and will depend on the particular area you are auditing.
- write the update_name function, to actually fix the street name.
    The function takes a string with street name as an argument and should return the fixed name
    We have provided a simple test so that you see what exactly is expected
"""


street_type_re = re.compile(r'^\S+\b', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons"]

street_prefixes = {
    'Ave': 'Avenida',
    'Ave.': 'Avenida',
    'Avda': 'Avenida',
    'Avda.': 'Avenida',
}

name_titles = {
   'Tte': 'Teniente',
   'Tte.': 'Teniente',
   'Cnel': 'Coronel',
   'Cnel.': 'Coronel',
   'Cmte': 'Comandante',
   'Cmte.': 'Comandante',
   'Sgto': 'Sargento',
   'Sgto.': 'Sargento',
   'Gral': 'General',
   'Gral.': 'General',
   'Dr': 'Doctor',
   'Dr.': 'Doctor',
   'Ing': 'Ingeniero',
   'Ing.': 'Ingeniero',
   'Prof': 'Profesor',
   'Prof.': 'Profesor',
}


wrong_names = {
   'Linch': 'Lynch',
   'Cora': 'Corá',
   'Lopez': 'López'
}


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        #if street_type not in expected:
        street_types[street_type].add(street_name)


def is_street_name(elem):
    return elem.attrib['k'] == 'addr:street'


def update_name(name, mapping):
    splitted_name = name.split()
    for wrong_name, correct_name in mapping.items():
        for token in splitted_name:
            if token == wrong_name:
                name = name.replace(wrong_name, correct_name)
    return name


def update_street_name(name):
    name = name.title()
    # fix street prefixes
    name = update_name(name, street_prefixes)
    # fix name titles
    name = update_name(name, name_titles)
    # fix wrong names
    name = update_name(name, wrong_names)
    return name


def audit(osmfile):
    osm_file = open(osmfile, 'r', encoding='utf-8')
    streets = set()
    for event, elem in ET.iterparse(osm_file, events=('start',)):
        if elem.tag == 'node' or elem.tag == 'way':
            for tag in elem.iter('tag'):
                if is_street_name(tag):
                    name = update_street_name(tag.attrib['v'])
                    streets.add(name)
    osm_file.close()
    return streets


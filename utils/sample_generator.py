#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET  # Use cElementTree or lxml if too slow


def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def generate_sample(osm_filename, sample_filename, k=10):
    print('Generating the sample...')
    with open(sample_filename, 'wb') as output:
        output.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write(b'<osm>\n  ')

        # Write every kth top level element
        for i, element in enumerate(get_element(osm_filename)):
            if i % k == 0:
                output.write(ET.tostring(element, encoding='utf-8'))

        output.write(b'</osm>')
    print('Sample created, please take a look at {0}'.format(sample_filename))


#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Use the iterative parsing to process the map file and
find out not only what tags are there, but also how many, to get the
feeling on how much of which data you can expect to have in the map.
"""

import xml.etree.cElementTree as ET


def count_tags(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    tags = {root.tag: 1}
    for high_level_node in root.findall('.//'):
        if high_level_node.tag not in tags.keys():
            tags[high_level_node.tag] = 1
        else:
            tags[high_level_node.tag] += 1
    return tags

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import pprint

"""
Find out how many unique users have contributed to the map
"""

def get_user(element):
    if 'user' in element.attrib.keys():
        return element.attrib['uid']
    return None


def process_map(filename):
    users = set()
    for _, element in ET.iterparse(filename):
        user_id = get_user(element)
        if user_id:
            users.add(user_id)
    return users


if __name__ == "__main__":
    users = process_map('../data/sample_granasuncion.osm')
    print('{0} users have contributed to the map of Gran Asuncion'.format(len(users)))
    pprint.pprint(users)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import re
import json
import argparse
import shutil
import urllib.request
from pathlib import Path


map_name_overworld = "Overworld - overworld"
map_name_nether = "Nether - nether"
map_name_end = "The End - end"
patreon_zone_color = "#ff7800"
patreon_layer_title = "Patreon Claimed Zones"
patreon_tooltip_prefix = "Patreon claimed zone: "  # will be followed by name if found
lookup_uuids = True

# Add predefined zones here:
zones = {
    map_name_overworld: [
        {"title": "Mindcrack Build Zone", "zones": [{"n": -1500, "e": 1500, "s": 1500, "w": -1500, "color": "#ff7800", "tooltip": "Mindcrack Build Zone"}]},
    ],

}


coords_regex = re.compile('.*world;([0-9]+);[0-9]+;([0-9]+)$')
current_location = os.path.dirname(os.path.realpath(__file__))
uuid_cache = {}

# PARSE ARGUMENTS
parser = argparse.ArgumentParser()
parser.add_argument('yamldir', help='The directory containing all the yaml files')
parser.add_argument('outputdir', help='The directory in which to write zones.json')
args = parser.parse_args()


def lookupMinecraftID(uuid):
    if len(uuid_cache) == 0:
        uuid_cache_file = os.path.join(args.outputdir, "uuid.cache")
        if os.path.exists(uuid_cache_file):
            cache_contents = Path(uuid_cache_file).read_text().splitlines()
            for line in cache_contents:
                components = line.split(":")
                if len(components) == 2:
                    uuid_cache[components[0]] = components[1]

    if uuid in uuid_cache:
        return uuid_cache[uuid]

    try:
        data = json.loads(urllib.request.urlopen("https://api.mojang.com/user/profiles/" + uuid + "/names").read())
    except:
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names")
        return ""

    if not isinstance(data, list):
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - root is not a list")
        return ""

    if len(data) == 0:
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - root is empty list")
        return ""

    first = data[0]
    if not isinstance(first, dict):
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - first object in root is not a dict")
        return ""

    if not "name" in first:
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - first object in root doesn't have name field")
        return ""

    uuid_cache[uuid] = first["name"]
    return first["name"]


# LOAD ALL YAML FILES
loaded_coords = []
for (root, dirs, filenames) in os.walk(args.yamldir):
    for f in filenames:
        if not f.endswith(".yml"):
            continue
        ymlfile = os.path.join(root, f)
        try:
            ymlcontents = Path(ymlfile).read_text().splitlines()
        except:
            print("Error parsing " + f)
            continue

        north = 0
        east = 0
        south = 0
        west = 0
        owner = ""
        try:
            for line in ymlcontents:
                if line.startswith("Lesser Boundary Corner"):
                    m = re.match(coords_regex, line)
                    if m == None:
                        raise Exception("Couldn't parse Lesser Boundary Corner in " + f)
                    west = m.group(1)
                    north = m.group(2)

                if line.startswith("Greater Boundary Corner"):
                    m = re.match(coords_regex, line)
                    if m == None:
                        raise Exception("Couldn't parse Greater Boundary Corner in " + f)
                    east = m.group(1)
                    south = m.group(2)

                if lookup_uuids and line.startswith("Owner:"):
                    owner = line.replace("Owner: ", "").replace("-", "")
                    accountname = lookupMinecraftID(owner)
                    owner = accountname
        except Exception as e:
            print(e)
            continue
        if len(owner) == 0:
            loaded_coords.append({"n": north, "e": east, "s": south, "w": west, "color": patreon_zone_color})
        else:
            loaded_coords.append({"n": north, "e": east, "s": south, "w": west, "color": patreon_zone_color, "tooltip": patreon_tooltip_prefix + owner})

if len(loaded_coords) > 0:
    zones[map_name_overworld].append({"title": patreon_layer_title, "zones": loaded_coords})

# GENERATE zones.json
Path(os.path.join(args.outputdir, "zones.json")).write_text(json.dumps(zones))

# COPY mindcrack.js IF IT DOESN"T EXIST YET
mindcrack_js_src = os.path.join(current_location, "mindcrack.js")
mindcrack_js_dst = os.path.join(args.outputdir, "mindcrack.js")

if not os.path.exists(mindcrack_js_src):
    print("Can't find source mindcrack.js")
else:
    shutil.copyfile(mindcrack_js_src, mindcrack_js_dst)

# CHECK IF mindcrack.js IS REFERENCED IN index.html - IF NOT, ADD IT
indexhtml = os.path.join(args.outputdir, "index.html")
indexhtml_contents = Path(indexhtml).read_text()
if "mindcrack.js" not in indexhtml_contents:
    Path(indexhtml).write_text(indexhtml_contents.replace('baseMarkers.js"></script>',
                                                          'baseMarkers.js"></script>\n    <script type="text/javascript" src="mindcrack.js"></script>'))

# WRITE OUT uuid.cache IN outputdir
tmp = ""
for uuid in uuid_cache:
    tmp = tmp + uuid + ":" + uuid_cache[uuid] + "\n"
uuid_cache_file = os.path.join(args.outputdir, "uuid.cache")
Path(uuid_cache_file).write_text(tmp)

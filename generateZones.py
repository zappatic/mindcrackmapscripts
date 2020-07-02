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
lookup_uuids = True

# Add predefined zones here:
zones = {
    map_name_overworld: [
        {"title": "Mindcrack Build Zone", "zones": [{"n": -1500, "e": 1500, "s": 1500, "w": -1500, "color": "#ff7800", "tooltip": "Mindcrack Build Zone"}]},
    ],
    map_name_nether: [
    ],
    map_name_end: [
    ],
}


coords_overworld_regex = re.compile('.*world;(-?[0-9]+);-?[0-9]+;(-?[0-9]+)$')
coords_nether_regex = re.compile('.*world_nether;(-?[0-9]+);-?[0-9]+;(-?[0-9]+)$')
coords_end_regex = re.compile('.*world_the_end;(-?[0-9]+);-?[0-9]+;(-?[0-9]+)$')
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

    last = data[-1]
    if not isinstance(last, dict):
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - last object in root is not a dict")
        return ""

    if not "name" in last:
        print("Failed parsing Minecraft API for: " + "https://api.mojang.com/user/profiles/" + uuid + "/names - last object in root doesn't have name field")
        return ""

    uuid_cache[uuid] = last["name"]
    return last["name"]


# LOAD ALL YAML FILES
loaded_coords_overworld = []
loaded_coords_nether = []
loaded_coords_end = []
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
        world = "overworld"
        try:
            for line in ymlcontents:
                if line.startswith("Lesser Boundary Corner"):
                    m = re.match(coords_overworld_regex, line)
                    if m != None:
                        west = m.group(1)
                        north = m.group(2)
                        world = "overworld"
                    else:
                        m = re.match(coords_nether_regex, line)
                        if m != None:
                            west = m.group(1)
                            north = m.group(2)
                            world = "nether"
                        else:
                            m = re.match(coords_end_regex, line)
                            if m != None:
                                west = m.group(1)
                                north = m.group(2)
                                world = "end"
                            else:
                                raise Exception("Couldn't parse Lesser Boundary Corner in " + f)

                if line.startswith("Greater Boundary Corner"):
                    m = re.match(coords_overworld_regex, line)
                    if m != None:
                        east = m.group(1)
                        south = m.group(2)
                        world = "overworld"
                    else:
                        m = re.match(coords_nether_regex, line)
                        if m != None:
                            east = m.group(1)
                            south = m.group(2)
                            world = "nether"
                        else:
                            m = re.match(coords_end_regex, line)
                            if m != None:
                                east = m.group(1)
                                south = m.group(2)
                                world = "end"
                            else:
                                raise Exception("Couldn't parse Greater Boundary Corner in " + f)

                if lookup_uuids and line.startswith("Owner:"):
                    owner = line.replace("Owner: ", "").replace("-", "")
                    accountname = lookupMinecraftID(owner)
                    owner = accountname
        except Exception as e:
            print(e)
            continue

        entry = {"n": int(north), "e": int(east), "s": int(south), "w": int(west), "color": patreon_zone_color}
        if len(owner) != 0:
            entry["tooltip"] = owner
        if world == "overworld":
            loaded_coords_overworld.append(entry)
        elif world == "nether":
            loaded_coords_nether.append(entry)
        elif world == "end":
            loaded_coords_end.append(entry)

if len(loaded_coords_overworld) > 0:
    zones[map_name_overworld].append({"title": patreon_layer_title, "zones": loaded_coords_overworld})
if len(loaded_coords_nether) > 0:
    zones[map_name_nether].append({"title": patreon_layer_title, "zones": loaded_coords_nether})
if len(loaded_coords_end) > 0:
    zones[map_name_end].append({"title": patreon_layer_title, "zones": loaded_coords_end})

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

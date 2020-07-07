#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import re
import json
import argparse
import anvil
import shutil
import math
import urllib.request
from pathlib import Path


map_name_overworld = "Overworld - overworld"
map_name_nether = "Nether - nether"
map_name_end = "The End - end"
patreon_zone_color = "#ff7800"
patreon_layer_title = "Claimed Zones"
lookup_uuids = True

# Add predefined zones here:
zones = {
    map_name_overworld: [
        {"title": "Mindcrack Build Zone", "color": "#ff7800", "zones": [{"n": -1500, "e": 1500, "s": 1500, "w": -1500, "tooltip": "Mindcrack Build Zone"}]},
    ],
    map_name_nether: [
    ],
    map_name_end: [
    ],
}

# Add mappings between the world identifier in the GriefProtection YAML file and the Overviewer map name here:
claim_dimensions = {
    "world": {"mapname": map_name_overworld, "diskname": ""},
    "world_nether": {"mapname": map_name_nether, "diskname": "DIM-1"},
    "world_the_end": {"mapname": map_name_end, "diskname": "DIM1"},
}

coords_regex = re.compile('.*(world.*?);(-?[0-9]+);-?[0-9]+;(-?[0-9]+)$')
current_location = os.path.dirname(os.path.realpath(__file__))
uuid_cache = {}
terrain_height_lookup = {}
terrain_heights = {}
loaded_coords = {}

# PARSE ARGUMENTS
parser = argparse.ArgumentParser()
parser.add_argument('yamldir', help='The directory containing all the yaml files')
parser.add_argument('mcadir', help='The directory that contains the world save')
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


def markCoordsForLookup(x, z, world):
    global terrain_height_lookup
    region = "r." + str(math.floor(math.floor(x / 16) / 32)) + "." + str(math.floor(math.floor(z / 16) / 32)) + ".mca"
    if world not in terrain_height_lookup:
        terrain_height_lookup[world] = {}

    if region not in terrain_height_lookup[world]:
        terrain_height_lookup[world][region] = []

    terrain_height_lookup[world][region].append([x, z])


# LOAD ALL YAML FILES
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
        world = ""
        try:
            for line in ymlcontents:
                if line.startswith("Lesser Boundary Corner"):
                    m = re.match(coords_regex, line)
                    if m != None:
                        world = m.group(1)
                        west = int(m.group(2))
                        north = int(m.group(3))
                    else:
                        raise Exception("Couldn't parse Lesser Boundary Corner in " + f)

                elif line.startswith("Greater Boundary Corner"):
                    m = re.match(coords_regex, line)
                    if m != None:
                        world = m.group(1)
                        east = int(m.group(2))
                        south = int(m.group(3))
                    else:
                        raise Exception("Couldn't parse Greater Boundary Corner in " + f)

                elif lookup_uuids and line.startswith("Owner:"):
                    owner = line.replace("Owner: ", "").replace("-", "")
                    accountname = lookupMinecraftID(owner)
                    owner = accountname
        except Exception as e:
            print(e)
            continue

        entry = {"n": north, "e": east, "s": south, "w": west}

        markCoordsForLookup(east, north, world)
        markCoordsForLookup(east, south, world)
        markCoordsForLookup(west, north, world)
        markCoordsForLookup(west, south, world)

        if len(owner) != 0:
            entry["tooltip"] = owner

        if world not in loaded_coords:
            loaded_coords[world] = []
        loaded_coords[world].append(entry)

# LOOKUP TERRAIN HEIGHTS OF ALL ZONE CORNERS
for world in terrain_height_lookup:
    if world not in claim_dimensions:
        print("Terrain lookup world name '" + world + "' not found in the claim_dimensions")
    else:
        for region_name in terrain_height_lookup[world]:
            if world not in terrain_heights:
                terrain_heights[world] = {}
            try:
                region = anvil.Region.from_file(os.path.join(args.mcadir, claim_dimensions[world]["diskname"], "region", region_name))
                for [x, z] in terrain_height_lookup[world][region_name]:
                    chunk_x = math.floor(x / 16)
                    chunk_z = math.floor(z / 16)
                    chunk = region.get_chunk(chunk_x, chunk_z)
                    for y in reversed(range(255)):
                        block = chunk.get_block(x - (chunk_x * 16), y, z - (chunk_z * 16))
                        if block.id != "air" and block.id != "bedrock":
                            break
                    terrain_heights[world][str(x) + "," + str(z)] = y

            except:
                print("Error loading terrain height from " + region_name)
                pass

# APPLY TERRAIN HEIGHTS TO ZONES
for world in loaded_coords:
    if world not in terrain_heights:
        continue
    for entry in loaded_coords[world]:
        key = str(entry["e"]) + "," + str(entry["n"])
        if key in terrain_heights[world]:
            entry["elNE"] = terrain_heights[world][key]
        key = str(entry["e"]) + "," + str(entry["s"])
        if key in terrain_heights[world]:
            entry["elSE"] = terrain_heights[world][key]
        key = str(entry["w"]) + "," + str(entry["n"])
        if key in terrain_heights[world]:
            entry["elNW"] = terrain_heights[world][key]
        key = str(entry["w"]) + "," + str(entry["s"])
        if key in terrain_heights[world]:
            entry["elSW"] = terrain_heights[world][key]

# SAVE THE ZONES
for world in loaded_coords:
    if world not in claim_dimensions:
        print("Yaml world name '" + world + "' not found in the claim_dimensions")
    else:
        dimension = claim_dimensions[world]
        zones[dimension["mapname"]].append({"title": patreon_layer_title, "color": patreon_zone_color, "zones": loaded_coords[world]})

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

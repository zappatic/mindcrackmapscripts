/*
 * The layerData object contains all the information about the layers that need to be added as well as the polygons within/
 * The structure is : { <map name> => [ { title, color, zones: [ {n,e,s,w, tooltip}, ... ] }, ... ] , ... }
 * It is dynamically loaded from zones.json
 */
let layerData = {};

// The altitude at which the rectangles should be drawn, if the precalculated terrain elevation is not present
const polygonAltitude = 64;

// The zoom level to use when selecting a claimed zone in the zone jumper dropdown
const zoneJumperZoomLevel = 11;

// A cache of the currently active overlays, so we can clear them when changing maps
let activeOverlays = [];
// A cache of the currently active hover lines (terrain height), so we can clear them when hovering off a zone
let activeHoverlines = [];

const dir = { NORTHEAST: "ne", SOUTHEAST: "se", NORTHWEST: "nw", SOUTHWEST: "sw" };
const vert = { TOP: "top", BOTTOM: "bottom" };

// This function converts a point centered inside a block to the top or bottom of a corner, depending on the cardinal direction
const fromWorldToLatLngNonCentered = (x, y, z, tset, corner, vertical = vert.TOP) => {
  var perPixel = 1.0 / (overviewerConfig.CONST.tileSize * Math.pow(2, tset.zoomLevels));
  let [lat, lng] = overviewer.util.fromWorldToLatLng(x, y, z, tset);
  lat *= -1;
  lat /= overviewerConfig.CONST.tileSize;
  lng /= overviewerConfig.CONST.tileSize;

  if (vertical == vert.TOP) {
    lat -= 12 * perPixel;
  } else if (vertical == vert.BOTTOM) {
    lat += 12 * perPixel;
  }

  if (corner === dir.NORTHWEST) {
    lng -= 12 * perPixel;
  } else if (corner === dir.NORTHEAST) {
    lat -= 6 * perPixel;
  } else if (corner === dir.SOUTHEAST) {
    lng += 12 * perPixel;
  } else if (corner === dir.SOUTHWEST) {
    lat += 6 * perPixel;
  }

  return [-lat * overviewerConfig.CONST.tileSize, lng * overviewerConfig.CONST.tileSize];
};

// This function calculates the highest of the four corners of a zone
const zoneElevation = (zone) => {
  let elevation = polygonAltitude;
  if (zone.hasOwnProperty("elNE") && zone.elNE > elevation) {
    elevation = zone.elNE;
  }
  if (zone.hasOwnProperty("elSE") && zone.elSE > elevation) {
    elevation = zone.elSE;
  }
  if (zone.hasOwnProperty("elNW") && zone.elNW > elevation) {
    elevation = zone.elNW;
  }
  if (zone.hasOwnProperty("elSW") && zone.elSW > elevation) {
    elevation = zone.elSW;
  }
  return elevation;
};

// The function that adds the polygon layers to the map
const loadPolygons = () => {
  const tileSetInfo = overviewer.current_layer[overviewer.current_world].tileSetConfig;

  // Clear previously added layers
  activeOverlays.forEach((ao) => {
    overviewer.map.removeLayer(ao);
    overviewer.layerCtrl.removeLayer(ao);
  });
  activeOverlays = [];

  // Clear the zoneJumper dropdown
  overviewer.zoneJumper.clear();

  // Loop over the provided layer data
  for (const [mapName, layers] of Object.entries(layerData)) {
    // Ignore the data if the layer doesn't belong to the current world
    if (mapName !== overviewer.current_world) {
      continue;
    }

    const jumpToEntries = [];

    // Loop all the layers assigned to the current map name
    layers.forEach((layer) => {
      // Create a layer group to hold all the rectangle zones within this layer
      const layerGroup = new L.layerGroup();

      // Loop all the rectangle zones within this layer
      layer.zones.forEach((zone) => {
        // Determine highest elevated corner
        const elevation = zoneElevation(zone);

        // Convert from Minecraft world coordinates to lat/lng
        const corner1 = fromWorldToLatLngNonCentered(zone.e, elevation, zone.n, tileSetInfo, dir.NORTHEAST);
        const corner2 = fromWorldToLatLngNonCentered(zone.e, elevation, zone.s, tileSetInfo, dir.SOUTHEAST);
        const corner3 = fromWorldToLatLngNonCentered(zone.w, elevation, zone.s, tileSetInfo, dir.SOUTHWEST);
        const corner4 = fromWorldToLatLngNonCentered(zone.w, elevation, zone.n, tileSetInfo, dir.NORTHWEST);

        // Create the polygon
        const polygon = new L.polygon([corner1, corner2, corner3, corner4], { color: layer.color, weight: 1 });

        // Assign a tooltip if it is present (sticky means the tooltip follows the mouse pointer)
        if (zone.hasOwnProperty("tooltip")) {
          if (zone.tooltip !== "Mindcrack Build Zone") {
            polygon.bindTooltip("Claimed by " + zone.tooltip, { sticky: true });
            jumpToEntries.push(zone);
          } else {
            polygon.bindTooltip(zone.tooltip, { sticky: true });
          }
        }

        // When hovering over the zone rectangle, draw solid vertical lines until the terrain is reached, then dashed lines to Y 0
        polygon.on("mouseover", (e) => {
          const lineProps = { color: layer.color, weight: 1 };
          const linePropsDashed = { color: layer.color, weight: 1, dashArray: [5, 5], dashOffset: 3 };

          const elevationNE = zone.hasOwnProperty("elNE") ? zone.elNE : 0;
          const elevationSE = zone.hasOwnProperty("elSE") ? zone.elSE : 0;
          const elevationSW = zone.hasOwnProperty("elSW") ? zone.elSW : 0;
          const elevationNW = zone.hasOwnProperty("elNW") ? zone.elNW : 0;

          if (elevation !== elevationNE) {
            const corner1Top = fromWorldToLatLngNonCentered(zone.e, elevation, zone.n, tileSetInfo, dir.NORTHEAST);
            const corner1Bottom = fromWorldToLatLngNonCentered(zone.e, elevationNE, zone.n, tileSetInfo, dir.NORTHEAST);
            const lineNE = new L.polyline([corner1Top, corner1Bottom], lineProps);
            lineNE.addTo(overviewer.map);
            activeHoverlines.push(lineNE);
          }

          const corner2Top = fromWorldToLatLngNonCentered(zone.e, elevation, zone.s, tileSetInfo, dir.SOUTHEAST);
          const corner2Bottom = fromWorldToLatLngNonCentered(zone.e, elevationSE, zone.s, tileSetInfo, dir.SOUTHEAST);
          const corner2BottomDashed = fromWorldToLatLngNonCentered(zone.e, 0, zone.s, tileSetInfo, dir.SOUTHEAST);
          if (elevation !== elevationSE) {
            const lineSE = new L.polyline([corner2Top, corner2Bottom], lineProps);
            lineSE.addTo(overviewer.map);
            activeHoverlines.push(lineSE);
          }
          const lineSEdashed = new L.polyline([corner2Bottom, corner2BottomDashed], linePropsDashed);
          lineSEdashed.addTo(overviewer.map);
          activeHoverlines.push(lineSEdashed);

          const corner3Top = fromWorldToLatLngNonCentered(zone.w, elevation, zone.s, tileSetInfo, dir.SOUTHWEST);
          const corner3Bottom = fromWorldToLatLngNonCentered(zone.w, elevationSW, zone.s, tileSetInfo, dir.SOUTHWEST);
          const corner3BottomDashed = fromWorldToLatLngNonCentered(zone.w, 0, zone.s, tileSetInfo, dir.SOUTHWEST);
          if (elevation !== elevationSW) {
            const lineSW = new L.polyline([corner3Top, corner3Bottom], lineProps);
            lineSW.addTo(overviewer.map);
            activeHoverlines.push(lineSW);
          }
          const lineSWdashed = new L.polyline([corner3Bottom, corner3BottomDashed], linePropsDashed);
          lineSWdashed.addTo(overviewer.map);
          activeHoverlines.push(lineSWdashed);

          const corner4Top = fromWorldToLatLngNonCentered(zone.w, elevation, zone.n, tileSetInfo, dir.NORTHWEST);
          const corner4Bottom = fromWorldToLatLngNonCentered(zone.w, elevationNW, zone.n, tileSetInfo, dir.NORTHWEST);
          const corner4BottomDashed = fromWorldToLatLngNonCentered(zone.w, 0, zone.n, tileSetInfo, dir.NORTHWEST);
          if (elevation !== elevationNW) {
            const lineNW = new L.polyline([corner4Top, corner4Bottom], lineProps);
            lineNW.addTo(overviewer.map);
            activeHoverlines.push(lineNW);
          }
          const lineNWdashed = new L.polyline([corner4Bottom, corner4BottomDashed], linePropsDashed);
          lineNWdashed.addTo(overviewer.map);
          activeHoverlines.push(lineNWdashed);
        });

        // Remove the vertical lines when moving off of the zone
        polygon.on("mouseout", (e) => {
          activeHoverlines.forEach((ahl) => {
            ahl.remove();
          });
        });

        // Add the polygon to the layer group
        polygon.addTo(layerGroup);
      });

      // Sort the zones, calculate the midpoint and add to the jumpZone dropdown
      jumpToEntries
        .sort((a, b) => {
          return a.tooltip.toLowerCase().localeCompare(b.tooltip.toLowerCase());
        })
        .map((zone) => {
          const midX = Math.round(zone.w + Math.abs(zone.e - zone.w) / 2);
          const midZ = Math.round(zone.n + Math.abs(zone.n - zone.s) / 2);
          overviewer.zoneJumper.addZone(zone.tooltip, { x: midX, z: midZ, elNE: zone.elNe, elSE: zone.elSE, elNW: zone.elNW, elSW: zone.elSW });
        });

      // Remember this layer group so we can remove it later
      activeOverlays.push(layerGroup);

      // Add the layer group to the map
      overviewer.layerCtrl.addOverlay(layerGroup, layer.title);
    });
  }
};

// Function that is ran when the overviewer is ready and loaded
overviewer.util.ready(function () {
  var httpRequest = new XMLHttpRequest();
  httpRequest.onreadystatechange = function () {
    if (httpRequest.readyState === 4) {
      if (httpRequest.status === 200) {
        layerData = JSON.parse(httpRequest.responseText);

        // Install the zone jumper dropdown
        overviewer.zoneJumperClass = L.Control.extend({
          initialize: function (options) {
            L.Util.setOptions(this, options);
            this.container = L.DomUtil.create("div", "zonejumper");
            this.select = L.DomUtil.create("select");
            this.select.onchange = this.onChange;
            this.container.appendChild(this.select);
            this.addZone("Jump to...", null);
          },
          addZone: function (title, coords) {
            var option = L.DomUtil.create("option");
            if (coords) {
              option.value = JSON.stringify(coords);
            } else {
              option.value = "";
            }
            option.innerText = title;
            this.select.appendChild(option);
          },
          clear: function () {
            L.DomUtil.empty(this.select);
            this.addZone("Jump to...", null);
          },
          onChange: function (ev) {
            var z = ev.target.value;
            if (z !== "") {
              const zone = JSON.parse(z);
              const tileSetInfo = overviewer.current_layer[overviewer.current_world].tileSetConfig;
              const latLng = overviewer.util.fromWorldToLatLng(zone.x, zoneElevation(zone), zone.z, tileSetInfo);
              overviewer.map.setView(latLng, zoneJumperZoomLevel);
              ev.target.value = "";
            }
          },
          onAdd: function () {
            return this.container;
          },
        });
        overviewer.zoneJumper = new overviewer.zoneJumperClass();
        overviewer.zoneJumper.addTo(overviewer.map);

        // Call the loadPolygons function for the first time so our layer options load
        loadPolygons();

        // Make sure the loadPolygons function is executed whenever we change the map
        overviewer.map.on("baselayerchange", function (ev) {
          loadPolygons();

          // Make sure that the jump dropdown is always at the bottom
          overviewer.zoneJumper.remove();
          overviewer.zoneJumper.addTo(overviewer.map);
        });
      }
    }
  };
  httpRequest.open("GET", "zones.json");
  httpRequest.send();
});

/*
 * The layerData object contains all the information about the layers that need to be added as well as the polygons within/
 * The structure is : { <map name> => [ { title, zones: [ {n,e,s,w, color, tooltip}, ... ] }, ... ] , ... }
 * It is dynamically loaded from zones.json
 */
let layerData = {};

// The altitude at which the rectangles should be drawn
const polygonAltitude = 64;

// A cache of the currently active overlays, so we can clear them when changing maps
let activeOverlays = [];

// The function that adds the polygon layers to the map
const loadPolygons = () => {
  const tileSetInfo = overviewer.current_layer[overviewer.current_world].tileSetConfig;

  // Clear previously added layers
  activeOverlays.forEach((ao) => {
    overviewer.map.removeLayer(ao);
  });
  activeOverlays = [];

  // Loop over the provided layer data
  for (const [mapName, layers] of Object.entries(layerData)) {
    // Ignore the data if the layer doesn't belong to the current world
    if (mapName !== overviewer.current_world) {
      continue;
    }

    // Loop all the layers assigned to the current map name
    layers.forEach((layer) => {
      // Create a layer group to hold all the rectangle zones within this layer
      const layerGroup = new L.layerGroup();

      // Loop all the rectangle zones within this layer
      layer.zones.forEach((zone) => {
        // Convert from Minecraft world coordinates to lat/lng
        const corner1 = overviewer.util.fromWorldToLatLng(zone.e, polygonAltitude, zone.n, tileSetInfo);
        const corner2 = overviewer.util.fromWorldToLatLng(zone.e, polygonAltitude, zone.s, tileSetInfo);
        const corner3 = overviewer.util.fromWorldToLatLng(zone.w, polygonAltitude, zone.s, tileSetInfo);
        const corner4 = overviewer.util.fromWorldToLatLng(zone.w, polygonAltitude, zone.n, tileSetInfo);

        // Create the polygon
        const polygon = new L.polygon([corner1, corner2, corner3, corner4], { color: zone.color, weight: 1 });

        // Assign a tooltip if it is present (sticky means the tooltip follows the mouse pointer)
        if (zone.hasOwnProperty("tooltip")) {
          polygon.bindTooltip(zone.tooltip, { sticky: true });
        }

        // Add the polygon to the layer group
        polygon.addTo(layerGroup);
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

        // Call the loadPolygons function for the first time so our layer options load
        loadPolygons();

        // Make sure the loadPolygons function is executed whenever we change the map
        overviewer.map.on("baselayerchange", function (ev) {
          loadPolygons();
        });
      }
    }
  };
  httpRequest.open("GET", "zones.json");
  httpRequest.send();
});

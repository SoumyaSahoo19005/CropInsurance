
// Function to create monthly mean Sentinel-1 VH images
var createMonthlyMeanImage = function(startDate, endDate) {
  return ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(roi)
    .filterDate(startDate, endDate)
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .select('VH')
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
    .mean();
};

// Create monthly mean images
var s1_J = createMonthlyMeanImage('2023-06-01', '2023-06-30').rename('VH1');
var s1_A = createMonthlyMeanImage('2023-07-01', '2023-07-30').rename('VH2');
var s1_S = createMonthlyMeanImage('2023-08-01', '2023-08-30').rename('VH3');
var s1_O = createMonthlyMeanImage('2023-09-01', '2023-09-30').rename('VH4');
var s1_N = createMonthlyMeanImage('2023-10-01', '2023-10-30').rename('VH5');

var stacked_s1 = s1_J.addBands([s1_A, s1_S, s1_O, s1_N]).clip(roi);
var stacked_scaled = stacked_s1.multiply(10).add(300).uint8();
var bands = ['VH2','VH4','VH5'];// Change accordignly
var display = {bands:bands,min:0 , max:255};

Map.addLayer(stacked_scaled,display, 'Stacked');


var training = stacked_scaled.sample({
  region: roi,
  scale: 10,
  numPixels: 10000,
  seed: 100
});

var ncluster = 6;
var originalClusterer = ee.Clusterer.wekaKMeans(ncluster).train(training);

// Original clustering
var originalClusters = stacked_scaled.cluster(originalClusterer);

var clusterVis = {
  palette: ['red','green','blue','lightgreen','yellow'],
  min: 0,
  max: ncluster-1,
};

Map.addLayer(originalClusters,clusterVis,'K-Means');
// var updatedNCluster = 6;

var filtercluster = originalClusters.updateMask((originalClusters.eq(3)).or(originalClusters.eq(0)));

Map.addLayer(filtercluster,{min:0,max:1,palette:['red']},'cluster');

Export.image.toDrive({
  image: filtercluster,
  description: 'filtercluster',
  scale: 30,
  folder: 'ORSAC',
  region:roi,
  fileFormat: 'GeoTIFF'
});

var area = filtercluster.multiply(ee.Image.pixelArea());

// Sum the area for the entire ROI
var totalArea = area.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 10,
  maxPixels: 1e13
});

// Convert square meters to acres for the total area
var totalAreaAcres = ee.Number(totalArea.get('cluster')).multiply(2.47105);

var crop_area = area.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 10,
  maxPixels: 1e13
});

// Convert square meters to acres (1 hectare = 2.47105 acres)
var crop_acreage = ee.Number(crop_area.get('cluster')).multiply(2.47105);

// Print the estimated crop acreage
print('Estimated Crop Acreage:', crop_acreage, 'acres');

// Convert crop_area to a binary image where non-zero values become 1
var binaryCropMask = filtercluster.gt(1);

// Mask the s1_J image using the binary crop mask
var intersection = s1_J.updateMask(binaryCropMask);


// Calculate the intersected area
var intersectionArea = intersection.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 10,
  maxPixels: 1e13
});


// Convert square meters to acres for the intersection area
var intersected_acreage = ee.Number(intersectionArea.get('VH1')).multiply(2.47105);

// Print the intersected area
print('Intersected Area:', intersected_acreage, 'acres');


Map.addLayer(intersection);



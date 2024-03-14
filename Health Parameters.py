// Define the region of interest (ROI)

// Function to mask clouds in Sentinel-2 imagery
function maskS2clouds(image) {
  var qa = image.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
              .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return image.updateMask(mask).divide(10000);
}

// Function to calculate NDVI and add it as a band
var addNDVI = function(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  return image.addBands(ndvi);
};

var addLSWI = function(image) {
  var lswi = image.normalizedDifference(['B8', 'B11']).rename('LSWI');
  return image.addBands(lswi);
};

// Load Sentinel-1 image collectio
var sentinel1 = ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(roi)
                  .filterDate('2017-06-01', '2017-10-30')
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                  .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'));

// Load Sentinel-2 image collection and apply filters and masking
var sentinel2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterDate('2017-06-01', '2017-10-30')
                  .filterBounds(roi)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                  .map(maskS2clouds)
                  .map(addNDVI)
                  .map(addLSWI);

// Function to calculate FAPAR
var calculateFAPAR = function(image) {
  // Calculate FAPAR using bands representing red and near-infrared
  var fapar = image.expression(
    '(1 - ((RED - NIR) / (RED + NIR))) * 0.5', {
      'RED': image.select('Oa10_radiance'),
      'NIR': image.select('Oa08_radiance')
    }).rename('FAPAR');

  return fapar;
};

// Load Sentinel-3 image collection and filter
var s3OLCI = ee.ImageCollection("COPERNICUS/S3/OLCI")
            .filterBounds(roi)
            .filterDate('2017-06-01', '2017-10-30')
            .map(calculateFAPAR);

// Calculate the integrated FAPAR
var integratedFAPAR = s3OLCI.sum();

// Calculate statistics by Panchayat
var statisticsByPanchayat = roi.map(function(feature) {
 var panchayatName = feature.get('gpname'); 
  
  // Filtering Sentinel-2 images for the current Panchayat
  var sentinel2Panchayat = sentinel2.filterBounds(feature.geometry());
  
  // Reducing NDVI for the current Panchayat
  var ndviStats = sentinel2Panchayat.select('NDVI').max().reduceRegion({
    reducer: ee.Reducer.max(),
    geometry: feature.geometry(),
    scale: 10,
  });
  
  // Reducing LSWI for the current Panchayat
  var lswiStats = sentinel2Panchayat.select('LSWI').max().reduceRegion({
    reducer: ee.Reducer.max(),
    geometry: feature.geometry(),
    scale: 10,
  });
    // Filtering Sentinel-1 images for the current Panchayat
  var sentinel1Panchayat = sentinel1.filterBounds(feature.geometry());
   
   
   // integrated VH
   var integratedVH = sentinel1Panchayat.max();
   
   var intvhstats = integratedVH.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: feature.geometry(),
    scale: 10,
  });
 
 
  // Reducing VH for the current Panchayat
  var maxVHstats = sentinel1Panchayat.max().reduceRegion({
    reducer: ee.Reducer.max(),
    geometry: feature.geometry(),
    scale: 10,
  });

  // Reducing FAPAR for the current Panchayat
  var faparStats = integratedFAPAR.reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: feature.geometry(),
    scale: 10,
  });

  return ee.Feature(null, {
    'Panchayat_Name': panchayatName,
    'Max_NDVI': ndviStats.get('NDVI'),
    'Max_LSWI': lswiStats.get('LSWI'),
    'Max_VH' : maxVHstats.get('VH'),
    'Integrated_FAPAR': faparStats.get('FAPAR'),
    'Integrated_VH': intvhstats.get('VH')
  });
});

print(statisticsByPanchayat);

// Export the statistics by Panchayat to Google Drive as a CSV file

// Export.table.toDrive({
//   collection: ee.FeatureCollection(statisticsByPanchayat),
//   description: 'statisticsByPanchayatF_2017',
//   folder: 'ORSAC',
//   fileFormat: 'CSV'
// });

var clippedSentinel2 = sentinel2.mean().clip(roi);
Map.centerObject(roi, 10);
Map.addLayer(clippedSentinel2, { bands: ['B4', 'B3', 'B2'], min: 0, max: 3000 }, 'Sentinel-2 Clipped');


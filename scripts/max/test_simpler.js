// Test script for Simpler device creation
// This script can be run directly to analyze error logging

const fs = require("fs");
const zlib = require("zlib");
const path = require("path");

// Test paths
const TEMPLATE_PATH =
  "/Users/Shared/Music/Google Drive/Documents/Looping Master Project/temp_simpler_donor/simpler1.adv";
const SAMPLE_PATH =
  "/Users/Shared/Music/Google Drive/Documents/CURRENT PROJECTS/Ableton Temp/2025-04-03 133201 Temp Project/Samples/Recorded/Looper 1 0002 [2025-04-03 143823].aif";
const OUTPUT_PATH =
  "/Users/Shared/Music/Google Drive/Documents/Looping Master Project/temp_simpler/Looper 1 0002 [2025-04-03 143823].adv";

// Debug function to log messages
function debug(message) {
  console.log(message);
}

// Convert ADV to XML
function advToXml(advContent) {
  debug("Converting ADV to XML...");
  debug(`Input content length: ${advContent.length}`);
  debug(`First bytes: ${advContent.slice(0, 20).toString("hex")}`);

  // Check if content is already XML
  if (advContent.toString().trim().startsWith("<?xml")) {
    debug("Content is already XML, no decompression needed");
    return advContent.toString();
  }

  // Try to decompress if it's GZIP
  try {
    const decompressed = zlib.gunzipSync(advContent);
    debug(`Decompressed size: ${decompressed.length}`);
    debug(
      `First bytes after decompression: ${decompressed
        .slice(0, 20)
        .toString("hex")}`
    );
    return decompressed.toString();
  } catch (error) {
    debug("Decompression failed, trying to parse as XML");
    try {
      return advContent.toString();
    } catch (e) {
      throw new Error("Failed to parse ADV content as XML");
    }
  }
}

// Transform XML with new sample path
function transformXml(xmlContent, samplePath) {
  debug("Transforming XML...");
  debug(`Sample path: ${samplePath}`);

  // Basic XML transformation
  let xml = xmlContent.replace(
    /<FileRef>.*?<\/FileRef>/g,
    `<FileRef>
            <FileRef>
                <RelativePathType Value="0" />
                <Path Value="${samplePath}" />
                <RelativePath Value="Samples/${path.basename(samplePath)}" />
                <Type Value="1" />
            </FileRef>
        </FileRef>`
  );

  debug("XML transformation complete");
  return xml;
}

// Convert XML back to ADV
function xmlToAdv(xmlContent) {
  debug("Converting XML to ADV...");

  // Compress the XML content
  const compressed = zlib.gzipSync(xmlContent);
  debug(`Compressed size: ${compressed.length}`);

  return compressed;
}

// Main test function
async function testSimplerCreation() {
  try {
    debug("Starting test...");
    debug(`Template path: ${TEMPLATE_PATH}`);
    debug(`Sample path: ${SAMPLE_PATH}`);
    debug(`Output path: ${OUTPUT_PATH}`);

    // Check if template file exists
    if (!fs.existsSync(TEMPLATE_PATH)) {
      throw new Error(`Template file not found: ${TEMPLATE_PATH}`);
    }

    // Read template file
    const templateContent = fs.readFileSync(TEMPLATE_PATH);
    debug(`Template file size: ${templateContent.length}`);
    debug(`First bytes: ${templateContent.slice(0, 20).toString("hex")}`);

    // Convert ADV to XML
    const xmlContent = advToXml(templateContent);
    debug("Successfully converted ADV to XML");

    // Transform XML
    const transformedXml = transformXml(xmlContent, SAMPLE_PATH);
    debug("Successfully transformed XML");

    // Convert back to ADV
    const advContent = xmlToAdv(transformedXml);
    debug("Successfully converted back to ADV");

    // Create output directory if it doesn't exist
    const outputDir = path.dirname(OUTPUT_PATH);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Write output file
    fs.writeFileSync(OUTPUT_PATH, advContent);
    debug(`Successfully wrote output file: ${OUTPUT_PATH}`);

    debug("Test completed successfully!");
  } catch (error) {
    debug("Error occurred:");
    debug(error.message);
    debug("Stack trace:");
    debug(error.stack);
    throw error;
  }
}

// Run the test
testSimplerCreation().catch((error) => {
  debug("Test failed:");
  debug(error.message);
  process.exit(1);
});

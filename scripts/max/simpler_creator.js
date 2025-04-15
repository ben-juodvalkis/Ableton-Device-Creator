// Simpler Device Creator for Max/MSP
// This script creates Ableton Simpler devices from audio samples

const maxApi = require("max-api");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

// Global state
const state = {
  templatePath:
    "/Users/Shared/Music/Google Drive/Documents/Looping Master Project/temp_simpler_donor/simpler1.adv",
  isProcessing: false,
};

// Initialize Node.js environment
maxApi.post("Simpler Creator script loading...");

// Create a new Simpler device
async function createSimplerDevice(samplePath, outputPath) {
  if (state.isProcessing) {
    maxApi.post("Already processing a device");
    return;
  }

  state.isProcessing = true;

  try {
    // Log the paths we're working with
    maxApi.post("Template path: " + state.templatePath);
    maxApi.post("Sample path: " + samplePath);
    maxApi.post("Output path: " + outputPath);

    // Check if template exists
    if (!fs.existsSync(state.templatePath)) {
      throw new Error("Template file not found: " + state.templatePath);
    }

    // Check if sample exists
    if (!fs.existsSync(samplePath)) {
      throw new Error("Sample file not found: " + samplePath);
    }

    // Create output directory if it doesn't exist
    const outputDir = path.dirname(outputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Read template file
    const templateContent = fs.readFileSync(state.templatePath);
    maxApi.post("Template file size: " + templateContent.length);
    maxApi.post("First bytes: " + templateContent.slice(0, 20).toString("hex"));

    // Convert ADV to XML
    const xmlContent = advToXml(templateContent);
    maxApi.post("Successfully converted ADV to XML");

    // Transform XML
    const transformedXml = transformXml(xmlContent, samplePath);
    maxApi.post("Successfully transformed XML");

    // Convert back to ADV
    const advContent = xmlToAdv(transformedXml);
    maxApi.post("Successfully converted back to ADV");

    // Write output file
    fs.writeFileSync(outputPath, advContent);
    maxApi.post("Successfully wrote output file: " + outputPath);

    maxApi.post("Simpler device created successfully");

    // Send a bang out of the node.script object
    maxApi.outlet("done");
  } catch (error) {
    maxApi.post("Error: " + error.message);
    if (error.stack) {
      maxApi.post("Stack trace: " + error.stack);
    }
  } finally {
    state.isProcessing = false;
  }
}

// Convert ADV to XML
function advToXml(advContent) {
  maxApi.post("Converting ADV to XML...");
  maxApi.post("Input content length: " + advContent.length);
  maxApi.post("First bytes: " + advContent.slice(0, 20).toString("hex"));

  // Check if content is already XML
  if (advContent.toString().trim().startsWith("<?xml")) {
    maxApi.post("Content is already XML, no decompression needed");
    return advContent.toString();
  }

  // Try to decompress if it's GZIP
  try {
    const decompressed = zlib.gunzipSync(advContent);
    maxApi.post("Decompressed size: " + decompressed.length);
    maxApi.post(
      "First bytes after decompression: " +
        decompressed.slice(0, 20).toString("hex")
    );
    return decompressed.toString();
  } catch (error) {
    maxApi.post("Decompression failed, trying to parse as XML");
    try {
      return advContent.toString();
    } catch (e) {
      throw new Error("Failed to parse ADV content as XML");
    }
  }
}

// Transform XML with new sample path
function transformXml(xmlContent, samplePath) {
  maxApi.post("Transforming XML...");
  maxApi.post("Sample path: " + samplePath);

  // Create the complete sample reference structure
  const sampleRefXml = `
    <MultiSampleMap>
      <SampleParts>
        <MultiSamplePart Id="0" InitUpdateAreSlicesFromOnsetsEditableAfterRead="false" HasImportedSlicePoints="true" NeedsAnalysisData="true">
          <LomId Value="0" />
          <Name Value="${path.basename(
            samplePath,
            path.extname(samplePath)
          )}" />
          <Selection Value="true" />
          <IsActive Value="true" />
          <Solo Value="false" />
          <KeyRange>
            <Min Value="0" />
            <Max Value="127" />
            <CrossfadeMin Value="0" />
            <CrossfadeMax Value="127" />
          </KeyRange>
          <VelocityRange>
            <Min Value="1" />
            <Max Value="127" />
            <CrossfadeMin Value="1" />
            <CrossfadeMax Value="127" />
          </VelocityRange>
          <SelectorRange>
            <Min Value="0" />
            <Max Value="127" />
            <CrossfadeMin Value="0" />
            <CrossfadeMax Value="127" />
          </SelectorRange>
          <RootKey Value="60" />
          <Detune Value="0" />
          <TuneScale Value="100" />
          <Panorama Value="0" />
          <Volume Value="1" />
          <Link Value="false" />
          <SampleRef>
            <FileRef>
              <RelativePathType Value="0" />
              <Path Value="${samplePath}" />
              <RelativePath Value="Samples/${path.basename(samplePath)}" />
              <Type Value="1" />
              <LivePackName Value="" />
              <LivePackId Value="" />
              <OriginalFileSize Value="0" />
              <OriginalCrc Value="0" />
            </FileRef>
            <LastModDate Value="0" />
            <SourceContext />
            <SampleUsageHint Value="0" />
            <DefaultDuration Value="0" />
            <DefaultSampleRate Value="48000" />
            <SamplesToAutoWarp Value="1" />
          </SampleRef>
        </MultiSamplePart>
      </SampleParts>
      <LoadInRam Value="false" />
      <LayerCrossfade Value="0" />
      <SourceContext />
      <RoundRobin Value="false" />
      <RoundRobinMode Value="0" />
      <RoundRobinResetPeriod Value="0" />
      <RoundRobinRandomSeed Value="2138069469" />
    </MultiSampleMap>`;

  // Replace the existing MultiSampleMap with our new one
  let xml = xmlContent.replace(
    /<MultiSampleMap>.*?<\/MultiSampleMap>/s,
    sampleRefXml
  );

  maxApi.post("XML transformation complete");
  return xml;
}

// Convert XML back to ADV
function xmlToAdv(xmlContent) {
  maxApi.post("Converting XML to ADV...");

  // Compress the XML content
  const compressed = zlib.gzipSync(xmlContent);
  maxApi.post("Compressed size: " + compressed.length);

  return compressed;
}

// Register handlers for Max messages
maxApi.addHandler("create", async (samplePath, outputPath) => {
  maxApi.post("Starting Simpler device creation...");
  await createSimplerDevice(samplePath, outputPath);
});

// Export functions for testing
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    createSimplerDevice: createSimplerDevice,
    transformXml: transformXml,
    advToXml: advToXml,
    xmlToAdv: xmlToAdv,
  };
}

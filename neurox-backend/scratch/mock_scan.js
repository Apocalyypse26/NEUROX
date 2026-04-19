import "dotenv/config";
import fs from "fs";
import path from "path";
import { processScanJob } from "../src/queue/scanQueue.js";

const imagePath = "C:\\Users\\doesi\\.gemini\\antigravity\\brain\\15698ac0-0690-474a-aa6a-723ddb32b42d\\scam_token_logo_1776630826973.png";

async function runMockScan() {
  console.log("🚀 Starting NEUROX Mock Scan (token-optimized)...\n");

  if (!fs.existsSync(imagePath)) {
    console.error("❌ Test image not found at", imagePath);
    process.exit(1);
  }

  const imageBuffer = fs.readFileSync(imagePath);
  const stats = fs.statSync(imagePath);

  const start = Date.now();

  try {
    const result = await processScanJob({
      data: {
        imageBase64: imageBuffer.toString("base64"),
        mimeType: "image/png",
        originalSize: stats.size,
        inputType: "image",
        inputUrl: null,
        extraBuffersBase64: [],
      },
    });

    const elapsed = Date.now() - start;

    console.log("\n═══════════════════════════════════════════");
    console.log("✅ SCAN COMPLETED (" + elapsed + "ms)");
    console.log("═══════════════════════════════════════════\n");
    console.log(JSON.stringify(result, null, 2));

    const resultPath = path.join(process.cwd(), "scratch", "mock_scan_result.json");
    fs.mkdirSync(path.dirname(resultPath), { recursive: true });
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));

    process.exit(0);
  } catch (error) {
    console.error("\n❌ SCAN FAILED:", error);
    process.exit(1);
  }
}

runMockScan();

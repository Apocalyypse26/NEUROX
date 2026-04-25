// ═══════════════════════════════════════════════════════
// Compression Middleware — Brotli + Gzip + Deflate
// ═══════════════════════════════════════════════════════
import { createBrotliCompress, createGzip, createDeflate } from "zlib";
import { Transform } from "stream";
import accepts from "accepts";

const BROTLI_QUALITY = 4;
const GZIP_LEVEL = 6;

function createCompressor(method, level = GZIP_LEVEL) {
  const compressors = {
    br: () => createBrotliCompress({ params: { [0x1e]: BROTLI_QUALITY } }),
    gzip: () => createGzip({ level }),
    deflate: () => createDeflate({ level }),
  };
  return compressors[method]?.() || compressors.gzip();
}

function shouldCompress(req, res) {
  const contentType = res.getHeader("Content-Type");
  if (!contentType || !contentType.includes("json") && !contentType.includes("text")) {
    return false;
  }
  const length = res.getHeader("Content-Length");
  if (length && parseInt(length, 10) < 2048) {
    return false;
  }
  return true;
}

export function compressMiddleware(req, res, next) {
  const accept = accepts(req);
  const encoding = accept.encoding(["br", "gzip", "deflate"], "gzip");

  res.shouldCompress = shouldCompress.bind(null, req, res);

  const originalEnd = res.end;
  res.end = function (chunk, encoding, cb) {
    originalEnd.call(this, chunk, encoding, cb);

    if (chunk && res.shouldCompress() && !res.getHeader("Content-Encoding")) {
      const compressor = createCompressor(encoding);
      res.setHeader("Content-Encoding", encoding);

      const stream = new Transform({
        transform(chunk, encoding, callback) {
          compressor.write(chunk, encoding);
          callback();
        }
      });

      compressor.on("data", (chunk) => res.write(chunk));
      compressor.on("end", () => res.end());
      compressor.on("error", () => {});

      stream.end(chunk);
    }
  };

  next();
}
// Pre-compress text and geometry payloads so Python can serve them with
// Content-Encoding: gzip. Original bytes remain for Range/non-gzip clients.
// Intentionally no external dependencies; run after Vite emits dist/.
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { gzipSync, constants } from 'node:zlib';

const root = new URL('../dist/', import.meta.url);
const eligible = new Set(['.html', '.js', '.css', '.gltf', '.bin']);
let before = 0, after = 0, count = 0;

async function visit(dir) {
  for (const item of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, item.name);
    if (item.isDirectory()) {
      await visit(path);
    } else if (item.isFile() && eligible.has(extname(item.name))) {
      const source = await readFile(path);
      if (source.length < 1024) continue;
      const compressed = gzipSync(source, { level: constants.Z_BEST_COMPRESSION });
      if (compressed.length >= source.length * .97) continue;
      await writeFile(path + '.gz', compressed);
      before += source.length;
      after += compressed.length;
      count++;
    }
  }
}
await visit(root.pathname);
console.log('Precompressed '+count+' files: '+before+' -> '+after+' bytes ('+(100*(1-after/before)).toFixed(1)+'% less transfer).');

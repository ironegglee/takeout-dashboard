const fs = require('fs');

const data = JSON.parse(fs.readFileSync('dashboard/data.json', 'utf8'));
const srcHtml = fs.readFileSync('dashboard/index.html', 'utf8');

// Extract version
const verMatch = srcHtml.match(/<meta name="version" content="([^"]+)"/);
const CURRENT_VERSION = verMatch ? verMatch[1] : 'v2.9.0';
console.log('Version:', CURRENT_VERSION);

// Extract date range
const allDates = new Set();
for (const arrKey of ['mp_daily', 'mt_daily']) {
  for (const d of data[arrKey] || []) {
    if (d.date) allDates.add(d.date);
  }
}
let dateStart = '2026-05-01', dateEnd = '2026-06-02';
if (allDates.size > 0) {
  const sorted = Array.from(allDates).sort();
  dateStart = sorted[0];
  dateEnd = sorted[sorted.length - 1];
  console.log('Date range:', dateStart, '~', dateEnd);
}

// Find markers
const MARKER_START = 'let REAL_MP_SUMMARY = null;';
const MARKER_END = 'const STORE_MP = [';
const idxStart = srcHtml.indexOf(MARKER_START);
const idxEnd = srcHtml.indexOf(MARKER_END, idxStart);
if (idxStart < 0 || idxEnd < 0) {
  console.error('ERROR: markers not found');
  process.exit(1);
}

const newBlock = MARKER_START + `\n\n/* ================================================================\n   嵌入真实数据（由 embed_data.py 自动生成）\n   绕过 file:// 协议下 fetch() 的浏览器 CORS 限制\n================================================================ */\nconst EMBEDDED_DATA = ${JSON.stringify(data)};\nconst EMBEDDED_DATE_START = "${dateStart}";\nconst EMBEDDED_DATE_END = "${dateEnd}";\n   // 真实汇总\n\n`;

let html = srcHtml.slice(0, idxStart) + newBlock + srcHtml.slice(idxEnd);

// Update build-time and version
const now = new Date();
const buildTime = now.toISOString().replace('Z', '+08:00');
const verStr = `${CURRENT_VERSION}@${now.toISOString().slice(0,10).replace(/-/g,'')}`;

html = html.replace(/<meta name="build-time" content="[^"]*"/, `<meta name="build-time" content="${buildTime}"`);
html = html.replace(/var VER\s*=\s*"[^"]*"/, `var VER = "${verStr}"`);
html = html.replace(/<meta name="version" content="[^"]*"/, `<meta name="version" content="${CURRENT_VERSION}"`);

fs.writeFileSync('index.html', html, 'utf8');
console.log('index.html written:', (html.length/1024).toFixed(0), 'KB');
console.log('Done!');

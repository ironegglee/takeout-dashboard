const fs = require('fs');
const h = fs.readFileSync('index.html', 'utf8');
console.log('leader select:', h.includes('id="gf-leader"'));
console.log('onAreaMgrChange:', h.includes('function onAreaMgrChange'));
console.log('gfState.leader:', h.includes("leader:'all'"));
console.log('EMBEDDED_DATE_END:', (h.match(/EMBEDDED_DATE_END = "([^"]+)"/)||[])[1]);
console.log('build-time:', (h.match(/<meta name="build-time" content="([^"]+)"/)||[])[1]);

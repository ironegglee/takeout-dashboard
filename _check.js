const fs = require('fs');
const h = fs.readFileSync('dashboard/index.html', 'utf8');
console.log('leader select:', h.includes('id="gf-leader"'));
console.log('onAreaMgrChange:', h.includes('function onAreaMgrChange'));
console.log('gfState.leader:', h.includes("leader:'all'"));

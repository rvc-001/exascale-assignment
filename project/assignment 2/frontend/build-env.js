const fs = require("fs");

const apiBase = process.env.API_BASE || "";
const content = `window.ENV = window.ENV || {};\nwindow.ENV.API_BASE = ${JSON.stringify(apiBase)};\n`;

fs.writeFileSync("env.js", content);
console.log(`Wrote env.js with API_BASE=${apiBase || "(empty)"}`);

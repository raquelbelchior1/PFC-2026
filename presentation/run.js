/**
 * run.js — Executor do build da apresentação PFC
 * Uso: node run.js
 */
"use strict";
const { execSync } = require("child_process");
const path = require("path");

console.log("\n╔══════════════════════════════════════════════════╗");
console.log("║  Gerador de Apresentação PFC — Caixão de Areia  ║");
console.log("║  Verificação de Curso (VC) · AMAN 2026          ║");
console.log("╚══════════════════════════════════════════════════╝\n");

try {
  execSync("node build.js", { cwd: __dirname, stdio: "inherit" });
} catch (e) {
  process.exit(1);
}

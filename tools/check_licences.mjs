#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// Licence check for the npm workspaces (milestone M6).
//
// Reads package-lock.json (lockfile v3 records each package's licence) and
//   - fails when a package has no licence or an unknown/unapproved one;
//   - requires permissive licences for packages that ship at runtime;
//   - allows a short list of weak-copyleft or data licences for dev tools only.
// Prints a summary per licence. `--list` prints every package.

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// Permissive licences: allowed everywhere, including the MIT EngineeringUI package.
export const PERMISSIVE = new Set([
  "MIT",
  "MIT-0",
  "ISC",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "Apache-2.0",
  "0BSD",
  "BlueOak-1.0.0",
  "CC0-1.0",
  "Unlicense",
  "Python-2.0",
  "Zlib",
]);
// Allowed only for development tools that are never shipped or bundled.
export const DEV_ONLY = new Set(["MPL-2.0", "CC-BY-4.0", "CC-BY-3.0"]);

/** Evaluates a simple SPDX expression (OR, AND, parentheses) against an allow-list. */
export function allowed(expression, allow) {
  const tokens = expression.replace(/[()]/g, " $& ").trim().split(/\s+/);
  let position = 0;
  function primary() {
    const token = tokens[position++];
    if (token === "(") {
      const value = or();
      position++;
      return value;
    }
    return allow.has(token?.replace(/\+$/, ""));
  }
  function and() {
    let value = primary();
    while (tokens[position] === "AND") {
      position++;
      value = primary() && value;
    }
    return value;
  }
  function or() {
    let value = and();
    while (tokens[position] === "OR") {
      position++;
      value = and() || value;
    }
    return value;
  }
  return or();
}

export function checkLock(lock) {
  const devAllow = new Set([...PERMISSIVE, ...DEV_ONLY]);
  const summary = new Map();
  const problems = [];
  const packages = [];
  for (const [path, info] of Object.entries(lock.packages ?? {})) {
    if (!path.includes("node_modules/") || info.link) continue;
    const name = path.slice(path.lastIndexOf("node_modules/") + "node_modules/".length);
    const licence = typeof info.license === "string" ? info.license.trim() : "";
    const scope = info.dev ? "dev" : "runtime";
    packages.push({ name, version: info.version, licence: licence || "(none)", scope });
    const key = `${licence || "(none)"}`;
    const entry = summary.get(key) ?? { runtime: 0, dev: 0 };
    entry[scope]++;
    summary.set(key, entry);
    if (!licence) problems.push(`${name}@${info.version}: no licence recorded`);
    else if (scope === "runtime" && !allowed(licence, PERMISSIVE))
      problems.push(`${name}@${info.version}: runtime dependency with non-permissive licence "${licence}"`);
    else if (scope === "dev" && !allowed(licence, devAllow))
      problems.push(`${name}@${info.version}: unapproved licence "${licence}"`);
  }
  return { summary, problems, packages };
}

function main() {
  const lock = JSON.parse(readFileSync(join(repoRoot, "package-lock.json"), "utf8"));
  const { summary, problems, packages } = checkLock(lock);
  if (process.argv.includes("--list")) {
    for (const item of packages.sort((a, b) => a.name.localeCompare(b.name)))
      console.log(`${item.scope.padEnd(7)} ${item.licence.padEnd(28)} ${item.name}@${item.version}`);
  }
  console.log(`Licences of ${packages.length} installed npm packages (runtime / dev):`);
  for (const [licence, count] of [...summary].sort((a, b) => b[1].runtime + b[1].dev - (a[1].runtime + a[1].dev)))
    console.log(`  ${licence.padEnd(32)} ${String(count.runtime).padStart(4)} / ${String(count.dev).padStart(4)}`);
  if (problems.length) {
    console.error(`Licence check failed (${problems.length} problem(s)):`);
    for (const problem of problems) console.error(`  ${problem}`);
    process.exit(1);
  }
  console.log("Licence check passed.");
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();

#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// Dependency-boundary check for the npm workspaces (milestone M6).
//
// EngineeringUI (packages/engineering-ui, MIT) must stay extractable:
//   1. relative imports never leave the package directory;
//   2. bare imports name only declared dependencies, and never application
//      code (gelectrical, GEstimator) or Tauri;
//   3. library sources import only peer/runtime dependencies;
//   4. the root, theme, icons and composables entries never reach Quasar,
//      directly or through relative imports.
//
// Usage: node tools/check_boundaries.mjs [--package <dir>]
// Exits 1 and lists every violation when the boundary is broken.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { builtinModules } from "node:module";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SCANNED_DIRS = ["src", "stories", "tests", ".storybook"];
const SCANNED_EXTENSIONS = new Set([".ts", ".mts", ".js", ".mjs", ".vue", ".css", ".mdx"]);
const SKIPPED_DIRS = new Set(["node_modules", "dist", "storybook-static", "coverage"]);
const QUASAR_FREE_ENTRIES = ["src/index.ts", "src/theme/index.ts", "src/icons/index.ts", "src/composables/index.ts"];
const FORBIDDEN = [
  { test: (name) => /gelectrical/i.test(name), reason: "application code (GElectrical)" },
  { test: (name) => /gestimator/i.test(name), reason: "application code (GEstimator)" },
  { test: (name) => name.startsWith("@tauri-apps/"), reason: "Tauri API (inject a native adapter instead)" },
];
const RESOLVE_EXTENSIONS = ["", ".ts", ".mts", ".js", ".mjs", ".vue", "/index.ts", "/index.js"];

function walk(dir, files = []) {
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir)) {
    if (SKIPPED_DIRS.has(entry)) continue;
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) walk(path, files);
    else if (SCANNED_EXTENSIONS.has(extname(entry))) files.push(path);
  }
  return files;
}

/** Returns import specifiers with their line numbers. */
export function extractSpecifiers(source, extension) {
  const found = [];
  const patterns =
    extension === ".css"
      ? [/@import\s+(?:url\(\s*)?["']?([^"')\s;]+)["']?/g]
      : [
          /\bimport\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?["']([^"']+)["']/g,
          /\bexport\s+(?:type\s+)?(?:\*(?:\s+as\s+\w+)?|\{[^}]*\})\s+from\s+["']([^"']+)["']/g,
          /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g,
          /\brequire\s*\(\s*["']([^"']+)["']\s*\)/g,
          /@import\s+(?:url\(\s*)?["']([^"')]+)["']/g,
        ];
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      const line = source.slice(0, match.index).split("\n").length;
      found.push({ specifier: match[1], line });
    }
  }
  return found;
}

function packageName(specifier) {
  const parts = specifier.split("/");
  return specifier.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
}

function resolveRelative(fromFile, specifier) {
  const base = resolve(dirname(fromFile), specifier.split("?")[0]);
  for (const suffix of RESOLVE_EXTENSIONS) {
    const candidate = base + suffix;
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return base;
}

export function checkPackage(packageDir) {
  const manifest = JSON.parse(readFileSync(join(packageDir, "package.json"), "utf8"));
  const runtime = new Set([
    ...Object.keys(manifest.peerDependencies ?? {}),
    ...Object.keys(manifest.dependencies ?? {}),
  ]);
  const declared = new Set([...runtime, ...Object.keys(manifest.devDependencies ?? {})]);
  const builtins = new Set(builtinModules.flatMap((name) => [name, `node:${name}`]));
  const violations = [];
  const graph = new Map();

  const files = [
    ...SCANNED_DIRS.flatMap((dir) => walk(join(packageDir, dir))),
    ...readdirSync(packageDir)
      .filter((entry) => /\.(c|m)?[jt]s$/.test(entry))
      .map((entry) => join(packageDir, entry)),
  ];

  for (const file of files) {
    const rel = relative(packageDir, file).split(sep).join("/");
    const inSource = rel.startsWith("src/");
    const edges = [];
    graph.set(file, edges);
    for (const { specifier, line } of extractSpecifiers(readFileSync(file, "utf8"), extname(file))) {
      const where = `${rel}:${line}`;
      if (/^[a-z]+:\/\//i.test(specifier) || specifier.startsWith("data:")) {
        violations.push(`${where}: remote import "${specifier}"`);
        continue;
      }
      if (specifier.startsWith(".")) {
        const target = resolveRelative(file, specifier);
        const outside = relative(packageDir, target).startsWith("..");
        if (outside) violations.push(`${where}: "${specifier}" leaves the package directory`);
        else if (inSource && relative(join(packageDir, "src"), target).startsWith(".."))
          violations.push(`${where}: library source imports "${specifier}" outside src/`);
        else edges.push({ target, specifier });
        continue;
      }
      if (specifier.startsWith("/") || /^[a-zA-Z]:[\\/]/.test(specifier)) {
        violations.push(`${where}: absolute import "${specifier}"`);
        continue;
      }
      if (builtins.has(specifier) || builtins.has(packageName(specifier))) {
        if (inSource) violations.push(`${where}: library source imports Node built-in "${specifier}"`);
        continue;
      }
      const name = packageName(specifier);
      const forbidden = FORBIDDEN.find((rule) => rule.test(name));
      if (forbidden) {
        violations.push(`${where}: imports ${forbidden.reason} via "${specifier}"`);
        continue;
      }
      if (name === manifest.name) {
        violations.push(`${where}: self-import "${specifier}" (use a relative import)`);
        continue;
      }
      if (inSource && !runtime.has(name)) {
        violations.push(`${where}: "${name}" is not a peer or runtime dependency of ${manifest.name}`);
        continue;
      }
      if (!declared.has(name)) violations.push(`${where}: "${name}" is not declared in package.json`);
      edges.push({ bare: name, specifier });
    }
  }

  // Quasar stays optional: these entries must not reach it.
  for (const entry of QUASAR_FREE_ENTRIES) {
    const start = join(packageDir, entry);
    if (!graph.has(start)) continue;
    const seen = new Set();
    const stack = [[start, [relative(packageDir, start)]]];
    while (stack.length) {
      const [file, path] = stack.pop();
      if (seen.has(file)) continue;
      seen.add(file);
      for (const edge of graph.get(file) ?? []) {
        if (edge.bare === "quasar") violations.push(`${entry}: reaches Quasar via ${path.join(" -> ")}`);
        if (edge.target && graph.has(edge.target))
          stack.push([edge.target, [...path, relative(packageDir, edge.target).split(sep).join("/")]]);
      }
    }
  }

  return { files: files.length, violations: [...new Set(violations)] };
}

function main() {
  const args = process.argv.slice(2);
  const index = args.indexOf("--package");
  const packageDir = resolve(index >= 0 ? args[index + 1] : join(repoRoot, "packages", "engineering-ui"));
  const { files, violations } = checkPackage(packageDir);
  const label = relative(repoRoot, packageDir) || packageDir;
  if (violations.length) {
    console.error(`Boundary check failed for ${label} (${violations.length} violation(s)):`);
    for (const violation of violations) console.error(`  ${violation}`);
    process.exit(1);
  }
  console.log(`Boundary check passed for ${label}: ${files} files, no imports outside the package boundary.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();

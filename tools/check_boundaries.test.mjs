// SPDX-License-Identifier: GPL-3.0-or-later
// Tests for the dependency-boundary check: it passes on a clean package and
// reports each kind of violation.
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, test } from "node:test";
import { checkPackage, extractSpecifiers } from "./check_boundaries.mjs";

const root = mkdtempSync(join(tmpdir(), "eui-boundary-"));
after(() => rmSync(root, { recursive: true, force: true }));

function makePackage(name, files) {
  const dir = join(root, name);
  const manifest = {
    name: "@kavilgroup/engineering-ui",
    peerDependencies: { vue: "^3.5.0", quasar: "^2.36.0" },
    devDependencies: { vitest: "5.1.2" },
  };
  for (const [path, content] of Object.entries({ "package.json": JSON.stringify(manifest), ...files })) {
    mkdirSync(dirname(join(dir, path)), { recursive: true });
    writeFileSync(join(dir, path), content);
  }
  return dir;
}

test("extracts static, dynamic, re-export and CSS imports", () => {
  const ts = `import a from "vue";\nimport type { B } from './b';\nexport * from "./c";\nconst d = import("./d");\nimport "./e.css";`;
  assert.deepEqual(
    extractSpecifiers(ts, ".ts").map((item) => item.specifier),
    ["vue", "./b", "./e.css", "./c", "./d"],
  );
  assert.deepEqual(
    extractSpecifiers('@import "./tokens.css";\n@import url(base.css);', ".css").map((item) => item.specifier),
    ["./tokens.css", "base.css"],
  );
});

test("passes a package that stays inside its boundary", () => {
  const dir = makePackage("clean", {
    "src/index.ts": 'export * from "./theme/index";',
    "src/theme/index.ts": 'import { ref } from "vue";\nexport const x = ref(1);',
    "src/controls/index.ts": 'import { QInput } from "quasar";\nexport { QInput };',
    "tests/a.spec.ts": 'import { test } from "vitest";\nimport "../src/index";',
  });
  assert.deepEqual(checkPackage(dir).violations, []);
});

test("reports application, Tauri, undeclared, escaping and Quasar-leaking imports", () => {
  const dir = makePackage("dirty", {
    "src/index.ts": 'export * from "./theme/index";',
    "src/theme/index.ts":
      'import "./helper";\nimport x from "../../../modern/src/App.vue";\nimport y from "../../stories/a.stories";',
    "src/theme/helper.ts": 'import { Dark } from "quasar";',
    "src/controls/index.ts":
      'import { invoke } from "@tauri-apps/api/core";\nimport lodash from "lodash";\nimport { test } from "vitest";\nimport fs from "node:fs";\nimport self from "@kavilgroup/engineering-ui/theme";',
    "stories/a.stories.ts": 'import x from "gelectrical-modern";',
  });
  const text = checkPackage(dir).violations.join("\n");
  assert.match(text, /src\/theme\/index\.ts:2: "\.\.\/\.\.\/\.\.\/modern\/src\/App\.vue" leaves the package directory/);
  assert.match(text, /src\/theme\/index\.ts:3: library source imports "\.\.\/\.\.\/stories\/a\.stories" outside src\//);
  assert.match(text, /Tauri API/);
  assert.match(text, /"lodash" is not a peer or runtime dependency/);
  assert.match(text, /"vitest" is not a peer or runtime dependency/);
  assert.match(text, /Node built-in "node:fs"/);
  assert.match(text, /self-import/);
  assert.match(text, /application code \(GElectrical\)/);
  assert.match(
    text,
    /src\/index\.ts: reaches Quasar via src\/index\.ts -> src\/theme\/index\.ts -> src\/theme\/helper\.ts/,
  );
});

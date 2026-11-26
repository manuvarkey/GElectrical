// SPDX-License-Identifier: GPL-3.0-or-later
import assert from "node:assert/strict";
import { test } from "node:test";
import { allowed, checkLock, PERMISSIVE } from "./check_licences.mjs";

test("evaluates SPDX expressions", () => {
  assert.equal(allowed("MIT", PERMISSIVE), true);
  assert.equal(allowed("(MIT OR GPL-3.0)", PERMISSIVE), true);
  assert.equal(allowed("MIT AND GPL-3.0", PERMISSIVE), false);
  assert.equal(allowed("(MIT OR Apache-2.0) AND BSD-3-Clause", PERMISSIVE), true);
  assert.equal(allowed("GPL-3.0-or-later", PERMISSIVE), false);
});

test("separates runtime and dev policies", () => {
  const { problems } = checkLock({
    packages: {
      "": { name: "root" },
      "node_modules/vue": { version: "1", license: "MIT" },
      "node_modules/lightningcss": { version: "1", license: "MPL-2.0", dev: true },
      "node_modules/copyleft": { version: "1", license: "MPL-2.0" },
      "node_modules/nolicence": { version: "1", dev: true },
      "node_modules/gpl-tool": { version: "1", license: "GPL-3.0", dev: true },
      "node_modules/@kavilgroup/engineering-ui": { link: true, resolved: "packages/engineering-ui" },
    },
  });
  assert.deepEqual(problems, [
    'copyleft@1: runtime dependency with non-permissive licence "MPL-2.0"',
    "nolicence@1: no licence recorded",
    'gpl-tool@1: unapproved licence "GPL-3.0"',
  ]);
});

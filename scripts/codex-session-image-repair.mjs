#!/usr/bin/env node

import { createReadStream, createWriteStream, constants, copyFileSync, existsSync, mkdirSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import { createInterface } from "node:readline";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";

const pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";
const args = process.argv.slice(2);
const apply = args.includes("--apply");
const allImages = args.includes("--all-images");
const files = args.filter((arg) => !arg.startsWith("--"));
const runStamp = new Date().toISOString().replace(/[:.]/g, "-");
const backupDir = join(process.env.HOME, "Documents", "Codex Session Backups", runStamp);

if (!files.length) {
  console.error("Usage: codex-session-image-repair.mjs [--apply] [--all-images] SESSION.jsonl [...]");
  process.exit(2);
}
function replaceImages(value, stats, assetDir) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) replaceImages(item, stats, assetDir);
    return;
  }
  for (const [key, child] of Object.entries(value)) {
    if ((key === "image_url" || key === "url") && typeof child === "string" && child.startsWith("data:image/") && child !== pixel) {
      stats.images++;
      stats.imageBytes += Buffer.byteLength(child);
      const match = child.match(/^data:image\/(png|jpe?g|webp|gif);base64,(.+)$/s);
      if (assetDir && match) {
        const bytes = Buffer.from(match[2], "base64");
        const hash = createHash("sha256").update(bytes).digest("hex");
        const ext = match[1].replace("jpeg", "jpg");
        const asset = join(assetDir, `${hash}.${ext}`);
        mkdirSync(assetDir, { recursive: true });
        if (!existsSync(asset)) writeFileSync(asset, bytes, { flag: "wx" });
        stats.assets.add(asset);
      }
      value[key] = pixel;
    } else {
      replaceImages(child, stats, assetDir);
    }
  }
}

function isOpen(file) {
  try {
    const output = execFileSync("lsof", [file], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    return output.trim().split("\n").length > 1;
  } catch {
    return false;
  }
}

async function processFile(file) {
  const before = statSync(file).size;
  if (apply && isOpen(file)) throw new Error(`refusing to modify open session: ${file}`);
  const stats = { images: 0, imageBytes: 0, lines: 0, compacted: 0, assets: new Set() };
  const threadId = basename(file).match(/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/i)?.[0] ?? basename(file, ".jsonl");
  const assetDir = apply && allImages ? join(process.env.HOME, "Documents", "Codex Session Images", threadId) : null;
  const temp = `${file}.repair-${process.pid}`;
  const output = apply ? createWriteStream(temp, { encoding: "utf8" }) : null;
  const reader = createInterface({ input: createReadStream(file), crlfDelay: Infinity });

  try {
    for await (const line of reader) {
      stats.lines++;
      let next = line;
      if (allImages) {
        const record = JSON.parse(line);
        if (record.type === "compacted") stats.compacted++;
        replaceImages(record, stats, assetDir);
        next = JSON.stringify(record);
      } else if (line.includes('"type":"compacted"')) {
        const record = JSON.parse(line);
        if (record.type === "compacted") {
          stats.compacted++;
          replaceImages(record, stats, null);
          next = JSON.stringify(record);
        }
      }
      if (output && !output.write(`${next}\n`)) await new Promise((resolve) => output.once("drain", resolve));
    }
    if (output) await new Promise((resolve, reject) => output.end((error) => error ? reject(error) : resolve()));
  } catch (error) {
    output?.destroy();
    try { unlinkSync(temp); } catch {}
    throw error;
  }

  const projected = before - stats.imageBytes + stats.images * Buffer.byteLength(pixel);
  const resultStats = { images: stats.images, imageBytes: stats.imageBytes, lines: stats.lines, compacted: stats.compacted, assets: stats.assets.size };
  if (!apply) return { file, before, projected, ...resultStats };
  if (stats.images === 0) {
    unlinkSync(temp);
    return { file, before, after: before, unchanged: true, ...resultStats };
  }

  mkdirSync(backupDir, { recursive: true });
  const backup = join(backupDir, basename(file));
  copyFileSync(file, backup, constants.COPYFILE_FICLONE);
  renameSync(temp, file);
  const after = statSync(file).size;
  return { file, backup, assetDir, before, after, ...resultStats };
}

for (const file of files) {
  try {
    console.log(JSON.stringify({ mode: apply ? "apply" : "dry-run", scope: allImages ? "replayed-images" : "compacted", ...await processFile(file) }));
  } catch (error) {
    console.error(JSON.stringify({ file, error: error.message }));
    process.exitCode = 1;
  }
}

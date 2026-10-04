import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // The page imports ../agents/registry.json (repo root), so Turbopack's root is the repo root.
  turbopack: { root: path.join(here, "..") },
};

export default nextConfig;

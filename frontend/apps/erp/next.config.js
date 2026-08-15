/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@kathwada/ui", "@kathwada/api-client"],
  // Static export — every page in this app is already a client component
  // that fetches its data from the API after load (see docs/architecture.md
  // for the constraint this places on future pages: no server-only logic).
  output: "export",
  images: { unoptimized: true },
};

module.exports = nextConfig;

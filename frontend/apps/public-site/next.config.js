/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@kathwada/ui", "@kathwada/api-client"],
  // Static export — this app is deployed as a Render Static Site (a plain
  // CDN of pre-built HTML/CSS/JS), not a Node server. See docs/deployment.md.
  output: "export",
  // The static-export build can't run Next's Image Optimization server
  // (there's no server at runtime). Images are served as-is, unresized.
  images: { unoptimized: true },
};

module.exports = nextConfig;

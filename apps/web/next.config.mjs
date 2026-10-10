/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  output: process.env.NEXT_OUTPUT_MODE === "standalone" ? "standalone" : "export"
};

export default nextConfig;

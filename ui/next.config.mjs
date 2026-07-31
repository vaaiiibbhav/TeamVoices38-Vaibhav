/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  // page.tsx's ChatKit widget isn't wired to this backend (see CLAUDE.md) --
  // send bare-root visitors to the working demo page instead.
  async redirects() {
    return [
      {
        source: "/",
        destination: "/dev-chat",
        permanent: false,
      },
    ];
  },
  // Proxy /chat requests to the backend server
  async rewrites() {
    return [
      {
        source: "/chat",
        destination: "http://127.0.0.1:8000/chat",
      },
      {
        source: "/chatkit",
        destination: "http://127.0.0.1:8000/chatkit",
      },
      {
        source: "/chatkit/:path*",
        destination: "http://127.0.0.1:8000/chatkit/:path*",
      },
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;

declare namespace Cloudflare {
  interface Env {
    FILES: R2Bucket;
  }
}

declare module '*.md?raw' {
  const value: string;
  export default value;
}

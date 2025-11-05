import { NextResponse } from "next/server";

const GATEWAY = process.env.APP_API_GATEWAY_URL || "";

function joinUrl(base: string, path: string) {
  if (!base) return path;
  if (base.endsWith("/") && path.startsWith("/")) return base + path.substring(1);
  if (!base.endsWith("/") && !path.startsWith("/")) return base + "/" + path;
  return base + path;
}

async function proxy(request: Request, context: { params?: Promise<{ path?: string[] }> | { path?: string[] } }) {
  // In Next 16 the `params` argument can be a Promise and must be awaited
  // before dereferencing. Accept either a promise or an object for
  // compatibility with older runtimes.
  const resolvedParams = context?.params ? await context.params : undefined;
  const pathParts = resolvedParams?.path || [];
  const path = pathParts.join("/") || "";
  const url = joinUrl(GATEWAY, path) + new URL(request.url).search;

  const headers: Record<string, string> = {};
  request.headers.forEach((v, k) => {
    // Avoid sending host header to the gateway
    if (k.toLowerCase() === "host") return;
    headers[k] = v;
  });

  const init: RequestInit = {
    method: request.method,
    headers,
    // Body will be null for GET/HEAD/OPTIONS
    body: ["GET", "HEAD", "OPTIONS"].includes(request.method) ? undefined : await request.text(),
    redirect: "follow",
  };

  const res = await fetch(url, init);
  const body = await res.arrayBuffer();
  const responseHeaders: Record<string, string> = {};
  res.headers.forEach((v, k) => (responseHeaders[k] = v));

  return new Response(body, {
    status: res.status,
    headers: responseHeaders,
  });
}

export async function GET(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

export async function POST(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

export async function PUT(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

export async function DELETE(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

export async function PATCH(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

export async function OPTIONS(request: Request, context: { params?: any }) {
  return proxy(request, context);
}

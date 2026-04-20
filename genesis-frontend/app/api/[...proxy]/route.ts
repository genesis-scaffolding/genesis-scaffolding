import { NextRequest, NextResponse } from 'next/server';
import { apiFetch } from '@/lib/api-client';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ proxy: string[] }> } // Type as Promise
) {
  // Unwrap the params
  const { proxy } = await params;
  const path = proxy.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const endpoint = `/${path}${searchParams ? `?${searchParams}` : ''}`;

  try {
    const response = await apiFetch(endpoint, { method: 'GET', cache: "no-store" });
    // Handling SSE (Server-Sent Events)
    const contentType = response.headers.get('content-type');

    if (contentType?.includes('text/event-stream')) {
      // Create a stream passthrough. 
      // We pass the original backend body directly to the frontend.
      return new NextResponse(response.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          // Important for Vercel/Proxies to not buffer the stream
          'X-Accel-Buffering': 'no',
        },
      });
    }

    // Check if the response is successful
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      return NextResponse.json(errorBody, { status: response.status });
    }

    // If it's a file download, return the raw body as a blob/stream
    if (contentType && !contentType.includes('application/json')) {
      const blob = await response.blob();
      return new NextResponse(blob, {
        status: 200,
        headers: {
          'Content-Type': contentType,
          'Content-Disposition': response.headers.get('content-disposition') || 'attachment',
        },
      });
    }

    // Otherwise, return JSON
    const data = await response.json();
    return NextResponse.json(data, { status: 200 });

  } catch (error) {
    console.error('[Proxy GET Error]:', error);
    return NextResponse.json({ error: 'Proxy request failed' }, { status: 500 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ proxy: string[] }> } // Type as Promise
) {
  const { proxy } = await params;
  const path = proxy.join('/');
  const body = await request.text();

  try {
    const response = await apiFetch(`/${path}`, {
      method: 'POST',
      body,
      headers: {
        'Content-Type': request.headers.get('Content-Type') || 'application/json',
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({ error: 'Proxy request failed' }, { status: 500 });
  }
}

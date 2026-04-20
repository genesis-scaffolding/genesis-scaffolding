import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { refreshAccessToken } from '@/lib/auth';

// Paths that don't require authentication
const PUBLIC_PATHS = ['/login', '/register'];

// Paths that authenticated users shouldn't access
const AUTH_PATHS = ['/login', '/register'];

function isTokenExpired(token: string): boolean {
  try {
    // JWT tokens are base64 encoded: header.payload.signature
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload));

    const now = Date.now();
    const exp = decoded.exp * 1000;
    const isExpired = exp < now;

    console.log('[Token Check]', {
      exp: new Date(exp).toISOString(),
      now: new Date(now).toISOString(),
      isExpired,
      timeUntilExpiry: Math.round((exp - now) / 1000) + 's'
    });

    return isExpired;
  } catch (error) {
    console.log('[Token Check] Invalid token format:', error);
    return true;
  }
}

export async function proxy(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;
  const refreshToken = request.cookies.get('refresh_token')?.value;
  const { pathname } = request.nextUrl;

  console.log('='.repeat(80));
  console.log('[Middleware] REQUEST:', {
    pathname,
    method: request.method,
    hasAccessToken: !!accessToken,
    hasRefreshToken: !!refreshToken,
    accessTokenPreview: accessToken ? accessToken.substring(0, 20) + '...' : null,
    url: request.url,
  });

  const tokenExpired = accessToken ? isTokenExpired(accessToken) : null;
  const isAuthenticated = accessToken && !tokenExpired;

  console.log('[Middleware] AUTH STATUS:', {
    isAuthenticated,
    hasToken: !!accessToken,
    tokenExpired,
  });

  // Check if current path is public
  const isPublicPath = PUBLIC_PATHS.some(path => {
    // If the public path is just '/', require an exact match
    if (path === '/') {
      return pathname === '/';
    }
    // For other paths like '/login', check if it starts with that path
    return pathname.startsWith(path);
  });
  const isAuthPath = AUTH_PATHS.some(path => pathname.startsWith(path));

  console.log('[Middleware] PATH CHECK:', {
    pathname,
    isPublicPath,
    isAuthPath,
  });

  // Redirect both root and dashboard to dashboard/workflows
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  //
  // if (pathname === '/dashboard' || pathname === '/dashboard/') {
  //   return NextResponse.redirect(new URL('/dashboard/workflows', request.url));
  // }
  //
  // If hitting /login or /register, ALWAYS clear tokens first. This step prevents the redirection loop with the backend changes its JWT key
  if (isAuthPath) {
    console.log('[Middleware] ACTION: Entering Auth Path, purging existing tokens');
    const response = NextResponse.next();
    response.cookies.delete('access_token');
    response.cookies.delete('refresh_token');
    return response;
  }
  // Redirect authenticated users away from auth pages
  if (isAuthenticated && isAuthPath) {
    console.log('[Middleware] ACTION: Redirecting authenticated user from entry point of the app');
    return NextResponse.redirect(new URL('/', request.url));
  }

  // If access token is expired but refresh token exists, try to refresh
  if (!isAuthenticated && refreshToken && !isPublicPath) {
    console.log('[Middleware] ACTION: Access token expired, attempting refresh');

    const refreshed = await refreshAccessToken(refreshToken);

    if (refreshed) {
      console.log('[Middleware] SUCCESS: Token refreshed');
      // Set the new access token and proceed
      const response = NextResponse.next();
      response.cookies.set('access_token', refreshed.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: refreshed.expires_in,
        path: '/',
      });
      // Optionally update refresh token if backend rotated it
      if (refreshed.refresh_token) {
        response.cookies.set('refresh_token', refreshed.refresh_token, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          maxAge: 60 * 60 * 24 * 7, // 7 days
          path: '/',
        });
      }
      console.log('[Middleware] ACTION: Allowing request with refreshed token');
      console.log('='.repeat(80));
      return response;
    } else {
      console.log('[Middleware] FAILURE: Token refresh failed');
      // Refresh failed, clear tokens and redirect to login
      const response = NextResponse.redirect(new URL('/login', request.url));
      response.cookies.delete('access_token');
      response.cookies.delete('refresh_token');
      return response;
    }
  }

  // Redirect unauthenticated users to login (except for public paths)
  if (!isAuthenticated && !isPublicPath) {
    console.log('[Middleware] ACTION: Redirecting unauthenticated user to /login');

    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('access_token');
    response.cookies.delete('refresh_token');
    return response;
  }

  console.log('[Middleware] ACTION: Allowing request to proceed');
  console.log('='.repeat(80));
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};

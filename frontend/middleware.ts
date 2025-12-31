import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  // Check if route is protected first
  if (isProtectedRoute(req)) {
    // Always protect protected routes, even for RSC requests
    // RSC requests still need authentication to access protected data
    await auth.protect();
  }
  
  // Skip further processing for RSC requests on non-protected routes
  // (RSC requests for protected routes already went through auth.protect() above)
  if (req.nextUrl.searchParams.has("_rsc")) {
    return;
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next|.*\\..*).*)",
  ],
};

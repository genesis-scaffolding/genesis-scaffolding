# Frontend Documentation: Architecture and Structure

## Architecture Overview: Backend-for-Frontend (BFF)

The frontend is designed as a **Backend-for-Frontend (BFF)**. Next.js does not serve as a standalone application but as an orchestration layer between the browser and the FastAPI backend (`myproject-server`).

### Key Design Principles

* **Server-Side Logic:** Authentication, session management, and sensitive API interactions are handled on the server.
* **Server Actions over REST:** Interaction with the backend is primarily driven by Next.js **Server Actions**. This removes the need to expose backend REST endpoints to the client and simplifies state management by moving the "fetch-and-mutate" logic to the server.
* **Environment Isolation:** The `FASTAPI_URL` is kept on the server. The client communicates with the backend either through Server Actions or a dedicated proxy route (`/api/proxy`), preventing the leakage of internal infrastructure details.
* **Stateless Frontend:** Identity is verified by the FastAPI service. The Next.js server maintains a stateless session via HTTP-only cookies, passing JWTs to the backend for authorization.

---

## Technical Stack and Dependencies

The frontend utilizes a modern React ecosystem focused on type safety and performance.

| Category | Technology |
| --- | --- |
| **Framework** | Next.js 16 (App Router) |
| **Language** | TypeScript ^5 |
| **UI Library** | React 19.2 |
| **Styling** | Tailwind CSS 4 (PostCSS build) |
| **UI Components** | Shadcn UI (Radix UI primitives) |
| **Icons** | Lucide React |
| **Utilities** | `clsx`, `tailwind-merge` (for dynamic class management) |

---

## Directory Structure

The project follows the Next.js App Router conventions with a domain-driven organization for components and logic.

### `/app` (Routing and Actions)

* **`/actions`**: Contains Server Actions. These functions handle data mutations and interact directly with the FastAPI backend.
  * `auth.ts`: Session and identity management.
  * `workflow.ts`: Workflow manifest retrieval and execution triggers.
  * `job.ts`: Polling and result retrieval for background tasks.
  * `sandbox.ts`: File management (upload/delete/list) within the user's persistent storage.
  * `schedule.ts`: CRUD operations for automated workflow triggers.

* **`/api/[...proxy]`**: A catch-all route handler. It proxies client-side requests to the FastAPI backend to bypass CORS, manage file downloads via secure JWT injection, and hide backend origin.

* **`/(routes)`**:
  * `/login`: Authentication entry point (wrapped in `Suspense` for CSR compatibility).
  * `/dashboard/workflows`: Gallery of executable tools.
  * `/dashboard/jobs`: Real-time monitoring of active and historical executions.
  * `/dashboard/sandbox`: Full-featured file explorer for user assets.
  * `/dashboard/schedules`: Management console for automations.
  * `/dashboard/schedules/[id]`: Detailed execution history for a specific schedule.

### `/lib` (Core Logic)

* **`auth.ts`**: Integration logic for FastAPI OAuth2 Password flow.
* **`session.ts`**: Low-level cookie management for tokens using `next/headers`.
* **`workflow-utils.ts`**: Dynamic **Zod schema generation** logic. Converts FastAPI-provided tool manifests into runtime validation schemas for React Hook Form.
* **`job-utils.ts`**: Helpers for parsing status states and formatting execution results.
* **date-utils.ts**: Normalization of backend UTC timestamps for consistent local browser rendering.

### `/components` (UI Layer)

* **`/auth`**: Login forms and logout triggers.

* **`/dashboard`**: Domain-specific UI for the core application.
  * **Workflow Execution**: `workflow-form.tsx` and `workflow-fields-renderer.tsx` (Shared logic for dynamic input generation).
  * **Automation**: `schedule-table.tsx`, `schedule-form.tsx`, and `timezone-select.tsx`.
  * **File Management**: Modular components including `sandbox-file-explorer.tsx`, `standalone-upload-button.tsx`, and `file-browser-modal.tsx`.
  * **File Picking**: Specialized inputs like `sandbox-file-picker.tsx` (single) and `sandbox-multi-file-picker.tsx` (array) that interface with the Sandbox API.
  * **Job Results**: Detailed views for downloads, status banners, and text outputs.

* **`/ui`**: Shadcn UI low-level primitives (Dialogs, Tabs, ScrollArea, etc.).

### `/types`

* Centralized TypeScript definitions mirroring FastAPI Pydantic models.
  * `workflow.ts`: Definitions for inputs, manifests, and parameter types.
  * `sandbox.ts`: Metadata structures for files and folders.
  * `job.ts`: Status enums and result payload interfaces.
  * `schedule.ts`: Definitions for Cron expressions, IANA timezones, and Schedule entities.

### Key Technical Patterns Implemented

* **Dynamic Validation**: Utilizing `generateZodSchema` to bridge the gap between backend-defined tool inputs and frontend form validation.
* **Smart Component Reuse**: The `WorkflowFieldsRenderer` decouples workflow input logic from execution logic, allowing the same high-fidelity UI (File Pickers, Smart Textareas) to be used for both manual execution and schedule configuration.
* **Timezone-Aware Persistence**: Capturing the user's specific IANA timezone and absolute sandbox directory during schedule creation to ensure deterministic background execution.
* **Stateful Syncing**: Implementing `revalidateTag('schedules')` to ensure real-time updates of the background scheduler state across the dashboard.

---

## Authentication Flow

The authentication system is a custom implementation of the **OAuth2 Password Grant** flow. It avoids third-party libraries, relying on FastAPI for credential validation and Next.js Server Actions for session persistence.

### 1. Credential Submission

The client submits the login form via a **Server Action** (`loginAction`). This avoids exposing the FastAPI `/auth/login` endpoint to the browser.

```typescript
// app/actions/auth.ts
export async function loginAction(prevState: LoginState, formData: FormData) {
  const result = await authenticateUser(username, password); // Calls FastAPI
  
  if (result.success) {
    await createSession(result.data.access_token, result.data.refresh_token);
    return { success: true };
  }
}

```

### 2. Stateless Session Management

Tokens are stored in **HTTP-only, Secure cookies**. This ensures that the frontend remains stateless while protecting tokens from client-side JavaScript access (XSS mitigation).

```typescript
// lib/session.ts
export async function createSession(accessToken: string, refreshToken: string) {
  const cookieStore = await cookies();
  cookieStore.set('access_token', accessToken, { httpOnly: true, secure: true, sameSite: 'lax' });
}

```

### 3. Middleware Protection and Proxying

The `proxy.ts` middleware acts as the primary gatekeeper. It intercepts requests to validate token expiration before the request reaches the App Router or the backend.

* **JWT Validation:** Decodes the `access_token` payload to check the `exp` claim.
* **Route Guarding:** Redirects unauthenticated users to `/login` and authenticated users away from auth pages to `/dashboard`.
* **Token Cleanup:** Deletes expired or invalid cookies during the redirection phase.

### 4. Server-Side Identity Verification

For sensitive operations or initial page loads, the server verifies the token against the FastAPI `/users/me` endpoint.

```typescript
// app/actions/auth.ts
export async function getCurrentUser(): Promise<User | null> {
  const accessToken = await getAccessToken();
  if (!accessToken) return null;

  const user = await fetchUser(accessToken); 
  if (!user) {
    await deleteSession(); // Token rejected by backend
    return null;
  }
  return user;
}

```

---

## API Proxy Implementation

The route handler at `app/api/[...proxy]/route.ts` serves as a transparent bridge for client-side components to communicate with the FastAPI backend. This avoids exposing the `FASTAPI_URL` to the client and centralizes header management.

### Mechanism

The handler uses **Dynamic Route Segments** (`[...proxy]`) to capture any nested path following `/api/`. It reconstructs the target endpoint and forwards the request using `apiFetch`.

* **Path Reconstruction**: It joins the path segments and appends the original query string to ensure the request is identical when it reaches the backend.
* **Method Handling**: Separate `GET` and `POST` exports handle different HTTP verbs, forwarding the request body and `Content-Type` headers where applicable.
* **Encapsulation**: Client-side components call `/api/users/profile` instead of `http://backend-host:8000/users/profile`.

```typescript
// Example Client-Side Usage
const response = await fetch('/api/users/me');
const userData = await response.json();

```

### Integration with `apiFetch`

The proxy relies on a utility in `lib/api-client.ts`. This utility is responsible for:

1. Prepending the `FASTAPI_URL` to the request.
2. Injecting the `access_token` from the server-side cookies into the `Authorization` header.
3. Standardizing error handling for server-to-server communication.

---

## Summary of Logic Flow

| Step | Component | Action |
| --- | --- | --- |
| **1. Request** | Browser | Calls `/api/some-endpoint` |
| **2. Intercept** | `proxy.ts` (Middleware) | Validates JWT; redirects to `/login` if expired. |
| **3. Route** | `app/api/[...proxy]` | Captures path and parameters. |
| **4. Fetch** | `lib/api-client.ts` | Attaches `access_token` and calls FastAPI. |
| **5. Response** | Route Handler | Returns FastAPI's JSON and status code to the browser. |

This architecture ensures that the browser never manages tokens directly and never communicates with the backend origin, maintaining a clean separation of concerns and a secure authentication perimeter.

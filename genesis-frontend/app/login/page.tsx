import { Suspense } from 'react';
import LoginForm from '@/components/auth/login-form';

export default async function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-white p-8 shadow-md">
        <div>
          <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900">
            Sign in to your account
          </h2>
        </div>
        <Suspense fallback={<div>Loading login...</div>}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}

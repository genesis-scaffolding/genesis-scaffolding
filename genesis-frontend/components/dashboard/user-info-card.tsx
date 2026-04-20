import type { User } from '@/types/user';

interface UserInfoCardProps {
  user: User;
}

export default function UserInfoCard({ user }: UserInfoCardProps) {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-2xl font-semibold">User Information</h2>
      <dl className="space-y-2">
        <div>
          <dt className="text-sm font-medium text-gray-500">Username</dt>
          <dd className="text-sm text-gray-900">{user.username}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-gray-500">Email</dt>
          <dd className="text-sm text-gray-900">{user.email || 'N/A'}</dd>
        </div>
        {user.full_name && (
          <div>
            <dt className="text-sm font-medium text-gray-500">Full Name</dt>
            <dd className="text-sm text-gray-900">{user.full_name}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

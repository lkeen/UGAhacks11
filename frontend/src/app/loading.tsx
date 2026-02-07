import { Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
        <div className="text-center">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Disaster Relief Optimizer
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Loading dashboard...
          </p>
        </div>
      </div>
    </div>
  );
}

'use client';

interface IdentityTabProps {
  mind: any;
}

export default function IdentityTab({ mind }: IdentityTabProps) {
  // Helper function to get initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Helper function to format date
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="flex items-center justify-center min-h-[600px] p-6">
      {/* Professional Digital ID Card */}
      <div className="w-full max-w-4xl">
        {/* Card Container with gradient border effect */}
        <div className="relative bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 p-[2px] rounded-2xl shadow-2xl">
          <div className="bg-white rounded-2xl overflow-hidden">
            {/* Header Section with gradient background */}
            <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium opacity-90">GENESIS MINDS</p>
                  <p className="text-xs opacity-75">Digital Identity Card</p>
                </div>
                <div className="text-right">
                  <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${
                    mind.status === 'active' ? 'bg-green-500' :
                    mind.status === 'sleeping' ? 'bg-yellow-500' :
                    'bg-gray-500'
                  }`}>
                    <span className="inline-block w-2 h-2 bg-white rounded-full animate-pulse"></span>
                    {mind.status?.toUpperCase() || 'UNKNOWN'}
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="p-8">
              <div className="flex gap-8">
                {/* Left: Avatar Section */}
                <div className="flex-shrink-0">
                  <div className="w-48 h-48 bg-gradient-to-br from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center shadow-lg">
                    <span className="text-6xl font-bold text-white">
                      {getInitials(mind.name)}
                    </span>
                  </div>
                  <div className="mt-4 text-center">
                    <div className="inline-block px-4 py-2 bg-gray-100 rounded-lg">
                      <p className="text-xs text-gray-600 font-medium">GMID</p>
                      <p className="text-sm font-mono font-bold text-gray-900 mt-1">
                        {mind.gmid}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Right: Personal Information */}
                <div className="flex-1 space-y-6">
                  {/* Name Section */}
                  <div className="border-b pb-4">
                    <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Full Name</p>
                    <p className="text-3xl font-bold text-gray-900 mt-1">{mind.name}</p>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Age</p>
                      <p className="text-lg font-semibold text-gray-900 mt-1">{mind.age}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Current Emotion</p>
                      <p className="text-lg font-semibold text-gray-900 mt-1 capitalize">
                        {mind.current_emotion || 'Neutral'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Template</p>
                      <p className="text-lg font-semibold text-gray-900 mt-1 capitalize">
                        {mind.template ? mind.template.split('/').pop()?.replace(/_/g, ' ') : 'N/A'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Model</p>
                      <p className="text-lg font-semibold text-gray-900 mt-1">{mind.llm_model || 'N/A'}</p>
                    </div>
                    <div className="col-span-2">
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Creator</p>
                      <p className="text-lg font-semibold text-gray-900 mt-1">{mind.creator_email || mind.creator || 'N/A'}</p>
                    </div>
                  </div>

                  {/* Personality Traits */}
                  {mind.personality && (
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider mb-3">Personality Profile</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(mind.personality).slice(0, 6).map(([trait, value]: [string, any]) => (
                          <div
                            key={trait}
                            className="px-4 py-2 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg"
                          >
                            <p className="text-xs text-gray-600 capitalize">{trait}</p>
                            <p className="text-sm font-bold text-gray-900">
                              {typeof value === 'number' ? value.toFixed(2) : value}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Footer with verification info */}
              <div className="mt-8 pt-6 border-t border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Verified Digital Identity</p>
                    <p className="text-sm font-semibold text-gray-900">Genesis Minds Network</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Created</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {formatDate(mind.created_at)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Additional Info Below Card */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>This is an official digital identity credential issued by Genesis Minds</p>
        </div>
      </div>
    </div>
  );
}

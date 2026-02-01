/**
 * Environment utility functions
 */

/**
 * Check if the current environment is production
 */
export function isProduction(): boolean {
  const envValue = process.env.NEXT_PUBLIC_ENVIRONMENT;
  console.log('[ENV CHECK] NEXT_PUBLIC_ENVIRONMENT:', envValue);
  console.log('[ENV CHECK] Is production?', envValue === 'production');
  return envValue === 'production';
}

/**
 * Check if creation features should be disabled
 * Creation is now allowed in production, but with limits enforced by backend
 */
export function isCreationDisabled(): boolean {
  // Allow creation in production (backend enforces per-user limits)
  const disabled = false;
  console.log('[ENV CHECK] Creation disabled?', disabled);
  return disabled;
}

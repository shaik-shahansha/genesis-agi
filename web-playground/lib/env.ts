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
 * In production, we disable creation of new minds, environments, and modification of settings
 */
export function isCreationDisabled(): boolean {
  const disabled = isProduction();
  console.log('[ENV CHECK] Creation disabled?', disabled);
  return disabled;
}

/**
 * Environment utility functions
 */

/**
 * Check if the current environment is production
 */
export function isProduction(): boolean {
  return process.env.Environment === 'production';
}

/**
 * Check if creation features should be disabled
 * In production, we disable creation of new minds, environments, and modification of settings
 */
export function isCreationDisabled(): boolean {
  return isProduction();
}

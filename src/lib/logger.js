/**
 * Production-safe logging utility.
 * - In development: uses console.* for full visibility
 * - In production: strips debug logs, sanitizes sensitive data from errors
 */

const isDev = import.meta.env.DEV;

/**
 * Strip sensitive data from error messages and objects
 */
function sanitize(input) {
  if (typeof input === 'string') {
    return input
      .replace(/Bearer\s+[A-Za-z0-9\-._~+/]+=*/g, 'Bearer [REDACTED]')
      .replace(/access_token["']?\s*[:=]\s*["'][A-Za-z0-9\-._~+/]+=*/g, 'access_token: [REDACTED]')
      .replace(/[?&]token=[^&\s]*/g, 'token=[REDACTED]');
  }
  return input;
}

/**
 * Sanitize all arguments before logging
 */
function sanitizeArgs(args) {
  return args.map(arg => {
    if (typeof arg === 'object' && arg !== null) {
      try {
        const str = JSON.stringify(arg);
        return JSON.parse(sanitize(str));
      } catch {
        return arg;
      }
    }
    return sanitize(String(arg));
  });
}

export const logger = {
  /**
   * Debug logs - only visible in development
   */
  debug: (...args) => {
    if (isDev) {
      console.debug('[DEBUG]', ...args);
    }
  },

  /**
   * Info logs - visible in all environments
   */
  info: (...args) => {
    if (isDev) {
      console.info('[INFO]', ...args);
    }
  },

  /**
   * Warning logs - visible in all environments, sanitized
   */
  warn: (...args) => {
    console.warn('[WARN]', ...sanitizeArgs(args));
  },

  /**
   * Error logs - visible in all environments, sanitized
   */
  error: (...args) => {
    console.error('[ERROR]', ...sanitizeArgs(args));
  },
};

export default logger;

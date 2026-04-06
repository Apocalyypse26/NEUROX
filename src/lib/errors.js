/**
 * Standardized error classes for consistent error handling across the app.
 * All API errors are mapped to these typed errors for uniform handling.
 */

export class ApiError extends Error {
  constructor(message, statusCode = 0, code = 'API_ERROR') {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
  }
}

export class ValidationError extends ApiError {
  constructor(message, field = null) {
    super(message, 400, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
    this.field = field;
  }
}

export class AuthError extends ApiError {
  constructor(message = 'Authentication required') {
    super(message, 401, 'AUTH_ERROR');
    this.name = 'AuthError';
  }
}

export class NotFoundError extends ApiError {
  constructor(message = 'Resource not found') {
    super(message, 404, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends ApiError {
  constructor(message = 'Rate limit exceeded') {
    super(message, 429, 'RATE_LIMITED');
    this.name = 'RateLimitError';
  }
}

export class ServerError extends ApiError {
  constructor(message = 'Internal server error') {
    super(message, 500, 'SERVER_ERROR');
    this.name = 'ServerError';
  }
}

/**
 * Map HTTP status codes to typed error classes
 */
export function errorFromResponse(statusCode, detail) {
  const message = typeof detail === 'string' ? detail : (detail?.message || 'Unknown error');

  switch (statusCode) {
    case 400:
      return new ValidationError(message, detail?.field);
    case 401:
      return new AuthError(message);
    case 404:
      return new NotFoundError(message);
    case 409:
      return new ApiError(message, 409, 'CONFLICT');
    case 422:
      return new ValidationError(message, detail?.field);
    case 429:
      return new RateLimitError(message);
    case 500:
      return new ServerError(message);
    default:
      return new ApiError(message, statusCode);
  }
}

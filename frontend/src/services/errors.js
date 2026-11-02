/**
 * Turn an Axios error into a short string that is safe to render.
 *
 * FastAPI returns `detail` as a plain string for errors we raise (e.g. 404, blocked URL),
 * but as an ARRAY of objects for request-validation errors (422). Rendering that array in
 * JSX would crash React, so it is flattened to text here.
 */
export function getErrorMessage(error, fallback = 'Something went wrong.') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => String(item?.msg ?? item).replace(/^Value error, /, '')).join(' ');
  }
  if (!error?.response && error?.message === 'Network Error') {
    return 'Cannot reach the API. Is the backend running?';
  }
  return error?.message && !error?.response ? error.message : fallback;
}

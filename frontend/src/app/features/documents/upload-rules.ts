import { MAX_UPLOAD_BYTES } from '../../core/models';

/**
 * What the backend's parser can actually read (`document_parser.extract_pages`).
 *
 * Checking here matters: an unsupported type still uploads successfully (201)
 * and only fails later, asynchronously, during ingestion. Rejecting it in the
 * browser turns a delayed, confusing failure into an immediate message — and
 * saves the wasted upload.
 *
 * Shared by the research form's picker and the documents screen so the two can
 * never disagree about what is allowed.
 */
export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md', '.csv', '.json'];

export const ACCEPT_ATTRIBUTE = ALLOWED_EXTENSIONS.join(',');

/** Returns a human-readable problem, or null when the file is acceptable. */
export function validateUpload(file: File): string | null {
  if (file.size === 0) {
    return 'File is empty.';
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `File is larger than ${MAX_UPLOAD_BYTES / 1024 / 1024} MB.`;
  }
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
  }
  return null;
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) {
    return '—';
  }
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

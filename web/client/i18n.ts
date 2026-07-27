let strings: Record<string, string> = {};

export async function initializeI18n() {
  try {
    const response = await fetch('/strings.json', { cache: 'no-cache' });
    if (response.ok) strings = await response.json();
  } catch {
    // Source previews still work before the runtime resource is copied.
  }

  document.querySelectorAll<HTMLElement>('[data-i18n]').forEach((element) => {
    const key = element.dataset.i18n;
    if (strings[key]) element.textContent = strings[key];
  });
  document.querySelectorAll<HTMLElement>('[data-i18n-attr]').forEach((element) => {
    for (const assignment of element.dataset.i18nAttr.split(';')) {
      const [attribute, key] = assignment.split(':', 2);
      if (attribute && strings[key]) element.setAttribute(attribute, strings[key]);
    }
  });
}

export function t(key: string, fields: Record<string, unknown> = {}, fallback = '') {
  let value = strings[key] || fallback || key;
  Object.entries(fields).forEach(([name, replacement]) => {
    value = value.replaceAll(`{${name}}`, String(replacement));
  });
  return value;
}

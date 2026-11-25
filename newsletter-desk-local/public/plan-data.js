// Accept the original hosted export as well as local schema version 1.
// Validate before changing the user's current browser state.
export function parsePlan(text) {
  let value;
  try { value = JSON.parse(text); }
  catch { throw new Error('Choose a valid newsletter-plan.json export.'); }
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      !Array.isArray(value.sources) || !Array.isArray(value.checks) ||
      !value.fields || typeof value.fields !== 'object' || Array.isArray(value.fields)) {
    throw new Error('This file is not a Newsletter Desk plan.');
  }
  if (value.schemaVersion !== undefined && value.schemaVersion !== 1) {
    throw new Error('This plan uses a newer format. Update the app before importing it.');
  }
  if (value.sources.length > 1000) throw new Error('This plan has more than 1,000 sources.');
  const sources = value.sources.map(source => {
    if (!source || typeof source !== 'object' ||
        typeof source.name !== 'string' || !source.name.trim() ||
        typeof source.url !== 'string') {
      throw new Error('Every source needs a name and a valid URL.');
    }
    let url;
    try { url = new URL(source.url); }
    catch { throw new Error('A source has an invalid URL.'); }
    const type = typeof source.type === 'string' ? source.type : 'Website';
    const protocols = type === 'Calendar feed' ? ['http:', 'https:', 'webcal:'] : ['http:', 'https:'];
    if (!protocols.includes(url.protocol)) {
      throw new Error(type === 'Calendar feed' ? 'Calendar URLs must use webcal, http, or https.' : 'Source URLs must use http or https.');
    }
    return {
      name: source.name,
      url: url.href,
      type,
      topic: typeof source.topic === 'string' ? source.topic : ''
    };
  });
  if (value.checks.some(check => !Number.isInteger(check) || check < 0 || check > 4)) {
    throw new Error('This plan contains invalid checklist items.');
  }
  const fields = Object.fromEntries(Object.entries(value.fields).map(([name, content]) => {
    if (typeof content !== 'string') throw new Error('Plan fields must contain text.');
    return [name, content];
  }));
  return { sources, checks: [...new Set(value.checks)], fields };
}

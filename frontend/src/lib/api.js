const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export async function fetchJSON(url) {
  try {
    const res = await fetch(`${API_BASE}${url}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`Fetch failed: ${url}`, e);
    return null;
  }
}

export async function postJSON(url, body) {
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return await res.json();
  } catch (e) {
    console.error(`Post failed: ${url}`, e);
    return null;
  }
}

export function formatMoney(val) {
  if (val == null) return '$0.00';
  const sign = val >= 0 ? '+' : '';
  return `${sign}$${val.toFixed(2)}`;
}

export function formatCurrency(val) {
  if (val == null || isNaN(Number(val))) return '$--';
  return `$${Number(val).toFixed(2)}`;
}

export function formatPrice(val) {
  if (val == null || isNaN(Number(val))) return '--';
  const num = Number(val);
  const decimals = Math.abs(num) >= 100 ? 3 : 5;
  return num.toFixed(decimals);
}

export function formatPercent(val) {
  if (val == null || isNaN(Number(val))) return '--';
  return `${(Number(val) * 100).toFixed(1)}%`;
}

export function formatProfitFactor(val) {
  if (val == null) return 'Inf';
  if (isNaN(Number(val))) return '--';
  if (!isFinite(val)) return 'Inf';
  return Number(val).toFixed(2);
}

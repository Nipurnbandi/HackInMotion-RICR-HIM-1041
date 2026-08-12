/**
 * Reverse geocoding, isolated behind one function so the provider can be
 * swapped without touching the map UI.
 *
 * Defaults to OpenStreetMap Nominatim, which needs no API key. Point
 * VITE_GEOCODING_URL at another provider (or your own backend proxy) to
 * change it; the address is optional everywhere, so failures degrade to
 * coordinates rather than blocking a report.
 */

const GEOCODING_URL =
  import.meta.env.VITE_GEOCODING_URL ?? "https://nominatim.openstreetmap.org/reverse";

export async function reverseGeocode(latitude, longitude, { signal } = {}) {
  const url = new URL(GEOCODING_URL);
  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("lat", latitude);
  url.searchParams.set("lon", longitude);
  url.searchParams.set("zoom", "18");

  try {
    const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
    if (!response.ok) return null;

    const data = await response.json();
    return data?.display_name ?? null;
  } catch {
    // Offline, rate-limited, or blocked: the caller falls back to coordinates.
    return null;
  }
}

export function formatCoordinates(latitude, longitude) {
  if (latitude == null || longitude == null) return "";
  return `${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)}`;
}

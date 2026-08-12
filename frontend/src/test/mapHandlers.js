/**
 * Shared sink for the map event handlers registered by LocationPicker.
 *
 * The react-leaflet stub in the test files writes into this object, letting a
 * test simulate a map click without a real Leaflet instance. It lives in its
 * own module so `vi.mock` factories (which are hoisted above imports) can
 * reach it via a dynamic import.
 */
export const mapHandlers = {};

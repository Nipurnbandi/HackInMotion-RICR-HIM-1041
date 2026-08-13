import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

import { formatCoordinates, reverseGeocode } from "../services/geocoding";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ??
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  import.meta.env.VITE_MAP_TILE_ATTRIBUTION ??
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const DEFAULT_CENTER = [23.2599, 77.4126];

function ClickHandler({ onPick }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function Recenter({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.setView(position, Math.max(map.getZoom(), 16));
  }, [map, position]);
  return null;
}

export default function LocationPicker({ value, onChange, error }) {
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [addressLoading, setAddressLoading] = useState(false);
  const geocodeRef = useRef(null);

  const position = value?.latitude != null ? [value.latitude, value.longitude] : null;

  const pick = useCallback(
    async (latitude, longitude) => {
      onChange({ latitude, longitude, address: null });

      geocodeRef.current?.abort();
      const controller = new AbortController();
      geocodeRef.current = controller;

      setAddressLoading(true);
      const address = await reverseGeocode(latitude, longitude, {
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setAddressLoading(false);
        onChange({ latitude, longitude, address });
      }
    },
    [onChange]
  );

  useEffect(() => () => geocodeRef.current?.abort(), []);

  function useMyLocation() {
    setLocationError("");

    if (!navigator.geolocation) {
      setLocationError("Your browser doesn't support location access.");
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (result) => {
        setLocating(false);
        pick(result.coords.latitude, result.coords.longitude);
      },
      () => {
        setLocating(false);
        setLocationError(
          "We couldn't get your location. Allow location access, or tap the map to place the marker."
        );
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  const errorId = error ? "location-error" : undefined;

  return (
    <div className="location-picker">
      <div className="location-picker__toolbar">
        <button
          type="button"
          className="button button--secondary"
          onClick={useMyLocation}
          disabled={locating}
        >
          {locating ? "Locating…" : "📍 Use my current location"}
        </button>
        <p className="location-picker__hint">
          Tap the map or drag the marker to pinpoint the exact spot.
        </p>
      </div>

      <div
        className="location-picker__map"
        aria-describedby={[errorId, "location-readout"].filter(Boolean).join(" ")}
      >
        <MapContainer
          center={position ?? DEFAULT_CENTER}
          zoom={position ? 16 : 13}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
          <ClickHandler onPick={pick} />
          {position && (
            <>
              <Recenter position={position} />
              <Marker
                position={position}
                icon={defaultIcon}
                draggable
                eventHandlers={{
                  dragend: (event) => {
                    const { lat, lng } = event.target.getLatLng();
                    pick(lat, lng);
                  },
                }}
              />
            </>
          )}
        </MapContainer>
      </div>

      {locationError && (
        <p className="field-error" role="alert">
          {locationError}
        </p>
      )}

      <div className="location-readout" id="location-readout">
        {position ? (
          <>
            <div>
              <p className="location-readout__label">Selected location</p>
              <p className="location-readout__value">
                {formatCoordinates(value.latitude, value.longitude)}
              </p>
            </div>
            <div>
              <p className="location-readout__label">Address</p>
              <p className="location-readout__value location-readout__value--muted">
                {addressLoading
                  ? "Looking up address…"
                  : value.address || "No address found — coordinates will be used."}
              </p>
            </div>
          </>
        ) : (
          <p className="location-readout__empty">
            No location selected yet. Use your current location or tap the map.
          </p>
        )}
      </div>

      {error && (
        <p className="field-error" id={errorId} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

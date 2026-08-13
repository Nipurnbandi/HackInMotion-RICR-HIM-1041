import { MapContainer, Marker, TileLayer } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  shadowSize: [41, 41],
});

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ??
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  import.meta.env.VITE_MAP_TILE_ATTRIBUTION ??
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export default function IssueLocationMap({ latitude, longitude, label }) {
  if (latitude == null || longitude == null) {
    return <p className="muted">No location was recorded for this report.</p>;
  }

  const position = [latitude, longitude];

  return (
    <div className="issue-map" role="img" aria-label={label ?? "Map of the reported location"}>
      <MapContainer
        center={position}
        zoom={16}
        scrollWheelZoom={false}
        dragging={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
        <Marker position={position} icon={defaultIcon} />
      </MapContainer>
    </div>
  );
}

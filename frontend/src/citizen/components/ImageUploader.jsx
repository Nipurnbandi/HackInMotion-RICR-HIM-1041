import { useEffect, useRef, useState } from "react";
import { ACCEPTED_PHOTO_TYPES, MAX_PHOTO_BYTES } from "../constants";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImageUploader({ value, onChange, progress, error }) {
  const inputRef = useRef(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (!value) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(value);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  function handleFile(file) {
    if (!file) return;

    if (!ACCEPTED_PHOTO_TYPES.includes(file.type)) {
      setLocalError(
        "That file type isn't supported. Please choose a JPEG, PNG, or WEBP image."
      );
      onChange(null);
      return;
    }

    if (file.size > MAX_PHOTO_BYTES) {
      setLocalError(
        `That photo is ${formatSize(file.size)}. Please choose an image under ${formatSize(
          MAX_PHOTO_BYTES
        )}.`
      );
      onChange(null);
      return;
    }

    setLocalError("");
    onChange(file);
  }

  function remove() {
    setLocalError("");
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const shownError = localError || error;

  return (
    <div className="image-uploader">
      <label className="image-uploader__label" htmlFor="photo-input">
        Photo evidence <span className="field-optional">(optional but recommended)</span>
      </label>

      <input
        id="photo-input"
        ref={inputRef}
        type="file"
        accept={ACCEPTED_PHOTO_TYPES.join(",")}
        capture="environment"
        onChange={(event) => handleFile(event.target.files?.[0])}
        className="image-uploader__input"
        aria-describedby="photo-help"
      />

      <p className="field-hint" id="photo-help">
        JPEG, PNG or WEBP, up to {formatSize(MAX_PHOTO_BYTES)}. A clear photo helps the
        city verify and prioritise your report.
      </p>

      {previewUrl && value && (
        <div className="image-uploader__preview">
          <img
            src={previewUrl}
            alt={`Preview of the photo evidence you attached: ${value.name}`}
          />
          <div className="image-uploader__meta">
            <p className="image-uploader__filename">{value.name}</p>
            <p className="image-uploader__size">{formatSize(value.size)}</p>

            {progress != null && progress < 100 && (
              <div className="upload-progress">
                <div
                  className="upload-progress__bar"
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Photo upload progress"
                >
                  <span style={{ width: `${progress}%` }} />
                </div>
                <span className="upload-progress__text">{progress}%</span>
              </div>
            )}

            <div className="image-uploader__actions">
              <button
                type="button"
                className="button button--ghost"
                onClick={() => inputRef.current?.click()}
              >
                Replace
              </button>
              <button
                type="button"
                className="button button--ghost button--danger"
                onClick={remove}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}

      {shownError && (
        <p className="field-error" role="alert">
          {shownError}
        </p>
      )}
    </div>
  );
}

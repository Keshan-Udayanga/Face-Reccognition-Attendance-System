import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CalendarDays,
  Camera,
  CameraOff,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  LogIn,
  LogOut,
  Radio,
  ScanFace,
  ShieldAlert,
  Trash2,
  Video,
} from "lucide-react";
import {
  recognizeFrame,
  startRecognition as createRecognitionSession,
  stopRecognition as closeRecognitionSession,
} from "../services/attendanceService";
import "./Attendance.css";

function getInitials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function formatEventTime(value) {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function AttendanceResult({ result }) {
  if (!result) {
    return (
      <div className="attendance-result-empty">
        <span className="attendance-result-empty-icon">
          <ScanFace aria-hidden="true" size={25} />
        </span>
        <h3>Ready for a face scan</h3>
        <p>Start recognition to see employee matches and attendance events here.</p>
      </div>
    );
  }

  if (!result.recognized) {
    return (
      <div className="attendance-result-unknown" role="status">
        <span className="attendance-result-icon attendance-result-icon-warning">
          <ShieldAlert aria-hidden="true" size={23} />
        </span>
        <div>
          <span className="attendance-result-kicker">No attendance recorded</span>
          <h3>Unknown Person</h3>
          <p>This face does not match an active employee record.</p>
        </div>
      </div>
    );
  }

  const employee = result.employee;
  const isCheckOut = result.attendanceAction === "CHECK OUT";
  const actionLabel =
    result.attendanceAction === "CHECK IN" || isCheckOut
      ? result.attendanceAction
      : result.attendanceAction || "RECOGNIZED";

  return (
    <div className="attendance-result-success" role="status">
      <div className="attendance-result-success-heading">
        <span className="attendance-result-icon attendance-result-icon-success">
          <CheckCircle2 aria-hidden="true" size={23} />
        </span>
        <div>
          <span className="attendance-result-kicker">Face match confirmed</span>
          <h3>Recognized</h3>
        </div>
        <span className="attendance-recognized-indicator">
          <span />
          Verified
        </span>
      </div>

      <div className="attendance-employee-profile">
        <span className="attendance-profile-photo">
          {employee.photoUrl ? (
            <img alt="" src={employee.photoUrl} />
          ) : (
            getInitials(employee.fullName)
          )}
        </span>
        <div className="attendance-employee-copy">
          <strong>{employee.fullName}</strong>
          <span>{employee.designation || employee.department || "Employee"}</span>
        </div>
      </div>

      <dl className="attendance-result-details">
        <div>
          <dt>Employee ID</dt>
          <dd>{employee.employeeId}</dd>
        </div>
        <div>
          <dt>Department</dt>
          <dd>{employee.department || "—"}</dd>
        </div>
      </dl>

      <div className={`attendance-action-row ${isCheckOut ? "attendance-action-checkout" : ""}`}>
        <span className="attendance-action-icon">
          <Clock3 aria-hidden="true" size={16} />
        </span>
        <div>
          <span>Attendance action</span>
          <strong>{actionLabel}</strong>
        </div>
        <time>{formatEventTime(result.timestamp)}</time>
      </div>
    </div>
  );
}

function AttendanceEventHistory({
  events,
  filter,
  selectedEventId,
  onFilterChange,
  onSelect,
  onClear,
}) {
  const filters = [
    { value: "ALL", label: "All" },
    { value: "CHECK IN", label: "Check-ins" },
    { value: "CHECK OUT", label: "Check-outs" },
  ];
  const visibleEvents = events.filter(
    (event) => filter === "ALL" || event.attendanceAction === filter,
  );

  return (
    <div aria-label="Recent check-in and check-out events" className="attendance-event-history">
      <div className="attendance-event-heading">
        <div>
          <h3>Recent activity</h3>
          <span>{events.length} event{events.length === 1 ? "" : "s"} this session</span>
        </div>
        {events.length > 0 && (
          <button className="attendance-clear-button" onClick={onClear} type="button">
            <Trash2 aria-hidden="true" size={14} />
            Clear
          </button>
        )}
      </div>

      <div aria-label="Filter attendance events" className="attendance-event-filters" role="group">
        {filters.map((item) => (
          <button
            aria-pressed={filter === item.value}
            className={filter === item.value ? "attendance-filter-active" : ""}
            key={item.value}
            onClick={() => onFilterChange(item.value)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {visibleEvents.length === 0 ? (
        <p className="attendance-event-empty" role="status">
          {events.length === 0
            ? "New check-ins and check-outs will appear here."
            : `No ${filter === "CHECK IN" ? "check-in" : "check-out"} events in this session.`}
        </p>
      ) : (
        <ul className="attendance-event-list">
          {visibleEvents.map((event) => {
            const isCheckOut = event.attendanceAction === "CHECK OUT";
            const ActionIcon = isCheckOut ? LogOut : LogIn;
            return (
              <li key={event.eventId}>
                <button
                  aria-pressed={selectedEventId === event.eventId}
                  className={`attendance-event-item ${
                    selectedEventId === event.eventId ? "attendance-event-selected" : ""
                  }`}
                  onClick={() => onSelect(event)}
                  type="button"
                >
                  <span
                    className={`attendance-event-icon ${
                      isCheckOut ? "attendance-event-icon-checkout" : ""
                    }`}
                  >
                    <ActionIcon aria-hidden="true" size={16} />
                  </span>
                  <span className="attendance-event-copy">
                    <strong>{event.employee.fullName}</strong>
                    <small>{isCheckOut ? "Checked out" : "Checked in"}</small>
                  </span>
                  <time>{formatEventTime(event.timestamp)}</time>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function Attendance() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const sessionIdRef = useRef("");
  const frameInFlightRef = useRef(false);
  const isMountedRef = useRef(false);
  const [cameraStatus, setCameraStatus] = useState("disconnected");
  const [cameraError, setCameraError] = useState("");
  const [recognitionError, setRecognitionError] = useState("");
  const [isOpeningCamera, setIsOpeningCamera] = useState(false);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [isStartingRecognition, setIsStartingRecognition] = useState(false);
  const [result, setResult] = useState(null);
  const [attendanceEvents, setAttendanceEvents] = useState([]);
  const [attendanceFilter, setAttendanceFilter] = useState("ALL");
  const [selectedEventId, setSelectedEventId] = useState("");
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const clock = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(clock);
  }, []);

  useEffect(() => {
    if (!isRecognizing || !sessionIdRef.current) {
      return undefined;
    }

    const sendFrame = async () => {
      const sessionId = sessionIdRef.current;
      if (frameInFlightRef.current || !sessionId) {
        return;
      }

      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2 || !video.videoWidth) {
        return;
      }

      frameInFlightRef.current = true;
      try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const frame = await new Promise((resolve) =>
          canvas.toBlob(resolve, "image/jpeg", 0.82),
        );
        if (!frame) {
          throw new Error("Could not capture a camera frame.");
        }

        const response = await recognizeFrame(sessionId, frame);
        if (sessionIdRef.current !== sessionId) {
          return;
        }
        setRecognitionError("");
        const event =
          response.faces.find((face) => face.isNewRecognition) ||
          response.faces.find((face) => face.recognized) ||
          response.faces[0] ||
          null;

        if (event && !event.recognized) {
          setResult(event);
        } else if (event?.isNewRecognition) {
          setResult(event);
        } else if (event?.recognized) {
          setResult((current) => (current?.recognized ? current : event));
        }

        const newEvents = response.faces
          .filter((face) => face.recognized && face.newAttendance)
          .map((face, index) => ({
            ...face,
            eventId: `${face.employee.employeeId}-${face.attendanceAction}-${face.timestamp}-${index}`,
          }));
        if (newEvents.length > 0) {
          setAttendanceEvents((current) => [...newEvents, ...current].slice(0, 8));
          setSelectedEventId(newEvents[0].eventId);
        }
      } catch (error) {
        if (sessionIdRef.current !== sessionId) {
          return;
        }
        setRecognitionError(error.message);
        setIsRecognizing(false);
        sessionIdRef.current = "";
        if (sessionId) {
          closeRecognitionSession(sessionId).catch((stopError) => {
            console.error("Could not close the recognition session.", stopError);
          });
        }
      } finally {
        frameInFlightRef.current = false;
      }
    };

    const interval = window.setInterval(sendFrame, 1800);
    sendFrame();
    return () => window.clearInterval(interval);
  }, [isRecognizing]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      streamRef.current?.getTracks().forEach((track) => {
        track.onended = null;
        track.stop();
      });
      streamRef.current = null;
      const sessionId = sessionIdRef.current;
      sessionIdRef.current = "";
      if (sessionId) {
        closeRecognitionSession(sessionId).catch((error) => {
          console.error("Could not close the recognition session.", error);
        });
      }
    };
  }, []);

  async function openCamera() {
    setCameraError("");
    setIsOpeningCamera(true);
    setCameraStatus("connecting");
    let openedStream = null;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera access requires a secure browser context (HTTPS or localhost).");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user" },
      });
      openedStream = stream;
      if (!isMountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      stream.getVideoTracks().forEach((track) => {
        track.onended = () => {
          streamRef.current = null;
          setCameraStatus("disconnected");
          setCameraError("Camera disconnected. Reconnect it to continue.");
          setIsRecognizing(false);
          const sessionId = sessionIdRef.current;
          sessionIdRef.current = "";
          if (sessionId) {
            closeRecognitionSession(sessionId).catch((stopError) => {
              console.error("Could not close the recognition session.", stopError);
            });
          }
        };
      });
      setCameraStatus("connected");
    } catch (error) {
      openedStream?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (!isMountedRef.current) {
        return;
      }
      const messages = {
        NotAllowedError: "Camera permission was denied. Allow camera access in your browser settings and try again.",
        NotFoundError: "No camera was found. Connect a camera and try again.",
        NotReadableError: "The camera is unavailable or being used by another application.",
      };
      setCameraStatus("disconnected");
      setCameraError(messages[error.name] || error.message || "Could not initialize the camera.");
    } finally {
      if (isMountedRef.current) {
        setIsOpeningCamera(false);
      }
    }
  }

  async function stopRecognition() {
    setIsRecognizing(false);
    const sessionId = sessionIdRef.current;
    sessionIdRef.current = "";
    if (sessionId) {
      try {
        await closeRecognitionSession(sessionId);
      } catch (error) {
        setRecognitionError(error.message);
      }
    }
  }

  async function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => {
      track.onended = null;
      track.stop();
    });
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraStatus("disconnected");
    await stopRecognition();
  }

  async function beginRecognition() {
    setRecognitionError("");
    setResult(null);
    setIsStartingRecognition(true);
    try {
      const session = await createRecognitionSession();
      if (!isMountedRef.current) {
        await closeRecognitionSession(session.sessionId);
        return;
      }
      if (session.registeredEmployees === 0) {
        await closeRecognitionSession(session.sessionId);
        throw new Error(
          "No saved employee face embeddings are available. Generate face embeddings for active employees before starting recognition.",
        );
      }
      sessionIdRef.current = session.sessionId;
      setIsRecognizing(true);
    } catch (error) {
      if (isMountedRef.current) {
        setRecognitionError(error.message);
      }
    } finally {
      if (isMountedRef.current) {
        setIsStartingRecognition(false);
      }
    }
  }

  const formattedDate = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(now);
  const formattedTime = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(now);

  return (
    <div className="page-content attendance-page">
      <div className="attendance-page-heading">
        <span className="attendance-page-eyebrow">ATTENDANCE WORKSPACE</span>
        <div className="attendance-page-meta">
          <div className="attendance-date-block">
            <CalendarDays aria-hidden="true" size={17} />
            <span>{formattedDate}</span>
            <strong>{formattedTime}</strong>
          </div>
          <div className={`camera-connection-status camera-status-${cameraStatus}`}>
            <span />
            {cameraStatus === "connected"
              ? "Camera connected"
              : cameraStatus === "connecting"
                ? "Connecting"
                : "Camera disconnected"}
          </div>
        </div>
      </div>

      {(cameraError || recognitionError) && (
        <div className="form-error attendance-error" role="alert">
          <AlertCircle aria-hidden="true" size={18} />
          <span>{cameraError || recognitionError}</span>
        </div>
      )}

      <div className="attendance-main-grid">
        <section aria-label="Camera preview" className="surface-card camera-card">
          <div className="attendance-section-heading">
            <div>
              <h2>Camera preview</h2>
              <p>Position one employee in the frame for best results.</p>
            </div>
            {isRecognizing && (
              <span className="live-recognition-badge">
                <Radio aria-hidden="true" size={14} />
                LIVE
              </span>
            )}
          </div>

          <div className={`camera-preview ${cameraStatus === "connected" ? "camera-preview-connected" : ""}`}>
            <video
              aria-label="Live camera preview"
              autoPlay
              className={cameraStatus === "connected" ? "" : "camera-video-hidden"}
              muted
              playsInline
              ref={videoRef}
            />
            {cameraStatus !== "connected" && (
              <div className="camera-preview-empty">
                {isOpeningCamera ? (
                  <>
                    <span className="camera-preview-icon camera-preview-loading">
                      <LoaderCircle aria-hidden="true" size={28} />
                    </span>
                    <strong>Initializing camera</strong>
                    <span>Please allow camera access when prompted.</span>
                  </>
                ) : (
                  <>
                    <span className="camera-preview-icon">
                      {cameraStatus === "disconnected" ? (
                        <CameraOff aria-hidden="true" size={28} />
                      ) : (
                        <Video aria-hidden="true" size={28} />
                      )}
                    </span>
                    <strong>Camera is not connected</strong>
                    <span>Open your camera to begin live attendance recognition.</span>
                  </>
                )}
              </div>
            )}
            {isRecognizing && (
              <span className="camera-scanning-frame" aria-hidden="true">
                <span />
              </span>
            )}
          </div>
          <canvas className="camera-capture-canvas" ref={canvasRef} />

          <div className="camera-controls">
            <button
              className="secondary-button"
              disabled={isOpeningCamera || cameraStatus === "connected"}
              onClick={openCamera}
              type="button"
            >
              {isOpeningCamera ? (
                <LoaderCircle aria-hidden="true" className="attendance-spin" size={17} />
              ) : (
                <Camera aria-hidden="true" size={17} />
              )}
              Open Camera
            </button>
            <button
              className="secondary-button"
              disabled={cameraStatus !== "connected"}
              onClick={stopCamera}
              type="button"
            >
              <CameraOff aria-hidden="true" size={17} />
              Stop Camera
            </button>
            {!isRecognizing ? (
              <button
                className="primary-button"
                disabled={cameraStatus !== "connected" || isStartingRecognition}
                onClick={beginRecognition}
                type="button"
              >
                {isStartingRecognition ? (
                  <LoaderCircle aria-hidden="true" className="attendance-spin" size={17} />
                ) : (
                  <ScanFace aria-hidden="true" size={17} />
                )}
                Start Recognition
              </button>
            ) : (
              <button className="danger-button" onClick={stopRecognition} type="button">
                <CameraOff aria-hidden="true" size={17} />
                Stop Recognition
              </button>
            )}
          </div>
        </section>

        <section aria-label="Recognition result" className="surface-card recognition-card">
          <div className="attendance-section-heading">
            <div>
              <h2>Recognition result</h2>
              <p>Employee verification and attendance event.</p>
            </div>
            <span className={`recognition-state-dot ${isRecognizing ? "recognition-state-active" : ""}`} />
          </div>
          <AttendanceResult result={result} />
          <AttendanceEventHistory
            events={attendanceEvents}
            filter={attendanceFilter}
            onClear={() => {
              setAttendanceEvents([]);
              setSelectedEventId("");
            }}
            onFilterChange={setAttendanceFilter}
            onSelect={(event) => {
              setSelectedEventId(event.eventId);
              setResult(event);
            }}
            selectedEventId={selectedEventId}
          />
        </section>
      </div>
    </div>
  );
}

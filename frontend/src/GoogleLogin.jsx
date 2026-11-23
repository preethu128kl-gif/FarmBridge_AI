import { useEffect, useRef, useState } from "react";
import { apiRequest } from "./api";

/** Shared Google Identity Services button for Farmer, Consumer, and Partner sign-in. */
export default function GoogleLogin({ role, go, onCredential }) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const buttonRef = useRef(null);
  const callbackRef = useRef({ go, onCredential });
  const [error, setError] = useState("");
  const [status, setStatus] = useState(clientId ? "loading" : "unconfigured");
  callbackRef.current = { go, onCredential };

  useEffect(() => {
    if (!clientId) return undefined;
    let active = true;
    let script = document.querySelector("script[data-google-identity]");
    let resizeObserver = null;
    let renderedWidth = 0;

    const init = () => {
      if (!active) return;
      if (!window.google?.accounts?.id || !buttonRef.current) {
        setStatus("error");
        setError("Google sign-in could not load. Check your connection and try again.");
        return;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (!response?.credential) {
            setError("Google did not return a sign-in credential. Please try again.");
            return;
          }
          setStatus("signing-in");
          setError("");
          try {
            const callback = callbackRef.current;
            if (callback.onCredential) {
              await callback.onCredential(response.credential);
            } else {
              const data = await apiRequest("/auth/google", {
                method: "POST",
                body: JSON.stringify({ credential: response.credential, role }),
              });
              localStorage.setItem("farmbridge_token", data.token);
              localStorage.setItem("farmbridge_user", JSON.stringify(data.user));
              callback.go(role);
            }
          } catch (requestError) {
            setError(requestError.message || "Google sign-in failed. Please try again.");
            setStatus("ready");
          }
        },
      });

      const renderButton = () => {
        if (!active || !buttonRef.current) return;
        const width = Math.max(200, Math.min(400, Math.floor(buttonRef.current.getBoundingClientRect().width)));
        if (width === renderedWidth) return;
        renderedWidth = width;
        buttonRef.current.replaceChildren();
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width,
        });
      };

      renderButton();
      if (window.ResizeObserver) {
        resizeObserver = new ResizeObserver(renderButton);
        resizeObserver.observe(buttonRef.current);
      }
      setStatus("ready");
    };

    const onLoad = () => {
      if (script) script.dataset.loaded = "true";
      init();
    };
    const onError = () => {
      if (!active) return;
      setStatus("error");
      setError("Google sign-in could not load. Check your connection and try again.");
    };

    if (window.google?.accounts?.id) {
      init();
    } else {
      const shouldAppend = !script;
      if (!script) {
        script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.dataset.googleIdentity = "true";
      }
      if (script.dataset.loaded === "true") {
        onError();
        return () => { active = false; };
      }
      script.addEventListener("load", onLoad);
      script.addEventListener("error", onError);
      if (shouldAppend) document.head.appendChild(script);
      if (window.google?.accounts?.id) init();
    }

    return () => {
      active = false;
      resizeObserver?.disconnect();
      script?.removeEventListener("load", onLoad);
      script?.removeEventListener("error", onError);
    };
  }, [clientId, role]);

  return (
    <div className="google-login-wrap">
      {clientId ? (
        <>
          <div className="google-login-button" ref={buttonRef} aria-label="Continue with Google" />
          {status === "loading" && <small className="google-login-status" role="status">Loading Google sign-in…</small>}
          {status === "signing-in" && <small className="google-login-status" role="status">Verifying your Google account…</small>}
        </>
      ) : (
        <>
          <button className="google-login" type="button" disabled>Continue with Google</button>
          <small className="google-login-status">Google sign-in needs VITE_GOOGLE_CLIENT_ID and backend GOOGLE_CLIENT_ID.</small>
        </>
      )}
      {error && <small className="google-login-error" role="alert">{error}</small>}
    </div>
  );
}

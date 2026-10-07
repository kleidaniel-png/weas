// Live-Abgleich: Der Server meldet jede Änderung, die Seiten laden dann neu.
// Verwendung in einer Seite:  useLive(load)
import { useEffect, useRef } from "react";
import { inBackground } from "./api.js";

const listeners = new Set();
let socket = null, retry = null, wanted = false, wasConnected = false;

const emit = (event) => listeners.forEach((fn) => inBackground(() => fn(event)));

function connect() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${location.host}/api/ws`);
  socket.onopen = () => {
    if (wasConnected) emit({ resource: "*" }); // nach Unterbrechung alles neu laden
    wasConnected = true;
  };
  socket.onmessage = (e) => emit(JSON.parse(e.data));
  socket.onclose = () => {
    socket = null;
    if (wanted) retry = setTimeout(connect, 3000);
  };
}

export function startLive() {
  if (wanted) return;
  wanted = true;
  wasConnected = false;
  connect();
}

export function stopLive() {
  wanted = false;
  clearTimeout(retry);
  socket?.close();
}

export function useLive(callback) {
  const ref = useRef(callback);
  ref.current = callback;
  useEffect(() => {
    const fn = (event) => ref.current(event);
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, []);
}

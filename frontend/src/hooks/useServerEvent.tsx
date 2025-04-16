"use client";
import { useState, useEffect, useRef, useCallback } from "react";

type SSEStatus = "idle" | "connecting" | "connected" | "error" | "closed";
type SSEOptions = {
	withCredentials?: boolean;
	reconnectOnError?: boolean;
	maxReconnectAttempts?: number;
	reconnectInterval?: number;
};

/**
 * @description This hook is used to connect to a server event to receive updates about a long running task.
 * @param url - The URL of the server event.
 * @param options - The options for the server event.
 * @returns The status, data, error, disconnect, and reconnect functions.
 */
export const useServerEvent = <T extends Record<string, any>>(
	url: string | null,
	options: SSEOptions = {}
) => {
	const [connectionStatus, setConnectionStatus] = useState<SSEStatus>("idle");
	const [data, setData] = useState<T[]>([]);
	const [error, setError] = useState<Error | null>(null);
	const eventSourceRef = useRef<EventSource | null>(null);
	const reconnectAttemptsRef = useRef(0);
	const expectingClosureRef = useRef(false);

	const {
		withCredentials = true,
		reconnectOnError = true,
		maxReconnectAttempts = 3,
		reconnectInterval = 3000,
	} = options;

	const connect = useCallback(() => {
		if (!url) return;

		// Close any existing connection
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
		}

		try {
			setConnectionStatus("connecting");
			const eventSource = new EventSource(url, { withCredentials });
			eventSourceRef.current = eventSource;

			eventSource.onopen = () => {
				setConnectionStatus("connected");
				reconnectAttemptsRef.current = 0;
				setError(null);
			};

			eventSource.onmessage = (event) => {
				try {
					const parsedData = JSON.parse(event.data);
					console.log("SSE event received:", parsedData);
					// channel: "task-status-updates:83570271-7cc3-4e94-8dc3-c4e0e7a71473";
					// message: "Preparing data for the dataset ...";
					// status: "IN_PROGRESS";
					// task_id: "83570271-7cc3-4e94-8dc3-c4e0e7a71473";

					// Handle data updates
					setData((prev) => [...prev, parsedData]);
				} catch (err) {
					console.error("Error parsing SSE data:", err);
				}
			};

			eventSource.onerror = (event) => {
				// Ignore errors if we're expecting the connection to close
				if (expectingClosureRef.current) {
					console.log("Ignoring expected connection closure error");
					expectingClosureRef.current = false;
					setConnectionStatus("closed");
					return;
				}

				// Handle unexpected errors
				console.error("SSE connection error:", event);
				setError(new Error("EventSource connection error"));
				setConnectionStatus("error");

				if (eventSourceRef.current) {
					eventSourceRef.current.close();
					eventSourceRef.current = null;
				}

				// Attempt reconnection if enabled
				if (
					reconnectOnError &&
					reconnectAttemptsRef.current < maxReconnectAttempts
				) {
					reconnectAttemptsRef.current += 1;
					const delay =
						reconnectInterval * reconnectAttemptsRef.current;
					console.log(
						`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
					);

					setTimeout(() => {
						connect();
					}, delay);
				}
			};
		} catch (err) {
			console.error("Error setting up EventSource:", err);
			setError(
				err instanceof Error
					? err
					: new Error("Unknown error setting up EventSource")
			);
			setConnectionStatus("error");
		}
	}, [
		url,
		withCredentials,
		reconnectOnError,
		maxReconnectAttempts,
		reconnectInterval,
	]);

	const disconnect = useCallback(() => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
			eventSourceRef.current = null;
			setConnectionStatus("closed");
		}
	}, []);

	const clearData = useCallback(() => {
		setData([]);
	}, []);

	// Connect when URL is provided
	useEffect(() => {
		if (url) {
			connect();
		}

		return () => {
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
				eventSourceRef.current = null;
			}
		};
	}, [url, connect]);

	return {
		connectionStatus,
		data,
		error,
		disconnect,
		clearData,
		reconnect: connect,
	};
};

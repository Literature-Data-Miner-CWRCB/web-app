// src/hooks/useServerSideEvents.ts
"use client";
import { useState, useEffect, useCallback } from "react";
import { TaskStage, DatasetResult } from "@/types/events";

interface UseServerSideEventsProps {
	onStageUpdate?: (stage: TaskStage) => void;
	onResultReceived?: (result: DatasetResult) => void;
	onError?: (error: Error) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSE_URL = `${API_BASE_URL}/api/v1/sse/events`;

export function useServerSideEvents({
	onStageUpdate,
	onResultReceived,
	onError,
}: UseServerSideEventsProps = {}) {
	const [isConnected, setIsConnected] = useState(false);
	const [eventSource, setEventSource] = useState<EventSource | null>(null);
	const [taskId, setTaskId] = useState<string | null>(null);

	// Close existing connection
	const stopListening = useCallback(() => {
		if (eventSource) {
			eventSource.close();
			setEventSource(null);
			setIsConnected(false);
			console.log("SSE connection closed");
		}
	}, [eventSource]);

	// Start listening for a specific task
	const startListening = useCallback(
		(newTaskId: string) => {
			// Close any existing connection first
			stopListening();

			setTaskId(newTaskId);

			try {
				// Create new SSE connection
				const sse = new EventSource(`${SSE_URL}/${newTaskId}`, {
					withCredentials: true,
				});
				setEventSource(sse);

				// Connection opened
				sse.onopen = () => {
					setIsConnected(true);
					console.log(`SSE connection opened for task: ${newTaskId}`);
				};

				// Handle incoming messages
				sse.onmessage = (event) => {
					try {
						const data = JSON.parse(event.data);
						console.log("SSE event received:", data);

						// Handle task stage updates
						if (data.stage) {
							const stageUpdate: TaskStage = {
								status: data.status,
								description: data.description,
								startedAt: data.startedAt,
								completedAt: data.completedAt,
							};

							onStageUpdate?.(stageUpdate);

							// If task completed with results, call the result handler
							if (
								data.result &&
								data.stage.status === "SUCCESS"
							) {
								onResultReceived?.(data.result);
							}
						}
					} catch (error) {
						console.error("Error parsing SSE event:", error);
					}
				};

				// Handle errors
				sse.onerror = (error) => {
					console.error("SSE connection error:", error);
					onError?.(new Error("SSE connection failed"));
					stopListening();
				};
			} catch (error) {
				console.error("Failed to establish SSE connection:", error);
			}
		},
		[stopListening, onStageUpdate, onResultReceived, onError]
	);

	// Clean up on unmount
	useEffect(() => {
		return () => {
			if (typeof window !== "undefined") {
				stopListening();
			}
		};
	}, [stopListening]);

	return {
		isConnected,
		startListening,
		stopListening,
		taskId,
	};
}

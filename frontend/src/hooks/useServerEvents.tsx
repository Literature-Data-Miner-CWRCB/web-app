// src/hooks/useServerEvents.ts
import { useCallback, useEffect, useRef } from "react";
import { ProcessingStage, ProcessingStatus } from "@/types/events";

interface UseServerEventsProps {
	onStatusUpdate?: (status: ProcessingStatus) => void;
	onComplete?: (result: any) => void;
	onError?: (error: Error) => void;
}

export function useServerEvents({
	onStatusUpdate,
	onComplete,
	onError,
}: UseServerEventsProps = {}) {
	const eventSourceRef = useRef<EventSource | null>(null);

	const startListening = useCallback(
		(sessionId?: string) => {
			// Close any existing connection
			if (eventSourceRef.current) {
				eventSourceRef.current.close();
			}

			// In a real implementation, this would connect to your SSE endpoint
			// with the session ID to track progress
			const url = `/api/sse${sessionId ? `?sessionId=${sessionId}` : ""}`;

			// This would be replaced with a real implementation that connects to your backend
			// For now, we'll just mock the behavior in useDatasetBuilder

			// The real implementation would look something like:
			/*
    const eventSource = new EventSource(url);
    
    eventSource.addEventListener("status", (event) => {
      try {
        const data = JSON.parse(event.data) as ProcessingStatus;
        onStatusUpdate?.(data);
      } catch (error) {
        console.error("Error parsing status event:", error);
      }
    });
    
    eventSource.addEventListener("complete", (event) => {
      try {
        const data = JSON.parse(event.data);
        onComplete?.(data);
        eventSource.close();
      } catch (error) {
        console.error("Error parsing complete event:", error);
      }
    });
    
    eventSource.addEventListener("error", (event) => {
      const error = new Error("Error in server-sent events");
      onError?.(error);
      eventSource.close();
    });
    
    eventSourceRef.current = eventSource;
    */
		},
		[onStatusUpdate, onComplete, onError]
	);

	const stopListening = useCallback(() => {
		if (eventSourceRef.current) {
			eventSourceRef.current.close();
			eventSourceRef.current = null;
		}
	}, []);

	// Clean up on unmount
	useEffect(() => {
		return () => {
			stopListening();
		};
	}, [stopListening]);

	return {
		startListening,
		stopListening,
	};
}

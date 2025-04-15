// src/hooks/useDatasetBuilder.ts
import { useState, useEffect, useCallback } from "react";
import { DatasetQuery } from "@/types/dataset";
import { DataSchema } from "@/types/schema";
import { TaskStatus, TaskStage, DatasetResult } from "@/types/events";

// API endpoint for dataset generation
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DATASET_API_ENDPOINT = `${API_BASE_URL}/api/v1/datasets/generate`;
const TASK_API_ENDPOINT = `${API_BASE_URL}/tasks`;

export function useDatasetBuilder() {
	const [status, setStatus] = useState<TaskStatus>(TaskStatus.IDLE);
	const [stage, setStage] = useState<TaskStage | null>(null);
	const [result, setResult] = useState<DatasetResult | null>(null);
	const [taskId, setTaskId] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);

	const buildDataset = async (query: DatasetQuery, schema: DataSchema) => {
		try {
			// Reset state
			setStage(null);
			setResult(null);
			setError(null);
			setTaskId(null);

			// Convert the schema to the format expected by the backend
			const fieldDefinitions = schema.map((field) => ({
				name: field.name,
				type: field.type.toLowerCase(),
				description: field.description || `Field for ${field.name}`,
			}));

			// Create form data for the API request
			const formData = new FormData();
			formData.append("user_query", query.searchQuery);
			formData.append("rows", query.rowLimit.toString());
			formData.append("model_name", "DatasetModel");
			formData.append(
				"field_definitions_json_str",
				JSON.stringify(fieldDefinitions)
			);

			// Send the request to the API
			const response = await fetch(DATASET_API_ENDPOINT, {
				method: "POST",
				body: formData,
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					errorData.message || "Failed to generate dataset"
				);
			}

			// Extract the task ID from the response
			const data = await response.json();
			setTaskId(data.task_id);
		} catch (error) {
			console.error("Error building dataset:", error);
		}
	};

	const cancelTask = async () => {
		if (!taskId) {
			console.warn("No task ID to cancel");
			return;
		}

		try {
			// TODO:Call the revoke endpoint to cancel the task

			return;
		} catch (error) {
			console.error("Error cancelling task:", error);
		}
	};

	const checkTaskStatus = async () => {
		if (!taskId) {
			console.warn("No task ID to check");
			return;
		}

		try {
			const response = await fetch(`${TASK_API_ENDPOINT}/${taskId}`, {
				method: "GET",
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					errorData.message || "Failed to check task status"
				);
			}

			return await response.json();
		} catch (error) {
			console.error("Error checking task status:", error);
			// TODO: toast error
		}
	};

	return {
		status,
		result,
		buildDataset,
		error: error,
		taskId,
		cancelTask,
		checkTaskStatus,
	};
}

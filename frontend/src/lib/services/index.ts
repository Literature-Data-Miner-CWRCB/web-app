import { DatasetQuery, ColumnFields } from "@/types";

// API endpoints
const API_BASE_URL = process.env.PUBLIC_API_URL || "http://localhost:8000";
const CREATE_DATASET_URL = `${API_BASE_URL}/api/v1/datasets/generate`;

interface CreateDatasetResponse {
    task_id: string;
}

export const createDatasetTask = async (
    query: DatasetQuery,
    columns: ColumnFields
): Promise<CreateDatasetResponse | undefined> => {
    // Create form data for the API request
    const formData = new FormData();
    formData.append("user_query", query.searchQuery);
    formData.append("rows", query.rowLimit.toString());
    formData.append("model_name", "DatasetModel");
    formData.append(
        "field_definitions_json_str",
        JSON.stringify(columns)
    );

    // Send the request to the API
    const response = await fetch(CREATE_DATASET_URL, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
            errorData.message
        );
    }

    // Extract the task ID from the response
    const data = await response.json();
    return { task_id: data.task_id };
};

export const revokeDatasetTask = async (taskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/datasets/revoke/${taskId}`, {
        method: "DELETE",
    });

    if (!response.ok) {
        const errorData = await response.json();
        return { success: false, message: errorData.message || "Failed to revoke task" };
    }

    return { success: true, message: "Task revoked successfully" };
}
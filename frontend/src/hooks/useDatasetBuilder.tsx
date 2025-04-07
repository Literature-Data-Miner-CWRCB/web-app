// src/hooks/useDatasetBuilder.ts
import { useState } from "react";
import { DatasetQuery } from "@/types/dataset";
import { DataSchema } from "@/types/schema";
import {
	ProcessingStage,
	ProcessingStatus,
	DatasetResult,
} from "@/types/events";

// This would be replaced with actual API calls to your backend
const mockBuildDataset = async (
	query: DatasetQuery,
	schema: DataSchema
): Promise<string> => {
	// In a real implementation, this would send the query and schema to your backend
	// and return a session ID for tracking progress via SSE
	return "session-" + Math.random().toString(36).substring(2, 9);
};

export function useDatasetBuilder() {
	const [status, setStatus] = useState<ProcessingStatus>({
		stage: ProcessingStage.IDLE,
		message: "",
	});

	const [result, setResult] = useState<DatasetResult | null>(null);

	const buildDataset = async (query: DatasetQuery, schema: DataSchema) => {
		try {
			setStatus({
				stage: ProcessingStage.SEARCHING,
				message: "Searching for relevant research papers...",
				progress: 10,
			});

			// In a real implementation, this would initiate the build process
			// and return a session ID for tracking progress
			const sessionId = await mockBuildDataset(query, schema);

			// The actual progress updates would come from the SSE endpoint
			// This is just a mock for demonstration purposes

			// Actual state updates would happen in the useServerEvents hook
			// We'll leave the rest of the mock implementation here for demonstration

			// This is just for demonstration - real implementation would listen to SSE
			setTimeout(() => {
				setStatus({
					stage: ProcessingStage.EXTRACTING,
					message: "Extracting data from papers...",
					progress: 30,
				});
			}, 1500);

			setTimeout(() => {
				setStatus({
					stage: ProcessingStage.TRANSFORMING,
					message: "Transforming data to match schema...",
					progress: 60,
				});
			}, 3000);

			setTimeout(() => {
				setStatus({
					stage: ProcessingStage.VALIDATING,
					message: "Validating dataset integrity...",
					progress: 90,
				});
			}, 4500);

			// Mock completion with sample data
			setTimeout(() => {
				setStatus({
					stage: ProcessingStage.COMPLETED,
					message: "Dataset successfully generated!",
				});

				// Generate mock result data based on the schema
				const mockData = Array.from(
					{ length: query.rowLimit },
					(_, i) => {
						const row: Record<string, any> = {};
						schema.forEach((field) => {
							switch (field.type) {
								case "string":
									row[field.name] = `Sample ${field.name} ${
										i + 1
									}`;
									break;
								case "number":
									row[field.name] = Math.floor(
										Math.random() * 100
									);
									break;
								case "boolean":
									row[field.name] = Math.random() > 0.5;
									break;
								case "date":
									row[field.name] = new Date(
										2020 + Math.floor(Math.random() * 5),
										Math.floor(Math.random() * 12),
										Math.floor(Math.random() * 28) + 1
									).toISOString();
									break;
								default:
									row[field.name] = `Sample ${field.name} ${
										i + 1
									}`;
							}
						});
						return row;
					}
				);

				// Mock citations
				const mockCitations = [
					{
						id: "c1",
						title: "Advances in Machine Learning for Natural Language Processing",
						authors: ["Smith, J.", "Johnson, A.", "Williams, R."],
						journal: "Journal of Artificial Intelligence Research",
						year: 2023,
						doi: "10.1234/jair.2023.123456",
						url: "https://example.com/paper1",
					},
					{
						id: "c2",
						title: "Deep Learning Approaches to Data Extraction from Scientific Literature",
						authors: ["Chen, L.", "Garcia, M."],
						journal: "Computational Linguistics",
						year: 2022,
						doi: "10.5678/cl.2022.654321",
						url: "https://example.com/paper2",
					},
					{
						id: "c3",
						title: "Automated Dataset Generation for Machine Learning Research",
						authors: ["Brown, T.", "Davis, S.", "Miller, J."],
						journal:
							"Proceedings of the Conference on Machine Learning Applications",
						year: 2024,
						doi: "10.9876/cmla.2024.112233",
						url: "https://example.com/paper3",
					},
				];

				setResult({
					id: sessionId,
					data: mockData,
					schema,
					totalRows: mockData.length,
					citations: mockCitations,
				});
			}, 6000);
		} catch (error) {
			console.error("Error building dataset:", error);
			setStatus({
				stage: ProcessingStage.ERROR,
				message: "An error occurred while generating the dataset.",
			});
		}
	};

	return {
		status,
		result,
		buildDataset,
	};
}

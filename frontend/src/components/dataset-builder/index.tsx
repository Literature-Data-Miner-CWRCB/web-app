// src/components/dataset-builder/index.tsx
"use client";
import { useState } from "react";
import { useDatasetBuilder } from "@/hooks/useDatasetBuilder";
import { DataSchema } from "@/types/schema";
import { OutputFormat, FilterOption, DatasetQuery } from "@/types/dataset";
import { TaskStatus } from "@/types/events";
import { QueryInput } from "./query-input";
import { FilterOptions } from "./filter-options";
import { OutputFormatSelector } from "./output-format-selecter";
import { SchemaDefinition } from "./schema-definition";
import { BuildButton } from "./build-button";
import { ProcessingIndicator } from "./processing-indicator";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { DatasetResults } from "@/components/results/dataset-results";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { z } from "zod";

// Define validation schema using Zod
const searchQuerySchema = z
	.string()
	.min(1, "Search query is required")
	.max(500, "Search query must be 500 characters or less");

const fieldNameSchema = z
	.string()
	.min(1, "Field name is required")
	.max(25, "Field name must be 25 characters or less")
	.regex(/^[a-zA-Z_]+$/, "Only letters and underscores are allowed");

const fieldDescriptionSchema = z
	.string()
	.min(1, "Description is required")
	.max(100, "Description must be 100 characters or less");

// Filter options
const filterOptions: FilterOption[] = [
	{ id: "peer-reviewed", name: "Peer-reviewed only" },
	{ id: "open-access", name: "Open access" },
	{ id: "recent", name: "Last 5 years" },
];

interface FormError {
	query?: string;
	definitions?: {
		[key: string]: {
			name?: string;
			description?: string;
		};
	};
}

export function DatasetBuilder() {
	// Form state
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
	const [outputFormat, setOutputFormat] = useState<OutputFormat>("csv");
	const [rowLimit, setRowLimit] = useState(100);
	const [schema, setSchema] = useState<DataSchema>([]);

	// Validation state
	const isFormValid =
		searchQuery.trim() !== "" &&
		schema.length > 0 &&
		schema.every((field) => field.name.trim() !== "");

	// Processing state and hooks
	const { status, result, buildDataset, error, cancelTask } =
		useDatasetBuilder();

	const handleBuild = () => {
		if (!isFormValid) return;

		const query: DatasetQuery = {
			searchQuery,
			filters: selectedFilters,
			outputFormat,
			rowLimit,
		};

		buildDataset(query, schema);
	};

	const handleCancel = async () => {
		if (
			window.confirm(
				"Are you sure you want to cancel dataset generation?"
			)
		) {
			await cancelTask();
		}
	};

	// Check if the process is currently running
	const isProcessing =
		status !== TaskStatus.IDLE &&
		status !== TaskStatus.SUCCESS &&
		status !== TaskStatus.FAILURE;

	return (
		<div className="space-y-6">
			<div className="grid gap-6">
				<Card>
					<CardHeader>
						<CardTitle>Dataset Query</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="grid gap-6">
							{/* Query input section */}
							<QueryInput
								value={searchQuery}
								onChange={setSearchQuery}
							/>

							{/* Selectors in responsive grid */}
							<div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
								<FilterOptions
									options={filterOptions}
									selectedFilters={selectedFilters}
									onFilterChange={setSelectedFilters}
								/>
								<OutputFormatSelector
									value={outputFormat}
									onChange={setOutputFormat}
								/>
								<div className="flex flex-col">
									<Label htmlFor="row-limit" className="mb-2">
										Rows ({rowLimit})
									</Label>
									<Slider
										id="row-limit"
										min={10}
										max={1000}
										step={10}
										value={[rowLimit]}
										onValueChange={(values) =>
											setRowLimit(values[0])
										}
									/>
								</div>
							</div>
						</div>
					</CardContent>
				</Card>

				<SchemaDefinition schema={schema} onSchemaChange={setSchema} />

				{error && (
					<Alert variant="destructive">
						<AlertCircle className="h-4 w-4" />
						<AlertDescription>{error}</AlertDescription>
					</Alert>
				)}

				<div className="flex justify-center gap-4">
					<BuildButton
						onClick={handleBuild}
						isLoading={isProcessing}
						isDisabled={isProcessing}
					/>

					{isProcessing && (
						<Button variant="destructive" onClick={handleCancel}>
							Cancel
						</Button>
					)}
				</div>
			</div>

			{result && <DatasetResults result={result} />}
		</div>
	);
}
